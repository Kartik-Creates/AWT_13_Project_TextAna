#!/usr/bin/env python3
"""
Quick test for Kartik's ML Pipeline
Run this from the backend directory
"""

import os
import sys
from PIL import Image
import numpy as np

# Add the backend directory to Python path
# Get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (backend)
backend_dir = os.path.dirname(current_dir)
# Add to path
sys.path.insert(0, backend_dir)

print("="*60)
print("KARTIK'S ML PIPELINE TEST")
print("="*60)

# Test 1: Check imports
print("\n📦 1. CHECKING IMPORTS...")
try:
    from app.ml.distilbert_model import distilbert_analyzer
    print("   ✅ DistilBERT imported")
    
    from app.ml.efficientnet_model import efficientnet_nsfw
    print("   ✅ EfficientNet imported")
    
    from app.ml.nsfw_model import nsfw_detector
    print("   ✅ NSFW Detector imported")
    
    from app.ml.clip_model import clip_analyzer
    print("   ✅ CLIP imported")
    
    from app.ml.model_loader import model_loader
    print("   ✅ Model Loader imported")
    
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create test image
print("\n🖼️ 2. CREATING TEST IMAGE...")
try:
    test_image_path = "test_ml_image.jpg"
    img = Image.new('RGB', (224, 224), color='blue')
    img.save(test_image_path)
    print(f"   ✅ Test image created: {test_image_path}")
except Exception as e:
    print(f"   ❌ Failed to create test image: {e}")
    sys.exit(1)

# Test 3: Test DistilBERT
print("\n📝 3. TESTING DISTILBERT (Text Analysis)...")
try:
    test_texts = [
        "Hello world, this is a normal post about weather",
        "I hate everyone, you should all die",  # Toxic
        "Check out this link: http://bit.ly/test"  # URL
    ]
    
    for i, text in enumerate(test_texts):
        result = distilbert_analyzer.analyze(text)
        print(f"\n   Text {i+1}: {text[:30]}...")
        print(f"     - Toxicity Score: {result.get('toxicity_score', 0):.3f}")
        print(f"     - Category: {result.get('category', 'unknown')}")
        print(f"     - Is Toxic: {result.get('is_toxic', False)}")
        print(f"     - Flagged Phrases: {len(result.get('flagged_phrases', []))}")
    print("\n   ✅ DistilBERT test complete")
except Exception as e:
    print(f"   ❌ DistilBERT test failed: {e}")

# Test 4: Test EfficientNet
print("\n🔞 4. TESTING EFFICIENTNET (NSFW Detection)...")
try:
    # Test with different images
    test_cases = [
        ("blue_square", Image.new('RGB', (224, 224), color='blue')),
        ("random_noise", Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))),
    ]
    
    for name, img_data in test_cases:
        path = f"test_{name}.jpg"
        img_data.save(path)
        
        result = efficientnet_nsfw.analyze(path)
        print(f"\n   Image: {name}")
        print(f"     - NSFW Probability: {result.get('nsfw_probability', 0):.3f}")
        print(f"     - Is NSFW: {result.get('is_nsfw', False)}")
        print(f"     - Primary Category: {result.get('primary_category', 'unknown')}")
        print(f"     - Using Fallback: {result.get('using_fallback', False)}")
        
        # Cleanup
        os.remove(path)
    
    print("\n   ✅ EfficientNet test complete")
except Exception as e:
    print(f"   ❌ EfficientNet test failed: {e}")

# Test 5: Test NSFW Detector Integration
print("\n🔄 5. TESTING NSFW DETECTOR INTEGRATION...")
try:
    # Create test image
    path = "test_integration.jpg"
    Image.new('RGB', (224, 224), color='red').save(path)
    
    # Test through wrapper
    result1 = nsfw_detector.analyze(path)
    # Test directly
    result2 = efficientnet_nsfw.analyze(path)
    
    print(f"   Through NSFWDetector: {result1.get('is_nsfw', False)}")
    print(f"   Direct EfficientNet: {result2.get('is_nsfw', False)}")
    print(f"   Same instance? {nsfw_detector.detector is efficientnet_nsfw}")
    
    os.remove(path)
    print("   ✅ Integration test complete")
except Exception as e:
    print(f"   ❌ Integration test failed: {e}")

# Test 6: Test CLIP (if available)
print("\n🎯 6. TESTING CLIP (Image-Text)...")
try:
    path = "test_clip.jpg"
    Image.new('RGB', (224, 224), color='green').save(path)
    
    result = clip_analyzer.analyze("a green square", path)
    print(f"   Similarity Score: {result.get('similarity_score', 0):.3f}")
    print(f"   Is Relevant: {result.get('is_relevant', False)}")
    
    os.remove(path)
    print("   ✅ CLIP test complete")
except Exception as e:
    print(f"   ⚠️ CLIP test skipped (might need CLIP installed): {e}")

# Test 7: Test Model Loader
print("\n📦 7. TESTING MODEL LOADER...")
try:
    print(f"   Device: {model_loader.device}")
    print(f"   Models loaded: {list(model_loader._models.keys())}")
    print("   ✅ Model loader working")
except Exception as e:
    print(f"   ❌ Model loader test failed: {e}")

# Cleanup
print("\n🧹 8. CLEANING UP...")
test_files = ['test_ml_image.jpg', 'test_blue_square.jpg', 'test_random_noise.jpg', 
              'test_integration.jpg', 'test_clip.jpg']
for f in test_files:
    if os.path.exists(f):
        os.remove(f)
print("   ✅ Cleanup complete")

print("\n" + "="*60)
print("✅ ML PIPELINE TEST COMPLETE")
print("="*60)

# Summary
print("\n📊 QUICK SUMMARY:")
print("If you see all ✅ above, your ML pipeline is working!")
print("If you see any ❌, check the specific component that failed.")