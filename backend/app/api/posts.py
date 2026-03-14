"""
Post API endpoints
Sachinn's responsibility: Handle all post-related HTTP requests
"""

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
    
    logger.info(f"File saved: {file_path}")
    return f"/uploads/{file_name}"

@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="Post content"),
    image: Optional[UploadFile] = File(None, description="Optional image")
):
    """
    Create a new post with automatic moderation
    
    - **text**: Post content (required)
    - **image**: Optional image file
    """
    try:
        logger.info(f"Creating new post with text: {text[:50]}...")
        
        # Save image if provided
        image_path = None
        if image and image.filename:
            # Validate file type
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type not allowed. Allowed: {allowed_types}"
                )
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[PostResponse])
async def get_posts(
    skip: int = 0, 
    limit: int = 50,
    filter: Optional[str] = None
):
    """
    Get all posts with pagination and optional filtering
    
    - **skip**: Number of posts to skip
    - **limit**: Maximum number of posts to return
    - **filter**: Filter by status (all, allowed, rejected, pending)
    """
    try:
        posts = post_repository.get_all(skip=skip, limit=limit)
        
        # Apply filter if specified
        if filter and filter != "all":
            if filter == "allowed":
                posts = [p for p in posts if p.get("allowed") == True]
            elif filter == "rejected":
                posts = [p for p in posts if p.get("allowed") == False]
            elif filter == "pending":
                posts = [p for p in posts if p.get("allowed") is None]
        
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

@router.get("/stats/overview", response_model=StatsResponse)
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
    return {"message": "Post deleted successfully", "id": post_id}

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
    
    return {"message": "Post queued for reprocessing", "id": post_id}