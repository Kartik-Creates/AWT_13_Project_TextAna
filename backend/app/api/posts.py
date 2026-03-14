from fastapi import APIRouter
from app.services.moderation_service import analyze_text

router = APIRouter()

@router.post("/posts")
def create_post(text: str):

    result = analyze_text(text)

    return {
        "status": "processed",
        "text": text,
        "classification": result
    }