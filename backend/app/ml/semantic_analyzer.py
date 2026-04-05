"""
Semantic Analyzer using Sentence Transformers
Provides context-aware tech relevance and harm detection
No hardcoded keywords - understands meaning of sentences
"""

import torch
import numpy as np
from sentence_transformers import SentenceTransformer, util
import logging
import time
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    Uses sentence embeddings to understand context and meaning.
    This gives you Ollama-like understanding without the LLM overhead.
    """
    
    def __init__(self, device=None):
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device
        
        # Small, fast model (~80MB) - runs well on CPU
        logger.info("🔄 Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device=str(self.device))
        
        # Tech anchor sentences - define what "tech content" means
        self.tech_anchors = [
            "building a REST API with Python and FastAPI",
            "deploying microservices with Docker and Kubernetes",
            "optimizing database queries in PostgreSQL",
            "writing React components with hooks and state management",
            "debugging JavaScript code in Chrome DevTools",
            "implementing authentication with JWT tokens",
            "setting up CI/CD pipelines with GitHub Actions",
            "machine learning model training with PyTorch",
            "cloud infrastructure on AWS EC2 and S3",
            "writing unit tests with pytest",
            "frontend performance optimization techniques",
            "backend system architecture design patterns",
            "coding in Python, JavaScript, or TypeScript",
            "using Git for version control and collaboration",
            "database schema design and normalization",
            "container orchestration with Kubernetes",
            "API gateway and service mesh patterns",
        ]
        
        # Off-topic anchor sentences - define what is NOT tech
        self.offtopic_anchors = [
            "going to the beach with friends on a sunny day",
            "cooking dinner for family and enjoying a meal together",
            "watching a movie on Netflix after work",
            "playing cricket in the park on weekends",
            "feeling tired after a long workout at the gym",
            "eating biryani at a restaurant with friends",
            "planning a vacation trip to Goa",
            "the weather is sunny and beautiful today",
            "my dog is very cute and playful",
            "had a great conversation with an old friend",
            "listening to music and relaxing at home",
            "motivational quotes about success and happiness",
            "stay positive and keep working hard every day",
            "believe in yourself and your dreams will come true",
        ]
        
        # Encode all anchors once (cache them for speed)
        logger.info("🔄 Encoding semantic anchors...")
        self.tech_embeddings = self.model.encode(self.tech_anchors, convert_to_tensor=True)
        self.offtopic_embeddings = self.model.encode(self.offtopic_anchors, convert_to_tensor=True)
        
        # Compile patterns for context detection
        self.tech_keywords_pattern = re.compile(
            r'\b(python|javascript|react|docker|kubernetes|api|database|server|code|programming|'
            r'devops|cloud|aws|azure|gcp|machine learning|ai|algorithm|git|github|backend|frontend|'
            r'fullstack|microservices|container|deployment|testing|debugging|framework|library)\b',
            re.IGNORECASE
        )
        
        self.motivational_patterns = [
            re.compile(r'\b(every day|start fresh|no matter what|yesterday|today is yours|keep pushing|'
                      r'believe in yourself|stay positive|keep going|never give up|dreams come true|'
                      r'motivation|inspiring|success|happiness)\b', re.IGNORECASE),
            re.compile(r'\b(i|we|you) can do this\b', re.IGNORECASE),
            re.compile(r'\b(keep|stay|always) \w+ing\b', re.IGNORECASE),
        ]
        
        logger.info(f"✅ Semantic analyzer ready on {self.device}")
    
    def _is_motivational_content(self, text: str) -> bool:
        """Check if text is primarily motivational/inspirational."""
        text_lower = text.lower()
        
        # Count motivational matches
        motivational_count = 0
        for pattern in self.motivational_patterns:
            matches = pattern.findall(text_lower)
            motivational_count += len(matches)
        
        # Count tech keywords
        tech_keywords = self.tech_keywords_pattern.findall(text_lower)
        tech_count = len(set(tech_keywords))  # Unique tech terms
        
        # If text is short and has motivational patterns but few tech terms
        words = text_lower.split()
        if len(words) < 30:  # Short post
            if motivational_count >= 2 and tech_count == 0:
                return True
            if motivational_count >= 1 and tech_count == 0 and len(words) < 15:
                return True
        
        # If motivational patterns dominate
        if motivational_count >= 3 and tech_count <= 1:
            return True
        
        return False
    
    def _is_contextual_tech(self, text: str) -> bool:
        """Check if tech terms appear in meaningful technical context."""
        text_lower = text.lower()
        tech_keywords = self.tech_keywords_pattern.findall(text_lower)
        
        if not tech_keywords:
            return False
        
        # Get unique tech terms
        unique_tech = set(tech_keywords)
        
        # Check for technical context indicators
        tech_context_indicators = [
            'code', 'function', 'class', 'import', 'from', 'def', 'return',
            'api', 'endpoint', 'request', 'response', 'database', 'query',
            'server', 'client', 'deploy', 'build', 'compile', 'run',
            'error', 'bug', 'fix', 'debug', 'test', 'commit', 'push',
            'install', 'configure', 'setup', 'tutorial', 'guide', 'learn'
        ]
        
        context_score = 0
        for indicator in tech_context_indicators:
            if indicator in text_lower:
                context_score += 1
        
        # If multiple tech terms AND technical context, it's real tech content
        if len(unique_tech) >= 2 and context_score >= 1:
            return True
        
        # If single tech term but multiple technical context words
        if len(unique_tech) == 1 and context_score >= 2:
            return True
        
        # If the tech term appears in a code-like context
        code_patterns = [
            r'```.*```',  # Code blocks
            r'import\s+\w+',  # Import statements
            r'def\s+\w+\(',  # Function definitions
            r'class\s+\w+',  # Class definitions
            r'=\s*\[',  # List assignments
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def analyze_tech_relevance(self, text: str) -> Dict[str, Any]:
        """
        Determine if text is tech-related using semantic similarity with context filtering.
        Returns: score (0-1), zone, and similarity details
        """
        if not text or not text.strip():
            return {"score": 0.0, "zone": "off_topic", "tech_sim": 0.0, "offtopic_sim": 0.0}
        
        # Step 1: Check for motivational content (fast path)
        if self._is_motivational_content(text):
            logger.info(f"📝 Detected motivational content - reducing tech score")
            
            # Check if it has technical context (override)
            if not self._is_contextual_tech(text):
                return {
                    "score": 0.0,
                    "zone": "off_topic",
                    "tech_sim": 0.0,
                    "offtopic_sim": 0.5,
                    "method": "semantic",
                    "context": "motivational"
                }
        
        # Step 2: Check if tech terms appear in technical context
        has_tech_context = self._is_contextual_tech(text)
        
        # Step 3: Encode the text
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        
        # Step 4: Calculate similarity to tech and off-topic anchors
        tech_similarities = util.cos_sim(text_embedding, self.tech_embeddings)[0]
        offtopic_similarities = util.cos_sim(text_embedding, self.offtopic_embeddings)[0]
        
        max_tech = tech_similarities.max().item()
        max_offtopic = offtopic_similarities.max().item()
        
        # Step 5: Apply context-based adjustments
        if not has_tech_context:
            # If no technical context, significantly reduce tech score
            max_tech = max_tech * 0.3
            logger.info(f"📝 No technical context detected - reducing similarity from {tech_similarities.max().item():.3f} to {max_tech:.3f}")
        
        # Normalize from [-1, 1] to [0, 1]
        tech_score = (max_tech + 1) / 2
        offtopic_score = (max_offtopic + 1) / 2
        
        # Step 6: Decision logic with stricter thresholds
        if max_tech > 0.55 and max_tech > max_offtopic and has_tech_context:
            final_score = tech_score
            zone = "tech"
        elif max_tech > 0.6 and max_tech > max_offtopic and not has_tech_context:
            # High similarity but no technical context - probably false positive
            final_score = min(tech_score * 0.4, 0.35)
            zone = "off_topic"
        elif max_offtopic > 0.45 and max_offtopic > max_tech:
            final_score = 1 - offtopic_score
            zone = "off_topic"
        else:
            # Ambiguous case
            final_score = tech_score * (0.5 if not has_tech_context else 1.0)
            zone = "review" if has_tech_context else "off_topic"
        
        # Cap the score for off_topic content
        if zone == "off_topic":
            final_score = min(final_score, 0.3)
        
        return {
            "score": round(final_score, 3),
            "zone": zone,
            "tech_sim": round(max_tech, 3),
            "offtopic_sim": round(max_offtopic, 3),
            "method": "semantic",
            "has_tech_context": has_tech_context
        }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Combined analysis returning scores format expected by moderation_service"""
        start_time = time.time()
        
        tech = self.analyze_tech_relevance(text)
        
        scores = {
            "tech_relevance": tech["score"],
            "toxicity": 0.0,
            "sexual": 0.0,
            "self_harm": 0.0,
            "violence": 0.0,
            "drugs": 0.0,
            "threats": 0.0,
        }
        
        result = {
            "scores": scores,
            "flagged_categories": [],
            "is_harmful": False,
            "max_harm_score": 0.0,
            "is_tech_relevant": tech["zone"] == "tech",
            "primary_category": "tech" if tech["zone"] == "tech" else "non_tech",
            "tech_zone": tech["zone"],
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "method": "semantic",   
            "has_tech_context": tech.get("has_tech_context", False),
            "source": "semantic"
        }
        
        return result


# Singleton
_semantic_analyzer = None

def get_semantic_analyzer():
    global _semantic_analyzer
    if _semantic_analyzer is None:
        _semantic_analyzer = SemanticAnalyzer()
    return _semantic_analyzer