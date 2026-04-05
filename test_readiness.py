import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    logger.info("Testing ML library imports...")
    try:
        import torch
        import transformers
        from sentence_transformers import SentenceTransformer
        import pymongo
        logger.info(f"✅ Imports successful!")
        logger.info(f"   - torch version: {torch.__version__}")
        logger.info(f"   - transformers version: {transformers.__version__}")
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_mongodb():
    logger.info("Testing MongoDB connection...")
    try:
        # Add backend to sys.path to import from app
        sys.path.append(os.path.join(os.getcwd(), "backend"))
        from app.db.mongodb import mongodb
        
        mongodb.connect()
        logger.info("✅ MongoDB connected successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False

def test_fastapi_init():
    logger.info("Testing FastAPI app initialization...")
    try:
        # Import the app to trigger startup events (or just check if it can be imported)
        from app.main import app
        logger.info("✅ FastAPI app imported successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ FastAPI app initialization failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== Starting Readiness Verification ===")
    
    # Run tests
    import_ok = test_imports()
    db_ok = test_mongodb()
    app_ok = test_fastapi_init()
    
    print("\n--- Summary ---")
    print(f"Imports: {'PASS' if import_ok else 'FAIL'}")
    print(f"MongoDB: {'PASS' if db_ok else 'FAIL'}")
    print(f"FastAPI: {'PASS' if app_ok else 'FAIL'}")
    
    if import_ok and db_ok and app_ok:
        print("\n🚀 PROJECT IS READY TO RUN!")
        sys.exit(0)
    else:
        print("\n⚠️ PROJECT HAS ISSUES.")
        sys.exit(1)
