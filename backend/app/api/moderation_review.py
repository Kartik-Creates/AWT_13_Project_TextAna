from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.db.mongodb import mongodb

router = APIRouter()

class ReviewDecision(BaseModel):
    post_id: str
    decision: str       # "approve" or "reject"
    reviewer_id: str

@router.get("/pending")
def get_pending_reviews():
    """Fetch all posts flagged for human review."""
    posts = list(mongodb.posts.find(
        {"moderation_status": "human_review"},
        {"_id": 1, "text": 1, "image_path": 1,
         "review_reasons": 1, "borderline_scores": 1, "flagged_at": 1}
    ))
    return {"count": len(posts), "posts": posts}

@router.post("/decide")
def submit_review_decision(payload: ReviewDecision):
    """Approve or reject a flagged post."""
    if payload.decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be 'approve' or 'reject'")

    allowed = payload.decision == "approve"

    mongodb.posts.update_one(
        {"_id": payload.post_id},
        {"$set": {
            "moderation_status": "approved" if allowed else "blocked",
            "allowed": allowed,
            "reviewed_by": payload.reviewer_id,
            "reviewed_at": datetime.utcnow(),
        }}
    )

    return {
        "post_id": payload.post_id,
        "decision": payload.decision,
        "success": True
    }