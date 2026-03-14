import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TextPreprocessor:
    """Text preprocessing utilities"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\'\"]', '', text)
        
        return text.strip()
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple tokenization"""
        return text.split()
    
    @staticmethod
    def remove_stopwords(tokens: List[str]) -> List[str]:
        """Remove common stopwords"""
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because',
            'as', 'what', 'which', 'this', 'that', 'these', 'those',
            'then', 'just', 'so', 'than', 'such', 'both', 'through',
            'about', 'for', 'is', 'of', 'while', 'during', 'to', 'from'
        }
        return [t for t in tokens if t not in stopwords]
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize unicode characters"""
        try:
            import unicodedata
            return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        except:
            return text

class ImagePreprocessor:
    """Image preprocessing utilities"""
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """Validate if image can be processed"""
        try:
            from PIL import Image
            img = Image.open(image_path)
            img.verify()
            return True
        except:
            return False
    
    @staticmethod
    def get_image_info(image_path: str) -> Dict[str, Any]:
        """Get basic image information"""
        try:
            from PIL import Image
            import os
            
            img = Image.open(image_path)
            
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "file_size": os.path.getsize(image_path)
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}