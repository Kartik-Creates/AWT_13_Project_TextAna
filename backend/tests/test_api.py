"""
API endpoint tests
Sachinn's responsibility: Ensure API endpoints work correctly
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
import tempfile
from PIL import Image

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "version" in response.json()

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_post_text_only():
    """Test creating a post with only text"""
    response = client.post(
        "/api/posts/",
        data={"text": "This is a test post"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "This is a test post"
    assert data["allowed"] is None
    assert "id" in data

def test_create_post_with_image():
    """Test creating a post with image"""
    # Create a test image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        tmp.seek(0)
        
        with open(tmp.name, "rb") as img_file:
            response = client.post(
                "/api/posts/",
                data={"text": "Post with image"},
                files={"image": ("test.jpg", img_file, "image/jpeg")}
            )
    
    os.unlink(tmp.name)
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "Post with image"
    assert data["image_path"] is not None

def test_get_posts():
    """Test getting all posts"""
    response = client.get("/api/posts/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_stats():
    """Test getting statistics"""
    response = client.get("/api/posts/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "allowed" in data
    assert "rejected" in data
    assert "pending" in data

def test_invalid_post_creation():
    """Test post creation with invalid data"""
    response = client.post("/api/posts/", data={"text": ""})
    assert response.status_code == 422  # Validation error

def test_get_nonexistent_post():
    """Test getting a post that doesn't exist"""
    response = client.get("/api/posts/123456789012345678901234")
    assert response.status_code == 404