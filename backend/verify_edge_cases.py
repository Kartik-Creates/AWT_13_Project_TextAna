import os
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.dirname(__file__))

from app.services.rule_engine import RuleEngine

engine = RuleEngine()

off_topic_tests = [
    "i do not react to this",
    "this is boring",
    "i love this thing",
    "why is this happening"
]

tech_tests = [
    "react js is a frontend library",
    "how to build api in node",
    "spring boot backend issue",
    "python script for data processing"
]

print("--- OFF TOPIC TESTS (Should be <= 0) ---")
for t in off_topic_tests:
    res = engine.check_tech_relevance(t)
    print(f"'{t}' -> score: {res['tech_relevance_score']}, zone: {res['zone']}")

print("\n--- TECH TESTS (Should be > 0) ---")
for t in tech_tests:
    res = engine.check_tech_relevance(t)
    print(f"'{t}' -> score: {res['tech_relevance_score']}, zone: {res['zone']}")
