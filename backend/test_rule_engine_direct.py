import os
import sys
import json

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.services.rule_engine import RuleEngine

engine = RuleEngine()

cases = [
    "i do not react to this",
    "this is boring",
    "why is this happening",
    "their is a snake named python.",
    "python is a snake. fuck you.",
    "react js is a frontend library",
    "learning spring boot backend",
    "rust is memory safe"
]

results = {}
for text in cases:
    res = engine.check_tech_relevance(text)
    # Check harm rules too to see profanity
    harm = engine.check_rules(text)
    results[text] = {
        "zone": res["zone"],
        "score": res["tech_relevance_score"],
        "details": res.get("details", {}),
        "banned_keywords": harm.get("banned_keywords", []),
        "violations": harm.get("violations", []),
        "rule_score": harm.get("rule_score", 0)
    }

with open("out.json", "w") as f:
    json.dump(results, f, indent=4)
