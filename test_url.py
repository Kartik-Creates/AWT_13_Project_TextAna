"""
Standalone debug script for rule engine
Run this to find what's causing the false positive
"""

import re
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)

# ============================================
# MINIMAL RULE ENGINE FOR DEBUGGING
# ============================================

class DebugRuleEngine:
    """Minimal version to debug false positives"""
    
    def __init__(self):
        # Suspicious URL patterns (keep minimal)
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com'
        ]
        
        # Spam patterns (keep minimal)
        self.spam_patterns = [
            r'(.)\1{4,}',
            r'[A-Z]{10,}',
            r'\b(viagra|casino|lottery|winner|congratulations)\b',
        ]
        
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)
        
        # Banned categories
        self.banned_categories = {
            "violence": [
                "kill you", "kill them", "murder", "bomb", "shoot",
                "beat up", "beat you", "beat him", "beat her"
            ],
            "harm": [
                "suicide", "self-harm", "cutting myself", "hang myself",
                "end my life", "want to die", "kill myself", "take my life",
                "better off dead", "no reason to live", "worthless"
            ],
        }
        
        # Compile banned patterns
        self._compiled_banned = {}
        for category, keywords in self.banned_categories.items():
            for kw in keywords:
                escaped = re.escape(kw)
                pattern = rf'\b{escaped}\b'
                self._compiled_banned[re.compile(pattern, re.IGNORECASE)] = (kw, category)
        
        # ALLOWLIST - This is the key fix
        self.allowlist_patterns = [
            # 'die' inside safe words
            r'\bdiscipline\b',
            r'\bdisciplined\b',
            r'\bdisciplines\b',
            r'\bdepends?\s+(?:on|upon)\b',
            r'\bstudied\b',
            r'\bstudies\b',
            r'\bstudying\b',
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdies\b',
            
            # 'beat' in safe contexts
            r'\bbeats?\s+(?:shortcuts|the|everything|all|competition|records?|goals)\b',
            r'\b(?:heart|drum|music)\s+beats?\b',
            
            # 'cut' in safe contexts
            r'\bshortcuts?\b',
            r'\bcut\s+(?:costs|time|effort|corners?)\b',
            
            # Educational/motivational
            r'\blearning\s+(?:new|curve|process)\b',
            r'\bpracticing\s+(?:daily|regularly)\b',
            r'\b(?:coding|programming)\s+(?:skills|practice)\b',
            
            # Safe words
            r'\bkey\s+(?:is|to|factor)\b',
            r'\bgoals?\b',
            r'\bsuccess\b',
            r'\bskills?\b',
            r'\bpractice\b',
            r'\bconsistent\w*\b',
        ]
        
        self._compiled_allowlist = [
            re.compile(p, re.IGNORECASE) for p in self.allowlist_patterns
        ]
    
    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against rules with allowlist masking"""
        text_stripped = text.strip()
        
        results = {
            "banned_keywords": [],
            "keyword_categories": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": [],
            "rule_score": 0.0
        }
        
        if not text_stripped:
            return results
        
        # Step 1: Mask allowlisted spans
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)
        
        print(f"\n🔍 Original: {text_stripped[:100]}...")
        print(f"🔍 Masked:   {masked_text[:100]}...")
        
        # Step 2: Check banned keywords on masked text
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text):
                results["banned_keywords"].append(keyword)
                results["keyword_categories"].append(category)
                results["violations"].append(f"keyword:{keyword}")
                print(f"   ⚠️ MATCHED: '{keyword}' in category '{category}'")
        
        # Step 3: Check suspicious URLs
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = list(set(urls))
            results["violations"].append("suspicious_url")
        
        # Step 4: Check spam
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            results["spam_detected"] = True
            results["violations"].append("spam")
        
        # Step 5: Calculate score
        unique_violations = len(set(results["violations"]))
        
        if unique_violations == 0:
            results["rule_score"] = 0.0
        elif unique_violations == 1:
            if any(cat in ["violence", "harm"] for cat in results["keyword_categories"]):
                results["rule_score"] = 0.5
            else:
                results["rule_score"] = 0.2
        elif unique_violations == 2:
            results["rule_score"] = 0.7
        else:
            results["rule_score"] = 0.8
        
        return results


# ============================================
# TEST THE TEXT
# ============================================

engine = DebugRuleEngine()

test_text = "Technology evolves fast, but success still depends on discipline. Learning new skills, staying updated, and practicing daily are key. Whether coding or chasing goals, consistency always beats shortcuts."

print("="*80)
print("🔍 DEBUGGING FALSE POSITIVE")
print("="*80)

# Test the full text
result = engine.check_rules(test_text)

print("\n" + "="*80)
print("📊 RESULTS:")
print("="*80)
print(f"Rule Score: {result['rule_score']:.2f}")
print(f"Violations: {result['violations']}")
print(f"Banned Keywords: {result['banned_keywords']}")
print(f"Categories: {result['keyword_categories']}")

if result['rule_score'] == 0:
    print("\n✅ SUCCESS! Text would be ALLOWED")
else:
    print(f"\n❌ Text would be BLOCKED (score: {result['rule_score']})")
    print("\n📝 To fix, add these patterns to allowlist:")
    
    # Suggest patterns
    if 'beats' in test_text.lower():
        print('   r\'\\bbeats?\\s+(?:shortcuts|the|everything|all|competition|records?|goals)\\b\',')
    if 'shortcuts' in test_text.lower():
        print('   r\'\\bshortcuts?\\b\',')
    if 'depends' in test_text.lower():
        print('   r\'\\bdepends?\\s+(?:on|upon)\\b\',')
    if 'discipline' in test_text.lower():
        print('   r\'\\bdiscipline\\b\',')

# Test individual words to find the exact culprit
print("\n" + "="*80)
print("🔍 TESTING INDIVIDUAL WORDS")
print("="*80)

words = re.findall(r'\b\w+\b', test_text.lower())
problem_words = []

for word in words:
    result = engine.check_rules(word)
    if result['rule_score'] > 0:
        problem_words.append(word)
        print(f"\n⚠️ Problem word: '{word}'")
        print(f"   Score: {result['rule_score']}")
        print(f"   Violations: {result['violations']}")

if problem_words:
    print(f"\n🚨 Problem words found: {problem_words}")
else:
    print("\n✅ No individual words triggered. The issue is a phrase, not a single word.")
    
    # Test phrases
    phrases = [
        "depends on",
        "beats shortcuts",
        "consistency always beats",
        "learning new skills"
    ]
    
    for phrase in phrases:
        result = engine.check_rules(phrase)
        if result['rule_score'] > 0:
            print(f"\n⚠️ Problem phrase: '{phrase}'")
            print(f"   Score: {result['rule_score']}")
            print(f"   Violations: {result['violations']}")