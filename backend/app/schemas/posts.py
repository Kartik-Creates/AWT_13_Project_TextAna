"""
Pydantic schemas for data validation
Sachinn's responsibility: Define API request/response models
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

class PostBase(BaseModel):
    """Base post schema"""
    text: str = Field(..., min_length=1, max_length=5000, description="Post content")
    image_path: Optional[str] = Field(None, description="Path to uploaded image")
    user_id: Optional[str] = Field(None, description="User ID (if authenticated)")

class PostCreate(PostBase):
    """Schema for creating a post"""
    pass

class PostModerationResult(BaseModel):
    """Schema for moderation results"""
    allowed: bool
    reasons: List[str] = []
    flagged_phrases: List[str] = []
    toxicity_score: Optional[float] = None
    nsfw_score: Optional[float] = None
    clip_similarity: Optional[float] = None
    moderation_time_ms: Optional[int] = None

class PostInDB(PostBase):
    """Schema for post from database"""
    id: str = Field(alias="_id")
    allowed: Optional[bool] = None
    reasons: List[str] = []
    flagged_phrases: List[str] = []
    created_at: datetime
    updated_at: datetime
    moderated_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PostResponse(PostBase):
    """Schema for post response"""
    id: str
    allowed: Optional[bool]
    reasons: List[str]
    flagged_phrases: List[str]
    created_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": "60f7b1b5b5f9b7b1b5b5f9b7",
                "text": "Hello world!",
                "image_path": "/uploads/image.jpg",
                "allowed": True,
                "reasons": [],
                "flagged_phrases": [],
                "created_at": "2024-01-01T12:00:00"
            }
        }

class StatsResponse(BaseModel):
    """Schema for statistics response"""
    total: int
    allowed: int
    rejected: int
    pending: int
    
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "allowed": 75,
                "rejected": 20,
                "pending": 5
            }
        }

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    status_code: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())