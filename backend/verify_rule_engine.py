import os
import sys

# Ensure backend root is in PYTHONPATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.rule_engine import RuleEngine

def run_edge_cases():
    print("Testing Edge Cases for Rule Engine...\n")
    engine = RuleEngine()
    
    cases = [
        # OFF-TOPIC Cases (Should score <= 0.0)
        ("i do not react to this", "off_topic"),
        ("this is boring", "off_topic"),
        ("why is this happening", "off_topic"),
        ("their is a snake named python.", "off_topic"),
        ("python is a snake. fuck you.", "off_topic"),
        
        # TECH Cases (Should score > 0.0 -> tech)
        ("react js is a frontend library", "tech"),
        ("learning spring boot backend", "tech"),
        ("rust is memory safe", "tech")
    ]
    
    passed_all = True
    
    for text, expected_zone in cases:
        print(f"Testing: '{text}'")
        result = engine.check_tech_relevance(text)
        actual_zone = result["zone"]
        score = result["tech_relevance_score"]
        
        print(f"  Zone: {actual_zone} (Expected: {expected_zone})")
        print(f"  Score: {score}")
        print(f"  Details: {result.get('details', {})}")
        
        if actual_zone != expected_zone:
            print(f"  ❌ FAILED")
            passed_all = False
        else:
            print(f"  ✅ PASSED")
        print("-" * 50)
        
    if passed_all:
        print("\n🎉 ALL EDGE CASES PASSED")
        sys.exit(0)
    else:
        print("\n⚠️ SOME EDGE CASES FAILED")
        sys.exit(1)

if __name__ == "__main__":
    run_edge_cases()
