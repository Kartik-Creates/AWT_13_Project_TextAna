#!/usr/bin/env python3
"""
Test Hindi/Hinglish abuse detection.

Run from backend directory:
    python -X utf8 tests/test_hindi_detection.py
Or test a single phrase:
    python -X utf8 tests/test_hindi_detection.py "madarchod"
"""

import os, sys

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")
    return condition


print("=" * 64)
print("  HINDI / HINGLISH ABUSE DETECTION TEST")
print("=" * 64)

# ── 1. Pure normalizer + dictionary tests (no ML needed) ──
print("\n[1] TEXT NORMALIZER (rule-based)")

from app.ml.text_normalizer import text_normalizer

# Group A: plain Hindi abuse  → must detect
abuse_plain = [
    ("madarchod", "Plain Hindi abuse"),
    ("chutiya", "Plain Hindi abuse"),
    ("bhosdike", "Plain Hindi abuse"),
    ("bkl", "Abbreviation"),
    ("mc bc", "Common abbreviations"),
    ("tu chutiya hai", "Hinglish sentence"),
    ("randi", "Abuse word"),
    ("gaandu", "Abuse word"),
    ("lund", "Abuse word"),
    ("teri maa ki", "Abusive phrase"),
    ("gand mara", "Abusive phrase"),
]

print("\n  -- Plain Hindi abuse (MUST detect):")
for text, desc in abuse_plain:
    r = text_normalizer.detect_hindi_abuse(text)
    check(f'"{text}" ({desc}) -> matched={r["matched_words"]}', r["has_hindi_abuse"])

# Group B: obfuscated Hindi abuse → must detect
abuse_obfus = [
    ("m@darchod", "@ for a"),
    ("bhosd1ke", "1 for i"),
    ("ma*darchod", "* removed"),
    ("chut!ya", "! for i"),
    ("maaaadarchod", "Repeated chars"),
    ("ch00tiya", "00 for oo/u"),
    ("m a d a r c h o d", "Spaced out"),
    ("b h o s d i k e", "Spaced out"),
]

print("\n  -- Obfuscated abuse (MUST detect):")
for text, desc in abuse_obfus:
    r = text_normalizer.detect_hindi_abuse(text)
    check(f'"{text}" ({desc}) -> matched={r["matched_words"]}', r["has_hindi_abuse"])

# Group C: safe content → must NOT detect
safe = [
    ("I love you", "English safe"),
    ("how are you", "English safe"),
    ("good morning", "English safe"),
    ("thank you very much", "English safe"),
    ("main aaj bahut khush hoon", "Hindi safe"),
    ("chai peelo", "Hindi safe"),
    ("kya haal hai", "Hindi safe"),
    ("I have great skill in coding", "Should not false-positive"),
]

print("\n  -- Safe content (must NOT flag):")
for text, desc in safe:
    r = text_normalizer.detect_hindi_abuse(text)
    check(f'"{text}" ({desc}) -> matched={r["matched_words"]}', not r["has_hindi_abuse"])

# ── 2. Full pipeline test (ML + Hindi) ──
print("\n\n[2] FULL PIPELINE (ML model + Hindi detection)")
try:
    from app.ml.distilbert_model import distilbert_analyzer

    full_cases = [
        # (text, should_be_toxic, description)
        ("madarchod", True, "Hindi abuse"),
        ("m@darchod", True, "Obfuscated Hindi"),
        ("tu chutiya hai", True, "Hinglish phrase"),
        ("bkl stop it", True, "Abbreviation in sentence"),
        ("I hate you and want to kill everyone", True, "English toxic"),
        ("you are chutiya", True, "Mixed English+Hindi"),
        ("Beautiful sunrise this morning", False, "Safe English"),
        ("I love coding in Python", False, "Safe English"),
        ("main aaj bahut khush hoon", False, "Safe Hindi"),
    ]

    for text, expected_toxic, desc in full_cases:
        result = distilbert_analyzer.analyze(text)
        score = result["toxicity_score"]
        is_toxic = result["is_toxic"]
        cat = result["category"]
        hindi = result.get("hindi_detection", {})
        hindi_flag = hindi.get("has_hindi_abuse", False)

        label = (
            f'"{text[:40]}" ({desc}): '
            f'toxic={is_toxic} score={score:.3f} cat={cat} hindi={hindi_flag}'
        )
        check(label, is_toxic == expected_toxic)

    print("\n  Full pipeline tests complete")
except Exception as e:
    print(f"  [FAIL] ML pipeline error: {e}")
    import traceback; traceback.print_exc()

# ── 3. Rule engine integration ──
print("\n\n[3] RULE ENGINE INTEGRATION")
from app.services.rule_engine import RuleEngine
re_eng = RuleEngine()

for text, desc in [("madarchod", "Hindi"), ("m@darchod", "Obfuscated"), ("bkl", "Abbr")]:
    result = re_eng.check_rules(text)
    has_v = len(result["violations"]) > 0
    check(f'Rule engine: "{text}" -> violations={result["violations"]}', has_v)

for text, desc in [("I love you", "Safe"), ("kya haal hai", "Safe Hindi")]:
    result = re_eng.check_rules(text)
    has_v = len(result["violations"]) > 0
    check(f'Rule engine: "{text}" -> violations={result["violations"]}', not has_v)

# ── Summary ──
print("\n" + "=" * 64)
print(f"  RESULTS:  [PASS] {PASS}   [FAIL] {FAIL}")
print("=" * 64)

if FAIL > 0:
    print(f"\n  {FAIL} test(s) failed -- see output above")
    sys.exit(1)
else:
    print("\n  All tests passed! Hindi abuse detection working correctly.")
    sys.exit(0)
