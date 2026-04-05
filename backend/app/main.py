"""
Main FastAPI application for Loops Moderation System
Sachinn's responsibility: API setup, middleware, server configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
from app.api import posts, metrics
from app.db.mongodb import mongodb
from app.api import moderation_review

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Loops Content Moderation System",
    description="AI-powered content moderation API",
    version="1.0.0"
)

# Include moderation review router
app.include_router(
    moderation_review.router,
    prefix="/api/review",
    tags=["human-review"]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React / Vite frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up Loops Moderation System")
    
    # Initialize database connection
    try:
        mongodb.connect()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Loops Moderation System")
    
    # Close database connection
    mongodb.close()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Loops Content Moderation System",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "posts": "/api/posts"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "moderation_approach": os.getenv("MODERATION_APPROACH", "ensemble"),
        "services": {
            "api": "operational",
            "moderation": "ready"
        }
    }