import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from mysql.connector import Error
from pymongo.errors import OperationFailure, ConfigurationError, ServerSelectionTimeoutError
from database_diagnostics import diagnose
from main import app


class DiagnosticsTests(unittest.TestCase):
    def test_mysql_password_and_database_have_distinct_diagnostics(self):
        self.assertEqual(diagnose('mysql', Error('private password', errno=1045))['code'], 'mysql_credentials')
        self.assertEqual(diagnose('mysql', Error('private database', errno=1049))['code'], 'mysql_database_missing')

    def test_atlas_credentials_and_network_have_distinct_diagnostics(self):
        self.assertEqual(diagnose('mongodb', OperationFailure('private URI', code=18))['code'], 'mongodb_credentials')
        self.assertEqual(diagnose('mongodb', ServerSelectionTimeoutError('private URI'))['code'], 'mongodb_network')
        self.assertEqual(diagnose('mongodb', ConfigurationError('private URI'))['code'], 'mongodb_uri')

    def test_health_reports_safe_diagnostics_without_credentials(self):
        with patch('query_api.get_connection', side_effect=Error('PRIVATE_MYSQL_SECRET', errno=1049)):
            with patch('query_api.client') as mongo:
                mongo.admin.command.side_effect = OperationFailure('PRIVATE_MONGO_SECRET', code=18)
                response = TestClient(app).get('/health')
        self.assertEqual(response.status_code, 503)
        errors = response.json()['detail']['errors']
        self.assertEqual(errors['mysql']['code'], 'mysql_database_missing')
        self.assertEqual(errors['mongodb']['code'], 'mongodb_credentials')
        self.assertNotIn('PRIVATE_', response.text)
