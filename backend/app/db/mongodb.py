from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

MONGO_URI = "mongodb://localhost:27017"

client = MongoClient(MONGO_URI)

db = client["moderation_db"]

posts_collection = db["posts"]


def get_posts_collection():
    return posts_collection


def insert_post(post_data):
    post_data["created_at"] = datetime.utcnow()
    result = posts_collection.insert_one(post_data)
    return str(result.inserted_id)


def get_all_posts():
    posts = []
    for post in posts_collection.find():
        post["_id"] = str(post["_id"])
        posts.append(post)
    return posts


def get_post_by_id(post_id):
    post = posts_collection.find_one({"_id": ObjectId(post_id)})

    if post:
        post["_id"] = str(post["_id"])

    return post