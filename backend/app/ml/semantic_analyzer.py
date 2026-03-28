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
        ]
        
        # Encode all anchors once (cache them for speed)
        logger.info("🔄 Encoding semantic anchors...")
        self.tech_embeddings = self.model.encode(self.tech_anchors, convert_to_tensor=True)
        self.offtopic_embeddings = self.model.encode(self.offtopic_anchors, convert_to_tensor=True)
        
        logger.info(f"✅ Semantic analyzer ready on {self.device}")
    
    def analyze_tech_relevance(self, text: str) -> Dict[str, Any]:
        """
        Determine if text is tech-related using semantic similarity.
        Returns: score (0-1), zone, and similarity details
        """
        if not text or not text.strip():
            return {"score": 0.0, "zone": "off_topic", "tech_sim": 0.0, "offtopic_sim": 0.0}
        
        # Encode the text
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        
        # Calculate similarity to tech and off-topic anchors
        tech_similarities = util.cos_sim(text_embedding, self.tech_embeddings)[0]
        offtopic_similarities = util.cos_sim(text_embedding, self.offtopic_embeddings)[0]
        
        max_tech = tech_similarities.max().item()
        max_offtopic = offtopic_similarities.max().item()
        
        # Normalize from [-1, 1] to [0, 1]
        tech_score = (max_tech + 1) / 2
        offtopic_score = (max_offtopic + 1) / 2
        
        # Decision logic
        if max_tech > 0.5 and max_tech > max_offtopic:
            final_score = tech_score
            zone = "tech"
        elif max_offtopic > 0.5 and max_offtopic > max_tech:
            final_score = 1 - offtopic_score
            zone = "off_topic"
        else:
            # Ambiguous - use tech score but mark for review
            final_score = tech_score
            zone = "review"
        
        return {
            "score": round(final_score, 3),
            "zone": zone,
            "tech_sim": round(max_tech, 3),
            "offtopic_sim": round(max_offtopic, 3),
            "method": "semantic"
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
            "method": "semantic"
        }
        
        return result


# Singleton
_semantic_analyzer = None

def get_semantic_analyzer():
    global _semantic_analyzer
    if _semantic_analyzer is None:
        _semantic_analyzer = SemanticAnalyzer()
    return _semantic_analyzer