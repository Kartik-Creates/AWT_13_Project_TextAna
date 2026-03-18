from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import shutil
import uuid
from datetime import datetime
import logging

from app.db.mongodb import post_repository
from app.schemas.posts import PostResponse, PostCreate, StatsResponse
from app.services.moderation_service import ModerationService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize moderation service
moderation_service = ModerationService()

# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return path"""
    # Generate unique filename
    file_extension = os.path.splitext(upload_file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return f"/uploads/{file_name}"

@router.post("/", response_model=PostResponse)
async def create_post(
    background_tasks: BackgroundTasks,
    text: str = Form(""),
    image: Optional[UploadFile] = File(None)
):
    """Create a new post with moderation"""
    try:
        logger.info(f"Creating new post with text: {text[:50]}...")
        
        # Save image if provided
        image_path = None
        if image and image.filename:
            image_path = await save_upload_file(image)
            logger.info(f"Image saved: {image_path}")
        
        # Create post in database
        post_data = {
            "text": text,
            "image_path": image_path,
            "allowed": None,  # Pending moderation
            "reasons": [],
            "flagged_phrases": []
        }
        
        post_id = post_repository.create(post_data)
        logger.info(f"Post created with ID: {post_id}")
        
        # Run moderation in background
        background_tasks.add_task(
            moderation_service.moderate_post,
            post_id=post_id,
            text=text,
            image_path=image_path
        )
        
        # Return immediate response
        return {
            "id": post_id,
            "text": text,
            "image_path": image_path,
            "allowed": None,
            "reasons": [],
            "flagged_phrases": [],
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[PostResponse])
async def get_posts(skip: int = 0, limit: int = 50):
    """Get all posts with pagination"""
    try:
        posts = post_repository.get_all(skip=skip, limit=limit)
        return posts
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: str):
    """Get a single post by ID"""
    post = post_repository.get_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.get("/stats/overview")
async def get_stats():
    """Get moderation statistics"""
    try:
        stats = post_repository.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{post_id}")
async def delete_post(post_id: str):
    """Delete a post"""
    success = post_repository.delete(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted successfully"}

@router.post("/{post_id}/reprocess")
async def reprocess_post(post_id: str, background_tasks: BackgroundTasks):
    """Reprocess a post through moderation"""
    post = post_repository.get_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Run moderation again
    background_tasks.add_task(
        moderation_service.moderate_post,
        post_id=post_id,
        text=post["text"],
        image_path=post.get("image_path")
    )
    
    return {"message": "Post queued for reprocessing"}