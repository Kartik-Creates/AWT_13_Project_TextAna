"""
Pydantic schemas for data validation.
Defines API request/response models for the moderation system.
"""
 
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
 
 
class PostBase(BaseModel):
    """Base post schema."""
    # Allow empty text for image-only posts (frontend uses "" as placeholder).
    text: str = Field("", min_length=0, max_length=5000, description="Post content")
    image_path: Optional[str] = Field(None, description="Path to uploaded image")
    user_id: Optional[str] = Field(None, description="User ID (if authenticated)")
 
 
class PostCreate(PostBase):
    """Schema for creating a post."""
    pass
 
 
class TechRelevanceResult(BaseModel):
    """Schema for tech relevance analysis results."""
    tech_relevance_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Tech relevance score (0=off-topic, 1=highly tech-relevant)"
    )
    zone: str = Field(
        ...,
        description="Decision zone: 'tech' | 'review' | 'off_topic'"
    )
    matched_categories: List[str] = Field(
        default=[],
        description="Tech taxonomy categories that matched (e.g. 'languages', 'devops_cloud')"
    )
    matched_terms: List[str] = Field(
        default=[],
        description="Sample of tech terms detected in the post"
    )
    non_tech_signals: List[str] = Field(
        default=[],
        description="Off-topic signals detected (if any)"
    )
 
    class Config:
        schema_extra = {
            "example": {
                "tech_relevance_score": 0.82,
                "zone": "tech",
                "matched_categories": ["languages", "devops_cloud", "tools_concepts"],
                "matched_terms": ["python", "docker", "kubernetes", "api"],
                "non_tech_signals": []
            }
        }
 
 
class PostModerationResult(BaseModel):
    """Schema for moderation results."""
    allowed: bool
    reasons: List[str] = []
    flagged_phrases: List[str] = []
    toxicity_score: Optional[float] = None
    nsfw_score: Optional[float] = None
    clip_similarity: Optional[float] = None
    tech_relevance_score: Optional[float] = Field(
        None,
        description="Tech relevance score from rule engine (0–1)"
    )
    tech_zone: Optional[str] = Field(
        None,
        description="Tech zone: 'tech' | 'review' | 'off_topic'"
    )
    moderation_time_ms: Optional[int] = None
 
    class Config:
        schema_extra = {
            "example": {
                "allowed": True,
                "reasons": ["tech_content"],
                "flagged_phrases": [],
                "toxicity_score": 0.05,
                "nsfw_score": 0.01,
                "clip_similarity": 0.87,
                "tech_relevance_score": 0.76,
                "tech_zone": "tech",
                "moderation_time_ms": 312
            }
        }
 
 
class PostInDB(PostBase):
    """Schema for post from database."""
    id: str = Field(alias="_id")
    allowed: Optional[bool] = None
    reasons: List[str] = []
    flagged_phrases: List[str] = []
    tech_relevance_score: Optional[float] = Field(
        None, description="Tech relevance score stored at moderation time"
    )
    tech_zone: Optional[str] = Field(
        None, description="Tech zone stored at moderation time"
    )
    created_at: datetime
    updated_at: datetime
    moderated_at: Optional[datetime] = None
 
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
 
 
class PostResponse(PostBase):
    """Schema for post response."""
    id: str
    allowed: Optional[bool]
    reasons: List[str]
    flagged_phrases: List[str]
    tech_relevance_score: Optional[float] = Field(
        None,
        description="Tech relevance score (0–1). None if not yet moderated."
    )
    tech_zone: Optional[str] = Field(
        None,
        description="Tech zone: 'tech' | 'review' | 'off_topic'"
    )
    created_at: str
 
    class Config:
        schema_extra = {
            "example": {
                "id": "60f7b1b5b5f9b7b1b5b5f9b7",
                "text": "Just deployed my FastAPI app on Kubernetes using Helm charts!",
                "image_path": None,
                "allowed": True,
                "reasons": ["tech_content"],
                "flagged_phrases": [],
                "tech_relevance_score": 0.91,
                "tech_zone": "tech",
                "created_at": "2024-01-01T12:00:00"
            }
        }
 
 
class StatsResponse(BaseModel):
    """Schema for statistics response."""
    total: int
    allowed: int
    rejected: int
    pending: int
    off_topic_blocked: Optional[int] = Field(
        None,
        description="Posts blocked specifically for being off-topic (not harmful)"
    )
    avg_tech_relevance_score: Optional[float] = Field(
        None,
        description="Average tech relevance score across all moderated posts"
    )
 
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "allowed": 75,
                "rejected": 20,
                "pending": 5,
                "off_topic_blocked": 8,
                "avg_tech_relevance_score": 0.68
            }
        }
 
 
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    status_code: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
 