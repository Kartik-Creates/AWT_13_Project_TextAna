import re
from typing import Dict, Any, List, Set
import logging

logger = logging.getLogger(__name__)

class RuleEngine:
    """Rule-based content filtering"""
    
    def __init__(self):
        # Load banned keywords
        self.banned_keywords = self._load_banned_keywords()
        
        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly',
            r'tinyurl\.com',
            r'goo\.gl',
            r'ow\.ly',
            r'short\.link',
            r'rb\.gy',
            r'cutt\.ly',
            r'is\.gd',
            r't\.co',
            r'buff\.ly'
        ]
        
        # Spam patterns
        self.spam_patterns = [
            r'(.)\1{4,}',  # Repeated characters
            r'[A-Z]{5,}',   # ALL CAPS
            r'\b(viagra|cialis|casino|lottery|prize|winner)\b',
            r'\b(free money|work from home|earn money|make money)\b'
        ]
        
        # Compile regex patterns
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)
    
    def _load_banned_keywords(self) -> Set[str]:
        """Load banned keywords from file or define them"""
        # In production, load from database or file
        return {
            # Hate speech
            'hate', 'racist', 'sexist', 'bigot', 'nazi',
            
            # Violence
            'kill', 'murder', 'assassinate', 'torture', 'bomb',
            
            # Explicit content
            'porn', 'xxx', 'nsfw', 'explicit',
            
            # Self-harm
            'suicide', 'selfharm', 'cutting',
            
            # Scams
            'scam', 'fraud', 'phishing'
        }
    
    def check_rules(self, text: str) -> Dict[str, Any]:
        """
        Check text against all rules
        Returns: Dict with rule violations
        """
        text_lower = text.lower()
        
        results = {
            "banned_keywords": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "spam_patterns": [],
            "violations": []
        }
        
        # Check banned keywords
        for keyword in self.banned_keywords:
            if keyword in text_lower:
                results["banned_keywords"].append(keyword)
                results["violations"].append(f"banned_keyword:{keyword}")
        
        # Check suspicious URLs
        urls = self.url_regex.findall(text_lower)
        if urls:
            results["suspicious_urls"] = urls
            for url in urls:
                results["violations"].append(f"suspicious_url:{url}")
        
        # Check spam patterns
        spam_matches = self.spam_regex.findall(text)
        if spam_matches:
            results["spam_detected"] = True
            results["spam_patterns"] = spam_matches
            for pattern in spam_matches:
                if pattern:
                    results["violations"].append(f"spam_pattern:{pattern}")
        
        # Calculate rule score (0-1, higher means more violations)
        violation_count = len(results["violations"])
        results["rule_score"] = min(violation_count / 10, 1.0)
        
        return results