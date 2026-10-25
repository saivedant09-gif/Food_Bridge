"""Initialize missing local storage and import reviews without overwriting existing data."""
from pathlib import Path
import os
import re
import mysql.connector
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import json_util

ROOT = Path(__file__).resolve().parents[1]


def setup():
    load_dotenv(ROOT / '.env')
    database = os.getenv('MYSQL_DATABASE', 'food_bridge')
    if not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise RuntimeError('MYSQL_DATABASE must contain only letters, digits and underscores.')
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'), port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'root'), password=os.getenv('MYSQL_PASSWORD'), connection_timeout=5,
    )
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s', (database,))
        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci')
            connection.database = database
            cursor.execute((ROOT / 'database' / 'food_bridge.sql').read_text(encoding='utf-8'))
            while cursor.nextset():
                pass
            connection.commit()
            print('Created MySQL database and imported teammate data.', flush=True)
        else:
            connection.database = database
        cursor.execute('SHOW TABLES')
        tables = {row[0] for row in cursor.fetchall()}
        missing = {'users', 'food_listings', 'donation_requests', 'collections'} - tables
        if missing:
            raise RuntimeError('Existing database has missing tables: ' + ', '.join(sorted(missing)) + '. No existing tables were replaced.')
        print('MySQL tables ready; existing data preserved.', flush=True)
    finally:
        cursor.close()
        connection.close()
    with MongoClient(os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017'), serverSelectionTimeoutMS=5000) as client:
        client.admin.command('ping')
        reviews = client[os.getenv('MONGO_DATABASE', 'food_bridge_mongo')]['food_reviews']
        for review in json_util.loads((ROOT / 'database' / 'food_reviews.json').read_text(encoding='utf-8')):
            reviews.update_one({'_id': review['_id']}, {'$setOnInsert': review}, upsert=True)
        print(f'MongoDB ready with {reviews.count_documents({})} reviews; existing reviews preserved.', flush=True)


if __name__ == '__main__':
    setup()
