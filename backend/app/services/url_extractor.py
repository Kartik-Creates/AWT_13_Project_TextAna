"""
URL Extractor Service
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
        # URL patterns
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
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
            '.win', '.bid', '.ren', '.club', '.online', '.site'
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
        matches = self.url_pattern.finditer(text)
        
        for match in matches:
            url = match.group()
            analysis = self.analyze_url(url)
            if analysis:
                urls.append(analysis)
        
        return urls
    
    def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single URL for suspicious characteristics
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with URL analysis or None if invalid
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Basic info
            url_info = {
                "full_url": url,
                "domain": parsed.netloc,
                "path": parsed.path,
                "params": parsed.params,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "scheme": parsed.scheme,
                "is_shortened": self._is_shortened_url(parsed.netloc),
                "has_suspicious_tld": self._has_suspicious_tld(parsed.netloc),
                "has_ip_address": self._is_ip_address(parsed.netloc),
                "num_subdomains": self._count_subdomains(parsed.netloc),
                "url_length": len(url),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            # Additional risk indicators
            url_info["risk_indicators"] = self._get_risk_indicators(url_info)
            url_info["risk_score"] = self._calculate_risk_score(url_info)
            url_info["risk_level"] = self._get_risk_level(url_info["risk_score"])
            
            return url_info
            
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {e}")
            return None
    
    def _is_shortened_url(self, domain: str) -> bool:
        """Check if URL is from a URL shortener"""
        return any(shortener in domain for shortener in self.suspicious_domains)
    
    def _has_suspicious_tld(self, domain: str) -> bool:
        """Check if domain has suspicious TLD"""
        return any(domain.endswith(tld) for tld in self.dangerous_tlds)
    
    def _is_ip_address(self, domain: str) -> bool:
        """Check if domain is an IP address"""
        # Remove port if present
        host = domain.split(':')[0]
        # Check if it's an IP address
        ip_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
        return bool(ip_pattern.match(host))
    
    def _count_subdomains(self, domain: str) -> int:
        """Count number of subdomains"""
        # Remove port if present
        host = domain.split(':')[0]
        parts = host.split('.')
        # For something like sub.domain.com -> parts = ['sub', 'domain', 'com']
        # Number of subdomains = len(parts) - 2 (if at least domain.tld)
        if len(parts) >= 3:
            return len(parts) - 2
        return 0
    
    def _get_risk_indicators(self, url_info: Dict[str, Any]) -> List[str]:
        """Get list of risk indicators for URL"""
        indicators = []
        
        if url_info["is_shortened"]:
            indicators.append("URL shortener used (may hide destination)")
        
        if url_info["has_suspicious_tld"]:
            indicators.append("Suspicious top-level domain")
        
        if url_info["has_ip_address"]:
            indicators.append("IP address used instead of domain name")
        
        if url_info["num_subdomains"] > 2:
            indicators.append("Too many subdomains (possible squatting)")
        
        if url_info["url_length"] > 100:
            indicators.append("Unusually long URL")
        
        # Check for common phishing patterns
        if "login" in url_info["path"].lower() or "signin" in url_info["path"].lower():
            indicators.append("Contains login page path (possible phishing)")
        
        if "secure" in url_info["domain"].lower() or "security" in url_info["domain"].lower():
            indicators.append("Security-related terms in domain (possible fake)")
        
        # Check for multiple subdomains with common brand names
        if "paypal" in url_info["domain"].lower() or "amazon" in url_info["domain"].lower():
            if url_info["num_subdomains"] > 1:
                indicators.append("Brand name in subdomain (possible typosquatting)")
        
        return indicators
    
    def _calculate_risk_score(self, url_info: Dict[str, Any]) -> float:
        """
        Calculate risk score from 0 (safe) to 1 (highly suspicious)
        """
        score = 0.0
        
        # Risk factors and their weights
        if url_info["is_shortened"]:
            score += 0.3
        
        if url_info["has_suspicious_tld"]:
            score += 0.4
        
        if url_info["has_ip_address"]:
            score += 0.5
        
        if url_info["num_subdomains"] > 3:
            score += 0.2
        elif url_info["num_subdomains"] > 2:
            score += 0.1
        
        if url_info["url_length"] > 200:
            score += 0.3
        elif url_info["url_length"] > 100:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level"""
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score > 0:
            return "LOW"
        else:
            return "SAFE"
    
    def resolve_shortened_url(self, short_url: str) -> Optional[str]:
        """
        Try to resolve shortened URL to actual destination
        (Optional - use with caution)
        """
        try:
            response = requests.head(short_url, allow_redirects=True, timeout=5)
            return response.url
        except Exception as e:
            logger.warning(f"Could not resolve shortened URL {short_url}: {e}")
            return None
    
    def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """
        Check domain reputation (basic implementation)
        In production, integrate with threat intelligence APIs
        """
        # Basic checks
        indicators = []
        
        # Check if domain is newly registered (simplified)
        # In production, use WHOIS API
        
        # Check for common malicious patterns
        if any(word in domain.lower() for word in ['secure', 'login', 'verify', 'account']):
            indicators.append("Common phishing terms in domain")
        
        # Check for typosquatting (simplified)
        common_domains = ['google', 'facebook', 'amazon', 'paypal', 'microsoft']
        for common in common_domains:
            if common in domain.lower() and common != domain.lower():
                indicators.append(f"Possible {common} typosquatting")
        
        return {
            "domain": domain,
            "suspicious": len(indicators) > 0,
            "indicators": indicators,
            "checked_at": datetime.utcnow().isoformat()
        }

# Global instance
url_extractor = URLExtractor()