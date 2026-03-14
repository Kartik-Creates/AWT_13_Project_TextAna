from fastapi import FastAPI
from app.core.config import settings
from app.api import posts

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

app.include_router(posts.router)

@app.get("/")
def root():
    return {"message": "Loops Moderation API is running"}