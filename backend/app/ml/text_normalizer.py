"""
Text normalization for obfuscated Hindi/English text.

Handles:
  - Leetspeak and symbol substitutions (m@darchod → madarchod)
  - Repeated characters (maaaadarchod → madarchod)
  - Spaced-out evasion (m a d a r c h o d → madarchod)
  - Hindi/Hinglish abusive word dictionary with confidence scoring
"""

import re
from typing import Dict, Any, List, Set

__all__ = ["TextNormalizer", "text_normalizer"]


class TextNormalizer:
    """Normalize obfuscated text and detect Hindi/Hinglish abuse."""

    def __init__(self):
        # ── Character substitution map (leetspeak / symbols) ──
        self.char_map: Dict[str, str] = {
            # Numbers → letters
            "0": "o", "1": "i", "2": "z", "3": "e", "4": "a",
            "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
            # Symbols → letters
            "@": "a", "$": "s", "!": "i", "|": "i",
            "€": "e", "£": "l", "©": "c", "®": "r",
            # Symbols → remove (used as separators / obfuscation)
            "*": "", "#": "", "+": "", "=": "", "_": "",
            "-": "", ".": "", "<": "", ">": "", "[": "", "]": "",
            "{": "", "}": "", "(": "", ")": "", "/": "", "\\": "",
            "~": "", "`": "", "^": "", "'": "", '"': "",
        }

        # ── Hindi / Hinglish abusive words ──
        # Organized by severity for confidence scoring.
        self.high_severity: Set[str] = {
            # Full forms + common spelling variants (including from 0→o normalization)
            "madarchod", "maderchod", "maderchot", "madarchot",
            "bhenchod", "behenchod", "bhenchodd", "behenchodd",
            "chutiya", "chutya", "chutiye", "chutiyo", "chutia",
            "chootiya", "chootya", "chootiye",  # from 0→o normalization
            "bhosdike", "bhosda", "bhosdi", "bhosadi", "bhosdiwale",
            "bhoosdike", "bhoosda",  # from 0→o normalization
            "randi", "randwe", "randwa", "randikhana",
            # Body parts used as abuse
            "gaand", "gaandu", "gandu", "gaandmara",
            "loda", "lodu", "lund", "lauda", "lawda",
            "lavde", "lavda", "lawde",
            # Phrases (stored without spaces — matched after space-removal)
            "maachod", "behenchod", "gaandmara", "lundchoos",
            "terimaaki", "teribehanki",
        }

        self.medium_severity: Set[str] = {
            # Common abbreviations
            "mc", "bc", "bkl", "bsdk", "mkc", "bkc",
            # Mild abuse
            "kamina", "kamine", "kamini",
            "harami", "haramkhor", "haramzada", "haramzadi",
            "kutte", "kutta", "kutiya",
            "saala", "saale", "saali",
            "ullu", "gadha", "bewakoof",
            "tatti", "gobar", "jhant",
        }

        # Union for quick lookup
        self.all_abusive = self.high_severity | self.medium_severity

        # Multi-word phrases (checked separately with spaces)
        self.abusive_phrases: List[str] = [
            "teri maa ki", "teri behan ki", "maa chod", "behan chod",
            "gand mara", "lund le", "maa ki chut", "bhag bsdk",
            "chup bc", "nikal mc", "gand phad", "muh me le",
        ]

        # ── Compiled regexes ──
        self._repeated_chars = re.compile(r"(.)\1{2,}")
        self._extra_spaces = re.compile(r"\s+")
        self._single_char_spaces = re.compile(
            r"\b(\w)\s(\w)\s(\w)\s(\w)(\s\w)*\b"
        )

    # ──────────────────────────────────────────────────────────
    #  Normalization
    # ──────────────────────────────────────────────────────────

    def normalize(self, text: str) -> str:
        """Normalize obfuscated text to its base form.

        Pipeline:
          1. lowercase
          2. replace leetspeak / symbol chars
          3. collapse repeated characters (aaaa → a)
          4. collapse spaced-out letters (m a d a r → madar)
          5. clean whitespace
        """
        if not text or not isinstance(text, str):
            return ""

        t = text.lower()

        # Symbol substitution
        for old, new in self.char_map.items():
            if old in t:
                t = t.replace(old, new)

        # Collapse repeated chars (maaaa → ma)
        t = self._repeated_chars.sub(r"\1", t)

        # Collapse spaced-out single letters:  "m a d a r" → "madar"
        t = self._collapse_spaced_letters(t)

        # Clean whitespace
        t = self._extra_spaces.sub(" ", t).strip()

        return t

    def _collapse_spaced_letters(self, text: str) -> str:
        """Collapse sequences of single spaced letters into words.

        "m a d a r c h o d" → "madarchod"
        "hello w o r l d"   → "hello world"
        """
        result = []
        i = 0
        chars = list(text)
        n = len(chars)

        while i < n:
            # Check if we're at the start of a spaced-letter sequence:
            #   letter, space, letter, space, letter ...  (≥3 letters)
            if (
                i + 4 < n
                and chars[i].isalpha()
                and chars[i + 1] == " "
                and chars[i + 2].isalpha()
                and chars[i + 3] == " "
                and chars[i + 4].isalpha()
            ):
                # Collect all single-spaced letters
                collapsed = [chars[i]]
                j = i + 2
                while j < n and chars[j].isalpha():
                    collapsed.append(chars[j])
                    if j + 1 < n and chars[j + 1] == " " and j + 2 < n and chars[j + 2].isalpha():
                        # Check that the next char after space is also a single letter
                        # (could be followed by another space or end)
                        if j + 3 >= n or not chars[j + 2 + 1:j + 2 + 2] or chars[j + 3] == " ":
                            j += 2
                        else:
                            # Next segment is a multi-char word — stop here
                            break
                    else:
                        break

                result.append("".join(collapsed))
                i = j + 1
            else:
                result.append(chars[i])
                i += 1

        return "".join(result)

    def preprocess_for_model(self, text: str) -> str:
        """Full preprocessing pipeline for ML model input.

        Returns text with obfuscation removed but sentence structure intact.
        """
        t = self.normalize(text)
        # Remove remaining non-alphanumeric (keep spaces)
        t = re.sub(r"[^\w\s]", " ", t)
        t = self._extra_spaces.sub(" ", t).strip()
        return t

    # ──────────────────────────────────────────────────────────
    #  Hindi Abuse Detection (rule-based)
    # ──────────────────────────────────────────────────────────

    def detect_hindi_abuse(self, text: str) -> Dict[str, Any]:
        """Detect Hindi/Hinglish abusive content with confidence scoring.

        Checks both normalized single-word matches and multi-word phrases.
        """
        original = text
        normalized = self.normalize(text)
        normalized_no_spaces = normalized.replace(" ", "")

        matched_words: List[str] = []
        matched_categories: List[str] = []

        # ── 1. Check multi-word phrases first (on normalized text) ──
        for phrase in self.abusive_phrases:
            if phrase in normalized:
                matched_words.append(phrase)
                matched_categories.append("hindi_abuse_phrase")

        # ── 2. Check single-word exact matches (on each word) ──
        words = normalized.split()
        for word in words:
            if word in self.all_abusive:
                if word not in matched_words:
                    matched_words.append(word)
                    if word in self.high_severity:
                        matched_categories.append("hindi_high_severity")
                    else:
                        matched_categories.append("hindi_medium_severity")

        # ── 3. Check concatenated form (for spaced-out evasion) ──
        # "m a d a r c h o d" normalizes to "madarchod" but just in case
        # the collapsing missed it, also check the no-space version
        if not matched_words:
            for abuse in self.all_abusive:
                if len(abuse) >= 3 and abuse in normalized_no_spaces:
                    matched_words.append(abuse)
                    if abuse in self.high_severity:
                        matched_categories.append("hindi_high_severity")
                    else:
                        matched_categories.append("hindi_medium_severity")

        # ── 4. Check abbreviation matches (mc, bc, bkl etc.) ──
        # These are short so only match as standalone words
        for word in words:
            if word in self.medium_severity and len(word) <= 4 and word not in matched_words:
                matched_words.append(word)
                matched_categories.append("hindi_abbreviation")

        # ── Confidence scoring ──
        if any(c == "hindi_high_severity" or c == "hindi_abuse_phrase" for c in matched_categories):
            confidence = 0.95
        elif any(c == "hindi_medium_severity" for c in matched_categories):
            confidence = 0.80
        elif any(c == "hindi_abbreviation" for c in matched_categories):
            confidence = 0.70
        elif matched_words:
            confidence = 0.65
        else:
            confidence = 0.0

        return {
            "has_hindi_abuse": bool(matched_words),
            "matched_words": list(dict.fromkeys(matched_words)),  # dedupe, preserve order
            "categories": list(dict.fromkeys(matched_categories)),
            "confidence": confidence,
            "normalized_text": normalized,
            "original_text": original,
        }


# Global instance
text_normalizer = TextNormalizer()
