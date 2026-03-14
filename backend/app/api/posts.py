from fastapi import APIRouter

router = APIRouter()

@router.post("/posts")
def create_post(text: str):
    return {
        "status": "received",
        "text": text
    }