# integration_test.py
from backend.app.services.url_extractor import url_extractor
from backend.app.services.rule_engine import rule_engine
from backend.app.services.decision_engine import decision_engine

# Initialize
rule_engine = rule_engine()
decision_engine = decision_engine()

# Test with various content
test_cases = [
    {
        "text": "Check out this cool site: https://bit.ly/3abc123",
        "expected": "Should be blocked (suspicious URL)"
    },
    {
        "text": "Normal tech content about Python programming",
        "expected": "Should be allowed"
    },
    {
        "text": "Visit http://suspicious.xyz/login now!",
        "expected": "Should be blocked (suspicious TLD + login path)"
    },
    {
        "text": "I want to die, no reason to live",
        "expected": "Should be blocked (self-harm keywords)"
    }
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"📝 Testing: {test['text']}")
    print(f"🎯 Expected: {test['expected']}")
    
    # Extract URLs
    urls = url_extractor.extract_urls(test['text'])
    has_suspicious_urls = False
    
    if urls:
        print(f"🔗 Found {len(urls)} URL(s):")
        for url in urls:
            print(f"  - {url['full_url']} (risk: {url['risk_level']}, score: {url['risk_score']})")
            if url['risk_score'] > 0.4:
                has_suspicious_urls = True
                print(f"    ⚠️ Suspicious! Indicators: {url['risk_indicators']}")
    
    # Check rules
    rule_results = rule_engine.check_rules(test['text'])
    print(f"📊 Rule Score: {rule_results['rule_score']:.2f}")
    if rule_results['violations']:
        print(f"🚫 Violations: {rule_results['violations']}")
    
    # Make decision
    decision = decision_engine.make_decision({
        'rule_score': rule_results['rule_score'],
        'has_suspicious_urls': has_suspicious_urls,
        'text_score': 0.5,  # Placeholder
        'toxicity_score': 0,
        'sexual_score': 0,
        'self_harm_score': 0,
        'violence_score': 0,
        'drugs_score': 0,
        'threats_score': 0,
        'nsfw_score': 0,
        'is_harmful': False
    })
    
    print(f"✅ Decision: {'ALLOWED' if decision['allowed'] else 'BLOCKED'}")
    print(f"📌 Reasons: {decision['reasons']}")
    print(f"📊 Confidence: {decision['confidence']:.2f}")