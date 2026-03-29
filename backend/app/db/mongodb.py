from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection and operations manager"""
    
    _instance = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._client:
            self.connect()
    
    def connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            db_name = os.getenv("MONGODB_DB_NAME", "loops_moderation")
            
            self._client = MongoClient(mongodb_url)
            self._db = self._client[db_name]
            
            # Test connection
            self._client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {mongodb_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @property
    def posts(self) -> Collection:
        """Get posts collection"""
        return self._db.posts
    
    @property
    def prediction_metrics(self) -> Collection:
        """Get prediction metrics collection"""
        return self._db.prediction_metrics
    
    def close(self) -> None:
        """Close database connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")

class PostRepository:
    """Repository for post operations"""
    
    def __init__(self):
        self.db = MongoDB()
        self.collection = self.db.posts
    
    def create(self, post_data: Dict[str, Any]) -> str:
        """Create a new post"""
        post_data["created_at"] = datetime.utcnow()
        post_data["updated_at"] = datetime.utcnow()
        
        result = self.collection.insert_one(post_data)
        return str(result.inserted_id)
    
    def get_all(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all posts with pagination"""
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        
        posts = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["id"] = doc["_id"]
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
            if "updated_at" in doc and hasattr(doc["updated_at"], 'isoformat'):
                doc["updated_at"] = doc["updated_at"].isoformat()
            posts.append(doc)
        
        return posts
    
    def get_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a post by ID"""
        from bson.objectid import ObjectId
        
        try:
            doc = self.collection.find_one({"_id": ObjectId(post_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                doc["id"] = doc["_id"]
                if "created_at" in doc:
                    doc["created_at"] = doc["created_at"].isoformat()
                if "updated_at" in doc and hasattr(doc["updated_at"], 'isoformat'):
                    doc["updated_at"] = doc["updated_at"].isoformat()
            return doc
        except Exception as e:
            logger.error(f"Error fetching post {post_id}: {e}")
            return None
    
    def update_moderation_result(self, post_id: str, allowed: bool, 
                                  reasons: List[str], flagged_phrases: List[str]) -> bool:
        """Update post with moderation results"""
        from bson.objectid import ObjectId
        
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$set": {
                        "allowed": allowed,
                        "reasons": reasons,
                        "flagged_phrases": flagged_phrases,
                        "moderated_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating moderation result for post {post_id}: {e}")
            return False
    
    def delete(self, post_id: str) -> bool:
        """Delete a post"""
        from bson.objectid import ObjectId
        
        result = self.collection.delete_one({"_id": ObjectId(post_id)})
        return result.deleted_count > 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get moderation statistics"""
        total = self.collection.count_documents({})
        allowed = self.collection.count_documents({"allowed": True})
        rejected = self.collection.count_documents({"allowed": False})
        pending = self.collection.count_documents({"allowed": None})
        
        return {
            "total": total,
            "allowed": allowed,
            "rejected": rejected,
            "pending": pending
        }

# Create singleton instances
mongodb = MongoDB()
post_repository = PostRepository()  # This is what we need to export

# Explicitly export
__all__ = ['mongodb', 'post_repository']
