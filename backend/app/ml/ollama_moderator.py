"""
Ollama Text Moderator — Enhanced with precise prompt
"""

import requests
import json
import os
import sys
import re
import time
import hashlib
from typing import Dict, Any

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_MAX_INPUT = int(os.getenv("OLLAMA_MAX_INPUT", "500"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "150"))


class OllamaModerator:
    def __init__(self):
        self.host = OLLAMA_HOST
        self.model = OLLAMA_MODEL
        self.max_input = OLLAMA_MAX_INPUT
        self.max_tokens = OLLAMA_MAX_TOKENS
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        print(f"🔥 OllamaModerator initialized with model: {self.model}")
        sys.stdout.flush()
        
        self._available = self._check_availability()
        if not self._available:
            print(f"⚠️ Ollama not available. Using fallback.")
        sys.stdout.flush()
    
    def _check_availability(self) -> bool:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            available = any(self.model == m or m.startswith(f"{self.model}:") for m in models)
            if available:
                print(f"✅ Ollama model '{self.model}' is available")
            else:
                print(f"⚠️ Model '{self.model}' not found. Run: ollama pull {self.model}")
            sys.stdout.flush()
            return available
        except Exception as e:
            print(f"⚠️ Cannot connect to Ollama: {e}")
            sys.stdout.flush()
            return False
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text[:200].encode()).hexdigest()
    
    def _call_ollama(self, text: str) -> str:
        """Enhanced Ollama API call with precise prompt"""
        if not self._available:
            return ""
        
        # Enhanced prompt with clear examples and format
        prompt = f"""Analyze this text for content moderation. Return ONLY valid JSON with 7 scores.

REQUIRED JSON FORMAT:
{{"tech_relevance":0.0-1.0, "toxicity":0.0-1.0, "sexual":0.0-1.0, "self_harm":0.0-1.0, "violence":0.0-1.0, "drugs":0.0-1.0, "threats":0.0-1.0}}

SCORING RULES:
- tech_relevance: 1.0 = software/coding/tech topic, 0.0 = not tech
  Examples: "python programming" = 0.9, "python weather today" = 0.1
  
- toxicity: hate speech, insults, aggressive language
- sexual: sexual harassment, explicit content, coercion
- self_harm: suicide, self-injury, ending life
- violence: physical harm, murder, assault
- drugs: illegal substances, dealing, buying
- threats: intimidation, stalking, blackmail

Text: {text[:self.max_input]}

JSON:"""
        
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": self.max_tokens,
                        "top_k": 20,
                        "top_p": 0.95,
                        "repeat_penalty": 1.1,
                    }
                },
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
        return ""
    
    def analyze(self, text: str) -> Dict[str, Any]:
        start = time.time()
        
        if not text or not text.strip():
            return self._fallback("")
        
        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            self._cache_hits += 1
            print(f"🔥 Cache hit! (hits={self._cache_hits}, misses={self._cache_misses})")
            return self._cache[cache_key]
        
        self._cache_misses += 1
        print(f"🔥 Calling Ollama...")
        sys.stdout.flush()
        
        response = self._call_ollama(text)
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            json_match = re.search(r'\{[^{}]*"tech_relevance"[^{}]*\}', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group())
                
                # Extract scores with defaults
                tech_score = float(data.get("tech_relevance", 0.5))
                tech_score = max(0.0, min(1.0, tech_score))
                
                tech_zone = "tech" if tech_score > 0.45 else ("review" if tech_score > 0.25 else "off_topic")
                
                result = {
                    "scores": {
                        "tech_relevance": tech_score,
                        "toxicity": float(data.get("toxicity", 0)),
                        "sexual": float(data.get("sexual", 0)),
                        "self_harm": float(data.get("self_harm", 0)),
                        "violence": float(data.get("violence", 0)),
                        "drugs": float(data.get("drugs", 0)),
                        "threats": float(data.get("threats", 0)),
                    },
                    "flagged_categories": [],
                    "is_harmful": any(data.get(cat, 0) > 0.5 for cat in ["toxicity", "sexual", "self_harm", "violence", "drugs", "threats"]),
                    "is_tech_relevant": tech_score > 0.45,
                    "primary_category": "tech" if tech_score > 0.45 else "safe",
                    "tech_zone": tech_zone,
                    "processing_time_ms": int((time.time() - start) * 1000),
                }
                
                # Cache result
                if len(self._cache) < 200:
                    self._cache[cache_key] = result
                
                print(f"✅ Ollama result: tech={tech_score:.3f}")
                sys.stdout.flush()
                return result
        except Exception as e:
            print(f"Parse error: {e}")
        
        # Fallback to keyword detection
        return self._fallback(text)
    
    def _fallback(self, text: str) -> Dict[str, Any]:
        """Fast fallback when Ollama is slow or unavailable"""
        text_lower = text.lower()
        tech_keywords = [
            'python', 'react', 'docker', 'api', 'code', 'database', 
            'backend', 'frontend', 'microservices', 'kubernetes', 
            'cloud', 'data', 'analytics', 'insights', 'algorithm',
            'programming', 'software', 'developer', 'engineering'
        ]
        tech_score = sum(1 for kw in tech_keywords if kw in text_lower) * 0.1
        tech_score = min(tech_score, 0.9)
        
        # Check for harmful keywords
        harmful = False
        harm_categories = []
        
        harmful_keywords = {
            'toxicity': ['hate', 'stupid', 'idiot', 'useless'],
            'sexual': ['nudes', 'sext', 'sex tape', 'rape'],
            'self_harm': ['suicide', 'kill myself', 'end my life'],
            'violence': ['kill you', 'murder', 'bomb'],
            'drugs': ['heroin', 'cocaine', 'drug dealer'],
            'threats': ['coming for you', 'i know where you live']
        }
        
        scores = {
            'tech_relevance': tech_score,
            'toxicity': 0, 'sexual': 0, 'self_harm': 0,
            'violence': 0, 'drugs': 0, 'threats': 0
        }
        
        for cat, keywords in harmful_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[cat] = 0.8
                    harmful = True
                    break
        
        tech_zone = "tech" if tech_score > 0.45 else ("review" if tech_score > 0.25 else "off_topic")
        
        return {
            "scores": scores,
            "flagged_categories": [cat for cat, val in scores.items() if val > 0.5 and cat != 'tech_relevance'],
            "is_harmful": harmful,
            "is_tech_relevant": tech_score > 0.45,
            "primary_category": "tech" if tech_score > 0.45 else ("harmful" if harmful else "safe"),
            "tech_zone": tech_zone,
            "processing_time_ms": 5,
        }


_ollama_moderator = None


def get_ollama_moderator():
    global _ollama_moderator
    if _ollama_moderator is None:
        _ollama_moderator = OllamaModerator()
    return _ollama_moderator