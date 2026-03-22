"""
Model sanity check — run from backend root:
  python test_models.py

Prints a clear PASS / FAIL for every test case so you can
see at a glance whether each model is doing its job.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── colour helpers for terminal output ──
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg): print(f"  {RED}❌ FAIL{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠️  WARN{RESET}  {msg}")
def hdr(msg):  print(f"\n{BOLD}{CYAN}{msg}{RESET}")
def sep():     print("─" * 60)

# ──────────────────────────────────────────────────────────────
#  Test data
#  Each entry: (label, text, expected_allowed)
# ──────────────────────────────────────────────────────────────

TECH_POSTS = [
    ("UX + frontend/backend",
     "User experience defines the success of any application. Fast loading, smooth interactions, and intuitive design keep users engaged. Combining frontend performance with strong backend systems creates powerful and reliable digital products.",
     True),
    ("Microservices + cloud",
     "Modern applications rely on scalable architectures. Microservices, cloud computing, and containerization help handle millions of users efficiently.",
     True),
    ("Security + encryption",
     "Security in tech applications is critical. Protecting user data through encryption, authentication, and secure APIs ensures trust. With increasing cyber threats, developers must prioritize security.",
     True),
    ("WebSockets + real-time",
     "Real-time communication is transforming modern apps. Technologies like WebSockets and event-driven systems make instant messaging possible. Building fast and responsive systems is now essential.",
     True),
    ("Python + Docker stack",
     "Just deployed my FastAPI app on Kubernetes using Helm charts! Python + React + Docker is my go-to stack.",
     True),
    ("Data + databases",
     "Data is the backbone of every tech platform. Everything stored in databases helps generate insights. Analyzing this data allows companies to improve features and personalize experiences.",
     True),
]

OFF_TOPIC_POSTS = [
    ("Motivational quote",
     "Growth doesn't happen overnight. Small consistent efforts every day lead to big results. Stay patient, trust the process.",
     False),
    ("Cricket / sports",
     "What a match! India won by 6 wickets in the final over. Rohit Sharma played an amazing innings today at the stadium.",
     False),
    ("Food / recipe",
     "Made the best biryani today! The secret is slow cooking the rice with whole spices and saffron. Perfect for family dinners.",
     False),
    ("Bollywood celebrity",
     "Watched the new Bollywood movie last night. The acting was incredible and the songs are already trending everywhere.",
     False),
]

HARMFUL_POSTS = [
    ("Direct death threat",
     "I will kill you tonight. Watch your back.",
     False),
    ("Drug dealing",
     "fent plug available, best prices, hmu for white powder for sale",
     False),
    ("Self-harm intent",
     "I want to kill myself. No reason to live anymore. End it all tonight.",
     False),
    ("Hindi abuse",
     "teri maa ki chut bhosdike madarchod",
     False),
    ("Sexual blackmail",
     "I found your photos. Send me more or I will share these with everyone.",
     False),
    ("Hate speech",
     "certain people are destroying this country they need to be removed from society",
     False),
]

EDGE_CASES = [
    ("Tech + mild spam signal",
     "Real-time systems are essential for modern apps. WebSockets, event-driven architecture, and pub/sub messaging make it possible.",
     True),
    ("Tech with word 'strong'",
     "Strong backend systems combined with efficient database queries create reliable and scalable digital products.",
     True),
    ("Tech with word 'kill'",
     "This new React hook completely kills boilerplate code. Such an overkill feature but I love it.",
     True),
    ("Empty text",
     "",
     False),  # should block or review
]


# ──────────────────────────────────────────────────────────────
#  Test 1 — Rule engine
# ──────────────────────────────────────────────────────────────

def test_rule_engine():
    hdr("TEST 1 — Rule engine (check_rules + check_tech_relevance)")
    sep()
    from app.services.rule_engine import RuleEngine
    engine = RuleEngine()

    passes = 0
    total  = 0

    # Tech relevance
    print(f"\n  {BOLD}Tech relevance scoring:{RESET}")
    for label, text, expected_allowed in TECH_POSTS + OFF_TOPIC_POSTS + EDGE_CASES:
        if not text:
            continue
        result = engine.check_tech_relevance(text)
        score  = result["tech_relevance_score"]
        zone   = result["zone"]
        cats   = result["matched_categories"]
        expected_zone = "tech" if expected_allowed else "off_topic"

        total += 1
        if expected_allowed and zone == "tech":
            ok(f"{label:<35} score={score:.3f}  zone={zone}  cats={cats}")
            passes += 1
        elif not expected_allowed and zone in ("off_topic", "review"):
            ok(f"{label:<35} score={score:.3f}  zone={zone}")
            passes += 1
        else:
            fail(f"{label:<35} score={score:.3f}  zone={zone}  expected={'tech' if expected_allowed else 'off_topic/review'}")

    # Harm rules — harmful posts should score > 0
    print(f"\n  {BOLD}Harm detection:{RESET}")
    for label, text, _ in HARMFUL_POSTS:
        result = engine.check_rules(text)
        score  = result.get("rule_score", 0)
        viols  = result.get("violations", [])
        total += 1
        if score > 0 or viols:
            ok(f"{label:<35} rule_score={score:.2f}  violations={viols[:3]}")
            passes += 1
        else:
            fail(f"{label:<35} rule_score={score:.2f}  no violations detected")

    # False-positive check — tech posts should score 0 on harm rules
    print(f"\n  {BOLD}False-positive check (tech posts should have rule_score=0):{RESET}")
    for label, text, _ in TECH_POSTS:
        result = engine.check_rules(text)
        score  = result.get("rule_score", 0)
        viols  = result.get("violations", [])
        total += 1
        if score == 0.0 and not viols:
            ok(f"{label:<35} rule_score=0.00  clean ✓")
            passes += 1
        else:
            fail(f"{label:<35} rule_score={score:.2f}  violations={viols}  ← FALSE POSITIVE")

    sep()
    print(f"  Rule engine: {passes}/{total} passed")
    return passes, total


# ──────────────────────────────────────────────────────────────
#  Test 2 — ML models (toxic-bert + dehatebert)
# ──────────────────────────────────────────────────────────────

def test_ml_models():
    hdr("TEST 2 — ML models (toxic-bert + dehatebert)")
    sep()

    from app.ml.multitask_model import get_multitask_moderator
    print("  Loading models (may take a few seconds on first run)...")
    model = get_multitask_moderator()
    model_type = type(model).__name__
    print(f"  Active model: {BOLD}{model_type}{RESET}")

    if model_type == "FallbackModerator":
        warn("Running on FallbackModerator — ML models not loaded. Results will be keyword-only.")
    else:
        print(f"  {GREEN}EnsembleModerator active — real ML models running{RESET}")

    passes = 0
    total  = 0

    # Harmful posts — model should flag them
    print(f"\n  {BOLD}Harmful posts (should be flagged):{RESET}")
    for label, text, _ in HARMFUL_POSTS:
        result = model.analyze(text)
        flagged = result.get("flagged_categories", [])
        scores  = result.get("scores", {})
        harmful = result.get("is_harmful", False)
        total += 1
        if harmful or flagged:
            ok(f"{label:<35} flagged={flagged}  max_harm={result.get('max_harm_score',0):.2f}")
            passes += 1
        else:
            fail(f"{label:<35} NOT flagged  scores={scores}")

    # Tech posts — model should NOT flag them as harmful
    print(f"\n  {BOLD}Tech posts (should NOT be flagged as harmful):{RESET}")
    for label, text, _ in TECH_POSTS:
        result = model.analyze(text)
        flagged = result.get("flagged_categories", [])
        zone    = result.get("tech_zone", "?")
        score   = result.get("tech_relevance_score", 0)
        harmful = result.get("is_harmful", False)
        total += 1
        if not harmful and not flagged:
            ok(f"{label:<35} clean  tech_zone={zone}  tech_score={score:.3f}")
            passes += 1
        else:
            fail(f"{label:<35} WRONGLY FLAGGED  flagged={flagged}  ← FALSE POSITIVE")

    # Off-topic posts — should be off_topic zone
    print(f"\n  {BOLD}Off-topic posts (should be zone=off_topic or review):{RESET}")
    for label, text, _ in OFF_TOPIC_POSTS:
        result = model.analyze(text)
        zone   = result.get("tech_zone", "?")
        score  = result.get("tech_relevance_score", 0)
        total += 1
        if zone in ("off_topic", "review"):
            ok(f"{label:<35} zone={zone}  tech_score={score:.3f}")
            passes += 1
        else:
            fail(f"{label:<35} zone={zone}  tech_score={score:.3f}  ← should be off_topic")

    sep()
    print(f"  ML models: {passes}/{total} passed")
    return passes, total


# ──────────────────────────────────────────────────────────────
#  Test 3 — Full moderation pipeline (end-to-end)
# ──────────────────────────────────────────────────────────────

def test_full_pipeline():
    hdr("TEST 3 — Decision engine (end-to-end simulation)")
    sep()

    from app.services.rule_engine import RuleEngine
    from app.services.decision_engine import DecisionEngine
    from app.ml.multitask_model import get_multitask_moderator

    engine   = RuleEngine()
    decision = DecisionEngine()
    model    = get_multitask_moderator()

    passes = 0
    total  = 0

    all_cases = TECH_POSTS + OFF_TOPIC_POSTS + HARMFUL_POSTS + EDGE_CASES

    print(f"\n  {'Label':<35} {'Expected':<10} {'Got':<10} {'Reason'}")
    print(f"  {'─'*35} {'─'*10} {'─'*10} {'─'*20}")

    for label, text, expected_allowed in all_cases:
        # Rule engine
        rule_result = engine.check_rules(text)
        tech_result = engine.check_tech_relevance(text) if text else {"tech_relevance_score": 0.0, "zone": "off_topic"}

        # ML
        ml_result = model.analyze(text) if text else {
            "scores": {}, "flagged_categories": [], "is_harmful": False,
            "tech_relevance_score": 0.0, "tech_zone": "off_topic"
        }

        # Build decision input
        text_scores = ml_result.get("scores", {})
        decision_input = {
            "rule_score":           rule_result.get("rule_score", 0.0),
            "has_suspicious_urls":  len(rule_result.get("suspicious_urls", [])) > 0,
            "is_harmful":           ml_result.get("is_harmful", False),
            "nsfw_score":           0.0,
            "tech_relevance_score": tech_result["tech_relevance_score"],
            "tech_zone":            tech_result["zone"],
            "text_score":           tech_result["tech_relevance_score"],
            "toxicity_score":       text_scores.get("toxicity", 0.0),
            "sexual_score":         text_scores.get("sexual", 0.0),
            "self_harm_score":      text_scores.get("self_harm", 0.0),
            "violence_score":       text_scores.get("violence", 0.0),
            "drugs_score":          text_scores.get("drugs", 0.0),
            "threats_score":        text_scores.get("threats", 0.0),
        }

        result  = decision.make_decision(decision_input)
        allowed = result["allowed"]
        reason  = result.get("primary_category", "?")

        total += 1
        expected_str = "ALLOW" if expected_allowed else "BLOCK"
        got_str      = "ALLOW" if allowed else "BLOCK"

        if allowed == expected_allowed:
            passes += 1
            status = f"{GREEN}✅{RESET}"
        else:
            status = f"{RED}❌{RESET}"

        print(f"  {status} {label:<35} {expected_str:<10} {got_str:<10} {reason}")

    sep()
    print(f"  Pipeline: {passes}/{total} passed")
    return passes, total


# ──────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}{'='*60}")
    print("  MODERATION SYSTEM — MODEL CORRECTNESS TESTS")
    print(f"{'='*60}{RESET}")

    total_pass = 0
    total_all  = 0

    try:
        p, t = test_rule_engine()
        total_pass += p; total_all += t
    except Exception as e:
        print(f"{RED}Rule engine test crashed: {e}{RESET}")
        import traceback; traceback.print_exc()

    try:
        p, t = test_ml_models()
        total_pass += p; total_all += t
    except Exception as e:
        print(f"{RED}ML model test crashed: {e}{RESET}")
        import traceback; traceback.print_exc()

    try:
        p, t = test_full_pipeline()
        total_pass += p; total_all += t
    except Exception as e:
        print(f"{RED}Pipeline test crashed: {e}{RESET}")
        import traceback; traceback.print_exc()

    print(f"\n{BOLD}{'='*60}")
    pct = (total_pass / total_all * 100) if total_all else 0
    colour = GREEN if pct >= 85 else (YELLOW if pct >= 60 else RED)
    print(f"  OVERALL: {colour}{total_pass}/{total_all} passed ({pct:.0f}%){RESET}")
    print(f"{'='*60}{RESET}\n")

    if pct < 85:
        print(f"  {YELLOW}Any ❌ rows above tell you exactly what to fix.{RESET}\n")