import os
import re

def fix_all_files():
    backend_dir = r"C:\Users\KARTIK\Desktop\AWT_13_Project_TextAna\backend\app"
    
    # Files to fix and their patterns
    fixes = [
        # Fix 1: Remove backend.app prefix
        {
            'pattern': r'from backend\.app',
            'replacement': 'from app'
        },
        # Fix 2: Remove nsfw_model imports
        {
            'pattern': r'from app\.ml\.nsfw_model.*\n',
            'replacement': ''
        },
        # Fix 3: Make sure efficientnet is used as nsfw_detector
        {
            'pattern': r'from app\.ml\.efficientnet_model import efficientnet_nsfw',
            'replacement': 'from app.ml.efficientnet_model import efficientnet_nsfw as nsfw_detector'
        }
    ]
    
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original = content
                
                # Apply all fixes
                for fix in fixes:
                    content = re.sub(fix['pattern'], fix['replacement'], content)
                
                # Also remove any standalone nsfw_model imports
                content = re.sub(r'import.*nsfw_model.*\n', '', content)
                
                if content != original:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Fixed: {os.path.basename(filepath)}")

if __name__ == "__main__":
    print("🔍 Fixing import errors...")
    fix_all_files()
    print("✅ All fixes applied!")
    print("▶️ Now restart your backend with: python -m uvicorn app.main:app --reload")