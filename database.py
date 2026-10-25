
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "food_bridge"),
        connection_timeout=5,
    )

if __name__ == "__main__":
    try:
        connection = get_connection()
        print("Connected to Food Bridge MySQL database!")

        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")

        print("Tables in database:")
        for table in cursor.fetchall():
            print(table[0])

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        print("Database connection failed:", error)
