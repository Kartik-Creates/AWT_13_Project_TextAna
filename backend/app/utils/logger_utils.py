"""
Clean logging utility for moderation system
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class ModerationLogger:
    """Clean logging for moderation decisions"""
    
    def __init__(self):
        self._last_post_id = None
        self._current_post_id = None
        self._initialization_logged = False
    
    def log_initialization(self, component: str, status: str, error: Optional[str] = None):
        """Log initialization status (only for errors/warnings)"""
        if status == 'error':
            print(f"{Colors.RED}❌ {component} initialization failed{Colors.END}")
            if error:
                print(f"{Colors.DIM}   {error}{Colors.END}")
        elif status == 'warning':
            print(f"{Colors.YELLOW}⚠️ {component} initialization warning{Colors.END}")
            if error:
                print(f"{Colors.DIM}   {error}{Colors.END}")
    
    def start_moderation(self, post_id: str):
        """Log moderation start"""
        self._current_post_id = post_id
        print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}📝 MODERATION REQUEST{Colors.END}")
        print(f"{Colors.DIM}Post ID: {post_id}{Colors.END}")
        print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
    
    def log_rule_engine(self, rule_results: Dict[str, Any]):
        """Log rule engine results"""
        rule_score = rule_results.get('rule_score', 0)
        violations = rule_results.get('violations', [])
        
        status = f"{Colors.RED}BLOCK{Colors.END}" if rule_score > 0.5 else f"{Colors.GREEN}PASS{Colors.END}"
        
        print(f"\n{Colors.YELLOW}🔍 RULE ENGINE{Colors.END}")
        print(f"  Score    : {rule_score:.3f}  [{status}]")
        if violations:
            print(f"  Flags    : {', '.join(violations[:3])}")
    
    def log_tech_scoring(self, tech_score: float, tech_zone: str, source: str, details: Dict[str, Any] = None):
        """Log tech relevance scoring"""
        zone_color = Colors.GREEN if tech_zone == 'tech' else Colors.YELLOW if tech_zone == 'review' else Colors.RED
        status = "TECH" if tech_zone == 'tech' else "REVIEW" if tech_zone == 'review' else "OFF-TOPIC"
        
        print(f"\n{Colors.BLUE}💻 TECH RELEVANCE{Colors.END}")
        print(f"  Model    : {source}")
        print(f"  Score    : {tech_score:.3f}")
        print(f"  Zone     : {zone_color}{status}{Colors.END}")
        
        if details and details.get('strong_anchors_found'):
            print(f"  Terms    : {', '.join(details.get('strong_anchors_found', [])[:5])}")
    
    def log_harm_scores(self, scores: Dict[str, float], flagged: list):
        """Log harm detection scores in table format"""
        print(f"\n{Colors.RED}⚠️ HARM DETECTION{Colors.END}")
        print(f"  {'Category':<12} {'Score':<8} {'Status':<10}")
        print(f"  {'-'*12} {'-'*8} {'-'*10}")
        
        categories = ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats']
        for cat in categories:
            score = scores.get(cat, 0)
            if cat in flagged:
                status = f"{Colors.RED}FLAGGED{Colors.END}"
                color = Colors.RED
            else:
                status = f"{Colors.GREEN}SAFE{Colors.END}"
                color = Colors.GREEN
            print(f"  {cat:<12} {score:.3f}     {color}{status}{Colors.END}")
    
    def log_decision(self, decision: Dict[str, Any], tech_score: float = None):
        """Log final decision"""
        allowed = decision.get('allowed', False)
        reasons = decision.get('reasons', [])
        confidence = decision.get('confidence', 0)
        
        print(f"\n{Colors.CYAN}{'─'*80}{Colors.END}")
        if allowed:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ FINAL DECISION: ALLOWED{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ FINAL DECISION: BLOCKED{Colors.END}")
        
        if tech_score is not None:
            print(f"  Tech Score: {tech_score:.3f}")
        print(f"  Confidence: {confidence:.1%}")
        print(f"  Reasons   : {', '.join(reasons) if reasons else 'No issues detected'}")
        print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    def log_model_status(self, model_name: str, status: str, error: Optional[str] = None):
        """Log model loading status (only for errors/warnings)"""
        if status == 'error':
            print(f"{Colors.RED}❌ MODEL FAILED: {model_name}{Colors.END}")
            if error:
                print(f"{Colors.DIM}   {error}{Colors.END}")
        elif status == 'warning':
            print(f"{Colors.YELLOW}⚠️ MODEL WARNING: {model_name}{Colors.END}")
            if error:
                print(f"{Colors.DIM}   {error}{Colors.END}")
    
    def log_model_used(self, model_name: str, source: str):
        """Log which model was used for moderation"""
        print(f"{Colors.DIM}  Used      : {model_name} ({source}){Colors.END}")


# Global instance
moderation_logger = ModerationLogger()
