import re
from typing import List, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)

class RuleEngine:
    """Rule-based content filtering (Professional Grade)"""
    
    def __init__(self):
        # Core categories of harmful content
        self.banned_categories = {
            "drugs": {"drugs", "heroin", "cocaine", "weed", "meth", "fentanyl", "pills", "dealer"},
            "violence": {"kill", "murder", "bomb", "shoot", "attack", "death", "die"},
            "harm": {"suicide", "self-harm", "cutting", "hang myself"},
            "offensive": {"hate", "racist", "sexist", "nazi", "terrorist"},
            "promotional": {"earn money", "make money", "work from home", "zero effort", "no investment", "cash prize"}
        }
        
        # Flatten for quick lookup
        self.all_banned_keywords = set()
        for keywords in self.banned_categories.values():
            self.all_banned_keywords.update(keywords)

        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes'
        ]
        
        # Spam patterns
        self.spam_patterns = [
            r'(.)\1{4,}',  # Repeated characters (aaaaa)
            r'[A-Z]{10,}',  # Long all caps
            r'\b(viagra|casino|lottery|winner|congratulations|prize)\b'
        ]
        
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)

    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all rules"""
        text_lower = text.lower().strip()
        
        results = {
            "banned_keywords": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": []
        }
        
        if not text_lower:
            return results

        # 1. Check Keywords
        for keyword in self.all_banned_keywords:
            if keyword in text_lower:
                # Basic context check: don't block if just saying "I hate bugs"
                if keyword == "hate" and "bugs" in text_lower:
                    continue
                results["banned_keywords"].append(keyword)
                results["violations"].append(f"keyword:{keyword}")
        
        # 2. Check Suspicious URLs
        urls = self.url_regex.findall(text_lower)
        if urls:
            results["suspicious_urls"] = urls
            results["violations"].append("suspicious_url")
        
        # 3. Check Spam
        spam_matches = self.spam_regex.findall(text)
        if spam_matches:
            # Only count as spam if it has multiple indicators or direct scam language
            if len(spam_matches) > 1 or any(kw in text_lower for kw in ["earn money", "winner"]):
                results["spam_detected"] = True
                results["violations"].append("spam")
        
        # Calculate rule score (0.0 to 1.0)
        # One banned keyword is now a 0.5 score (significant)
        unique_violations = len(set(results["violations"]))
        results["rule_score"] = min(unique_violations * 0.5, 1.0)
        
        return results