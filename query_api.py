"""Read models for the local donor/NGO workspace. No credentials are exposed."""
from fastapi import APIRouter, HTTPException, Query
from database import get_connection
from mongodb import client
from database_diagnostics import diagnose
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def read_rows(sql, params=()):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as error:
        raise HTTPException(503, 'Database unavailable. Check the configured MySQL service.') from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@router.get('/users')
def list_users(role: str | None = Query(default=None, pattern='^(DONOR|NGO)$')):
    sql = 'SELECT user_id, name, role, location FROM users'
    return read_rows(sql + (' WHERE role = %s' if role else '') + ' ORDER BY name', (role,) if role else ())


@router.get('/requests')
def list_requests(donor_id: int | None = Query(default=None, gt=0), ngo_id: int | None = Query(default=None, gt=0)):
    sql = '''SELECT r.request_id, r.food_id, r.ngo_id, r.requested_quantity,
        r.request_date, r.status, f.food_name, f.unit, f.donor_id,
        f.pickup_deadline, n.name AS ngo_name, d.name AS donor_name,
        c.collected_quantity, c.collected_at, c.notes
        FROM donation_requests r
        JOIN food_listings f ON f.food_id = r.food_id
        JOIN users n ON n.user_id = r.ngo_id
        JOIN users d ON d.user_id = f.donor_id
        LEFT JOIN collections c ON c.request_id = r.request_id'''
    conditions, params = [], []
    if donor_id:
        conditions.append('f.donor_id = %s')
        params.append(donor_id)
    if ngo_id:
        conditions.append('r.ngo_id = %s')
        params.append(ngo_id)
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    return read_rows(sql + ' ORDER BY r.request_id DESC', tuple(params))


@router.get('/health')
def health():
    databases = {}
    errors = {}
    try:
        read_rows('SELECT 1 AS connected')
        databases['mysql'] = 'connected'
    except HTTPException as error:
        databases['mysql'] = 'unavailable'
        errors['mysql'] = diagnose('mysql', error.__cause__ or error)
    try:
        client.admin.command('ping')
        databases['mongodb'] = 'connected'
    except Exception as error:
        databases['mongodb'] = 'unavailable'
        errors['mongodb'] = diagnose('mongodb', error)
    if 'unavailable' in databases.values():
        for database, error in errors.items():
            logger.warning('Database health failure: %s (%s)', database, error['code'])
        raise HTTPException(503, {'status': 'degraded', **databases, 'errors': errors})
    return {'status': 'ready', **databases}
