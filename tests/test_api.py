"""Contract checks without requiring or modifying the user's databases."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_status(self):
        self.assertEqual(self.client.get('/').json()['status'], 'running')

    def test_validation_prevents_invalid_quantities(self):
        with patch('main.get_connection') as connection:
            response = self.client.post('/requests', json={
                'food_id': 0, 'ngo_id': 1, 'requested_quantity': -2,
            })
            self.assertEqual(response.status_code, 422)
            connection.assert_not_called()

    def test_invalid_pickup_window_does_not_touch_database(self):
        with patch('main.get_connection') as connection:
            response = self.client.post('/food', json={
                'donor_id': 1, 'food_name': 'Rice', 'quantity': 2, 'unit': 'kg',
                'prepared_at': '2026-10-25T16:00', 'pickup_deadline': '2026-10-25T15:00',
            })
            self.assertEqual(response.status_code, 400)
            connection.assert_not_called()

    def test_food_database_failure_is_safe(self):
        with patch('main.get_connection', side_effect=RuntimeError('private connection string')):
            response = self.client.get('/food')
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('private', response.text)

    def test_review_database_failure_is_safe(self):
        with patch('main.food_reviews') as reviews:
            reviews.find.side_effect = RuntimeError('private connection string')
            response = self.client.get('/reviews')
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('private', response.text)

    def test_review_filter_matches_food_id(self):
        with patch('main.food_reviews') as reviews:
            reviews.find.return_value = []
            response = self.client.get('/reviews/19')
            self.assertEqual(response.json(), {'food_id': 19, 'count': 0, 'reviews': []})
            reviews.find.assert_called_once_with({'food_id': 19}, {'_id': 0})

    def test_local_origin_is_allowed(self):
        response = self.client.options('/food', headers={
            'Origin': 'http://127.0.0.1:5173',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], 'http://127.0.0.1:5173')

    def test_unknown_origin_is_rejected(self):
        response = self.client.options('/food', headers={
            'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'POST',
        })
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access-control-allow-origin', response.headers)

    def test_sql_decimal_precision_is_validated(self):
        with patch('main.get_connection') as connection:
            response = self.client.post('/requests', json={
                'food_id': 1, 'ngo_id': 4, 'requested_quantity': 0.001,
            })
            self.assertEqual(response.status_code, 422)
            connection.assert_not_called()

    def test_users_reject_arbitrary_roles(self):
        self.assertEqual(self.client.get('/users?role=ADMIN').status_code, 422)

    def test_user_list_excludes_private_fields(self):
        with patch('query_api.read_rows', return_value=[]) as rows:
            self.assertEqual(self.client.get('/users?role=NGO').json(), [])
            sql, params = rows.call_args.args
            self.assertNotIn('password', sql.lower())
            self.assertNotIn('email', sql.lower())
            self.assertEqual(params, ('NGO',))

    def test_health_reports_dependency_failure(self):
        from fastapi import HTTPException
        with patch('query_api.read_rows', side_effect=HTTPException(503, 'unavailable')):
            with patch('query_api.client') as mongo:
                mongo.admin.command.return_value = {'ok': 1}
                response = self.client.get('/health')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['detail']['mysql'], 'unavailable')
                self.assertNotIn('private', response.text)


if __name__ == '__main__':
    unittest.main()
