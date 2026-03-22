"""
URL Extractor Service - ENHANCED
Extracts and analyzes URLs from text content
"""

import re
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
import socket
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class URLExtractor:
    """Extract and analyze URLs from text"""
    
    def __init__(self):
        # IMPROVED URL PATTERN - catches more URLs including those with special chars
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[-\w$.+!*\'(),;:@&=?/~#%]*)?',
            re.IGNORECASE
        )
        
        # Even more aggressive pattern for bit.ly and shortened URLs
        self.shortened_url_pattern = re.compile(
            r'(?:bit\.ly|tinyurl\.com|goo\.gl|ow\.ly|short\.link|rb\.gy|cutt\.ly|is\.gd|t\.co|buff\.ly|tiny\.cc|tr\.im)/[A-Za-z0-9]+',
            re.IGNORECASE
        )
        
        # Suspicious domain patterns
        self.suspicious_domains = [
            'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 'short.link',
            'rb.gy', 'cutt.ly', 'is.gd', 't.co', 'buff.ly', 'tiny.cc',
            'tr.im', 'shrten.com', 'shortener', 'urlshortener'
        ]
        
        # Dangerous TLDs
        self.dangerous_tlds = [
            '.xyz', '.top', '.work', '.date', '.loan', '.download',
            '.win', '.bid', '.ren', '.club', '.online', '.site', '.click',
            '.link', '.help', '.fail', '.info', '.me', '.pw', '.cc'
        ]
        
        # SCAM/PHISHING keywords in URLs
        self.scam_keywords = [
            'free', 'bonus', 'prize', 'winner', 'claim', 'gift', 'reward',
            'cash', 'money', 'lottery', 'jackpot', 'offer', 'limited',
            'congratulations', 'won', 'earn', 'quick', 'easy', 'click',
            '₹', 'rs', 'rupees', 'dollar', '$', 'pound', '£', 'bitcoin',
            'crypto', 'wallet', 'verify', 'login', 'account', 'secure',
            'update', 'confirm', 'urgent', 'important', 'alert'
        ]
    
    def extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract all URLs from text and analyze them
        
        Args:
            text: Text content to extract URLs from
            
        Returns:
            List of dictionaries with URL information
        """
        urls = []
        
        # First, try to find URLs with the main pattern
        matches = self.url_pattern.finditer(text)
        
        for match in matches:
            url = match.group()
            
            # Clean up URL (remove trailing punctuation)
            url = url.rstrip('.,!?;:')
            
            analysis = self.analyze_url(url)
            if analysis:
                urls.append(analysis)
        
        # Also check for shortened URLs explicitly
        short_matches = self.shortened_url_pattern.finditer(text)
        for match in short_matches:
            url = match.group()
            if not any(u['full_url'] == url for u in urls):
                analysis = self.analyze_url(url)
                if analysis:
                    urls.append(analysis)
        
        return urls
    
    def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single URL for suspicious characteristics
        """
        try:
            # Ensure URL has scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Parse URL
            parsed = urlparse(url)
            
            # Get domain without port
            domain = parsed.netloc.split(':')[0]
            
            # Check for scam keywords in URL
            has_scam_keywords, scam_matches = self._check_scam_keywords(url)
            
            # Basic info
            url_info = {
                "full_url": url,
                "domain": domain,
                "path": parsed.path,
                "params": parsed.params,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "scheme": parsed.scheme,
                "is_shortened": self._is_shortened_url(domain),
                "has_suspicious_tld": self._has_suspicious_tld(domain),
                "has_ip_address": self._is_ip_address(domain),
                "has_scam_keywords": has_scam_keywords,
                "scam_keywords_found": scam_matches,
                "num_subdomains": self._count_subdomains(domain),
                "url_length": len(url),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            # Additional risk indicators
            url_info["risk_indicators"] = self._get_risk_indicators(url_info)
            url_info["risk_score"] = self._calculate_risk_score(url_info)
            url_info["risk_level"] = self._get_risk_level(url_info["risk_score"])
            
            # Log suspicious URLs
            if url_info["risk_level"] in ["MEDIUM", "HIGH"]:
                logger.warning(f"🚨 Suspicious URL detected: {url} - Risk: {url_info['risk_level']} ({url_info['risk_score']:.2f})")
                if url_info["has_scam_keywords"]:
                    logger.warning(f"   Scam keywords: {url_info['scam_keywords_found']}")
            
            return url_info
            
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {e}")
            return None
    
    def _check_scam_keywords(self, url: str) -> tuple:
        """Check if URL contains scam/phishing keywords"""
        url_lower = url.lower()
        found_keywords = []
        
        for keyword in self.scam_keywords:
            if keyword.lower() in url_lower:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords[:5]  # Limit to first 5
    
    def _is_shortened_url(self, domain: str) -> bool:
        """Check if URL is from a URL shortener"""
        return any(shortener in domain for shortener in self.suspicious_domains)
    
    def _has_suspicious_tld(self, domain: str) -> bool:
        """Check if domain has suspicious TLD"""
        return any(domain.endswith(tld) for tld in self.dangerous_tlds)
    
    def _is_ip_address(self, domain: str) -> bool:
        """Check if domain is an IP address"""
        ip_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
        return bool(ip_pattern.match(domain))
    
    def _count_subdomains(self, domain: str) -> int:
        """Count number of subdomains"""
        parts = domain.split('.')
        if len(parts) >= 3:
            return len(parts) - 2
        return 0
    
    def _get_risk_indicators(self, url_info: Dict[str, Any]) -> List[str]:
        """Get list of risk indicators for URL"""
        indicators = []
        
        if url_info["is_shortened"]:
            indicators.append("⚠️ URL shortener used (hides destination)")
        
        if url_info["has_suspicious_tld"]:
            indicators.append("⚠️ Suspicious top-level domain")
        
        if url_info["has_ip_address"]:
            indicators.append("⚠️ IP address used instead of domain name")
        
        if url_info["has_scam_keywords"]:
            indicators.append(f"🚨 SCAM ALERT: Contains keywords - {', '.join(url_info['scam_keywords_found'][:3])}")
        
        if url_info["num_subdomains"] > 2:
            indicators.append("Too many subdomains (possible squatting)")
        
        if url_info["url_length"] > 100:
            indicators.append("Unusually long URL")
        
        # Check for common phishing patterns
        if "login" in url_info["path"].lower() or "signin" in url_info["path"].lower():
            indicators.append("Contains login page path (possible phishing)")
        
        if "secure" in url_info["domain"].lower() or "security" in url_info["domain"].lower():
            indicators.append("Security-related terms in domain (possible fake)")
        
        return indicators
    
    def _calculate_risk_score(self, url_info: Dict[str, Any]) -> float:
        """
        Calculate risk score from 0 (safe) to 1 (highly suspicious)
        """
        score = 0.0
        
        # Risk factors and their weights - STRICTER
        if url_info["is_shortened"]:
            score += 0.5  # Increased from 0.3
        
        if url_info["has_suspicious_tld"]:
            score += 0.5  # Increased from 0.4
        
        if url_info["has_ip_address"]:
            score += 0.6  # Increased from 0.5
        
        # SCAM KEYWORDS - MAJOR RISK
        if url_info["has_scam_keywords"]:
            keyword_count = len(url_info["scam_keywords_found"])
            score += min(0.4 + (keyword_count * 0.1), 0.7)  # Up to 0.7 for multiple keywords
        
        if url_info["num_subdomains"] > 3:
            score += 0.3
        elif url_info["num_subdomains"] > 2:
            score += 0.2
        
        if url_info["url_length"] > 200:
            score += 0.4
        elif url_info["url_length"] > 100:
            score += 0.2
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level - STRICTER thresholds"""
        if score >= 0.5:  # Lowered from 0.7
            return "HIGH"
        elif score >= 0.3:  # Lowered from 0.4
            return "MEDIUM"
        elif score > 0:
            return "LOW"
        else:
            return "SAFE"
    
    def get_url_summary(self, urls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of URL analysis results
        """
        if not urls:
            return {
                "total_urls": 0,
                "suspicious_count": 0,
                "has_suspicious": False,
                "has_scam": False,
                "max_risk_score": 0.0,
                "risk_levels": {"SAFE": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0}
            }
        
        summary = {
            "total_urls": len(urls),
            "suspicious_count": 0,
            "has_suspicious": False,
            "has_scam": False,
            "max_risk_score": 0.0,
            "risk_levels": {"SAFE": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "urls": urls
        }
        
        for url in urls:
            risk_level = url["risk_level"]
            summary["risk_levels"][risk_level] += 1
            summary["max_risk_score"] = max(summary["max_risk_score"], url["risk_score"])
            
            if risk_level in ["MEDIUM", "HIGH"]:
                summary["suspicious_count"] += 1
                summary["has_suspicious"] = True
            
            if url.get("has_scam_keywords", False):
                summary["has_scam"] = True
        
        return summary

# Global instance
url_extractor = URLExtractor()