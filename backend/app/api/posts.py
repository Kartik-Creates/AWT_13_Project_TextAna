from fastapi import APIRouter, UploadFile, File
from app.services.moderation_service import analyze_text, decision_engine
from app.services.image_service import analyze_image
from app.db.mongodb import get_all_posts

router = APIRouter()

@router.get("/posts")
async def get_posts():
    try:
        posts = get_all_posts()
        return posts
    except Exception as e:
        return {"error": str(e)}

@router.post("/posts")
async def create_post(text: str, image: UploadFile = File(None)):

    text_result = analyze_text(text)

    image_result = "SAFE"

    if image:
        image_result = analyze_image(image)

    decision = decision_engine(text_result, image_result)

    return {
        "text": text,
        "text_result": text_result,
        "image_result": image_result,
        "decision": decision
    }
