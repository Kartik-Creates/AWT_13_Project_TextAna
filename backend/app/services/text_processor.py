import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class TextProcessor:
    """Processes and extracts information from text"""
    
    def __init__(self):
        # URL patterns
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Email pattern
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        
        # Phone pattern (simplified)
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
        
        # Mention pattern
        self.mention_pattern = re.compile(r'@(\w+)')
        
        # Hashtag pattern
        self.hashtag_pattern = re.compile(r'#(\w+)')
    
    def extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """Extract and analyze URLs from text"""
        if not text:
            return []
        
        urls = []
        matches = self.url_pattern.finditer(text)
        
        for match in matches:
            url = match.group()
            try:
                parsed = urlparse(url)
                urls.append({
                    "full_url": url,
                    "domain": parsed.netloc,
                    "path": parsed.path,
                    "params": parsed.params,
                    "query": parsed.query,
                    "fragment": parsed.fragment,
                    "is_shortened": self._is_shortened_url(parsed.netloc)
                })
            except:
                urls.append({
                    "full_url": url,
                    "domain": "unknown",
                    "is_shortened": False
                })
        
        return urls
    
    def _is_shortened_url(self, domain: str) -> bool:
        """Check if URL is from a URL shortener"""
        shorteners = {
            'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 
            'short.link', 'rb.gy', 'cutt.ly', 'is.gd', 
            't.co', 'buff.ly', 'tiny.cc', 'tr.im'
        }
        return domain in shorteners
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text"""
        if not text:
            return []
        return self.mention_pattern.findall(text)
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract #hashtags from text"""
        if not text:
            return []
        return self.hashtag_pattern.findall(text)
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        if not text:
            return []
        return self.email_pattern.findall(text)
    
    def extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers"""
        if not text:
            return []
        return self.phone_pattern.findall(text)
    
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get basic text statistics"""
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "avg_word_length": 0,
                "has_uppercase": False,
                "has_numbers": False,
                "has_special_chars": False
            }
        
        words = text.split()
        
        return {
            "char_count": len(text),
            "word_count": len(words),
            "sentence_count": len(re.split(r'[.!?]+', text)) - 1,
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "has_uppercase": any(c.isupper() for c in text),
            "has_numbers": any(c.isdigit() for c in text),
            "has_special_chars": any(not c.isalnum() and not c.isspace() for c in text)
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        return text.strip()