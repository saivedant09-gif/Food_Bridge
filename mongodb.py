
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client[os.getenv("MONGO_DATABASE", "food_bridge_mongo")]

food_reviews = db["food_reviews"]


def test_mongo_connection():
    try:
        client.admin.command("ping")
        return True
    except Exception as error:
        print("MongoDB connection failed:", error)
        return False


if __name__ == "__main__":
    if test_mongo_connection():
        print("Connected to Food Bridge MongoDB!")
        print("Database:", db.name)
        print("Collection:", food_reviews.name)
        print("Number of reviews:", food_reviews.count_documents({}))

    client.close()
