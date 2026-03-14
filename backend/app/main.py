from fastapi import FastAPI
from app.core.config import settings
from app.api import posts
from app.services.moderation_service import load_model



app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

app.include_router(posts.router)

@app.on_event("startup")
def startup_event():
    load_model()

@app.get("/")
def root():
    return {"message": "Loops Moderation API is running"}