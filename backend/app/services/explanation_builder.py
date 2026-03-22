from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ExplanationBuilder:
    """Builds human-readable explanations for moderation decisions.

    Translates raw decision engine output and intermediate results
    into structured, user-facing explanation text.

    Covers:
      - Rule-based violations (keywords, URLs, spam, Hindi abuse)
      - ML harm categories (toxicity, sexual, self-harm, etc.)
      - Tech relevance outcomes (allowed, review, off-topic)  ← NEW
      - Image signals (NSFW, CLIP mismatch, tech image)       ← NEW
      - Severity and confidence metadata
    """

    def __init__(self):

        # ── Primary reason templates ──
        # Keys match decision["primary_category"] and decision["reasons"] values.
        self.templates: Dict[str, str] = {
            # ── Harm violations ──
            "rules":            "Content triggered safety rules",
            "suspicious_url":   "A suspicious or shortened URL was detected",
            "spam":             "Content appears to be spam or promotional material",
            "toxicity":         "Toxic or hateful language detected",
            "sexual":           "Sexual or explicit content detected",
            "self_harm":        "Content related to self-harm or suicide detected",
            "violence":         "Violent content detected",
            "drugs":            "Drug-related content detected",
            "threats":          "Threatening or intimidating content detected",
            "nsfw_image":       "Image contains explicit or NSFW content",
            "harmful_content":  "Content flagged as potentially harmful",
            "cyber_harm_intent": "Harmful cyber-security content detected (e.g. exploit guide, malware tutorial)",
            "content_mixing":   "Off-topic content mixed into technical post",

            # ── Tech relevance outcomes ──
            "off_topic":        "Content does not appear to be tech-related",
            "needs_review":     "Content could not be confirmed as tech-related and needs review",
            "tech_content":     "Technology content approved",

            # ── Safe / approved ──
            "safe":             "No issues detected — content approved",
            "safe_content":     "Content approved",
        }

        # ── Detail templates for off-topic explanations ──
        self.off_topic_detail_templates: Dict[str, str] = {
            "food":         "appears to be about food or cooking",
            "sports":       "appears to be about sports",
            "entertainment": "appears to be about entertainment or celebrities",
            "politics":     "appears to be about politics",
            "religion":     "appears to be about religion or religious events",
            "fashion":      "appears to be about fashion or lifestyle",
            "relationships": "appears to be about personal relationships",
        }

        # ── Category severity levels ──
        self.severity_levels: Dict[str, str] = {
            "self_harm":    "critical",
            "violence":     "high",
            "sexual":       "high",
            "nsfw_image":   "high",
            "threats":      "high",
            "toxicity":     "medium",
            "drugs":        "medium",
            "rules":        "medium",
            "suspicious_url": "medium",
            "spam":         "low",
            "off_topic":    "low",
            "needs_review": "low",
            "safe":         "none",
            "tech_content": "none",
            "cyber_harm_intent": "high",
            "content_mixing":    "medium",
            "cyber_harm":   "high",
        }

        # ── User-facing severity labels ──
        self.severity_labels: Dict[str, str] = {
            "critical": "🔴 Critical",
            "high":     "🔴 High",
            "medium":   "🟡 Medium",
            "low":      "🟢 Low",
            "none":     "✅ None",
        }

    # ──────────────────────────────────────────────────────────
    #  Main entry point
    # ──────────────────────────────────────────────────────────

    def build_explanation(
        self,
        decision: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a complete explanation from decision + pipeline results.

        Args:
            decision : Output from DecisionEngine.make_decision()
            results  : Full pipeline results dict from ModerationService

        Returns:
            Dict with:
              reasons          : list of human-readable reason strings
              flagged_phrases  : list of matched harmful keywords / URLs
              severity         : severity string (critical / high / medium / low / none)
              severity_label   : emoji-prefixed severity label
              score            : decision confidence score (0–1)
              primary_category : top category string
              allowed          : bool
              summary          : one-sentence summary
              tech_context     : dict with tech relevance context  ← NEW
              image_context    : dict with image analysis context  ← NEW
        """
        reasons: List[str] = []
        flagged_phrases: List[str] = []

        decision_reasons = decision.get("reasons", [])
        primary_category = decision.get("primary_category", "safe")
        allowed = decision.get("allowed", True)

        # ── 1. Translate decision reasons into human-readable strings ──
        for reason in decision_reasons:
            template = self.templates.get(reason)
            if template:
                reasons.append(template)
            else:
                # Unknown reason — pass through as-is
                reasons.append(reason)

        # ── 2. Enrich rule-based violations ──
        rule_results = results.get("rule_based") or {}
        if rule_results:
            # Banned keywords
            banned = rule_results.get("banned_keywords", [])
            if banned:
                flagged_phrases.extend(banned)

            # Hindi abuse
            hindi = rule_results.get("hindi_detection", {})
            if hindi.get("has_hindi_abuse"):
                matched = hindi.get("matched_words", [])
                flagged_phrases.extend(matched)
                if "Hindi/Hinglish abusive language detected" not in reasons:
                    reasons.append("Hindi/Hinglish abusive language detected")

            # Suspicious URLs
            sus_urls = rule_results.get("suspicious_urls", [])
            if sus_urls:
                flagged_phrases.extend(sus_urls)

            # Spam
            if rule_results.get("spam_detected"):
                if "Content appears to be spam or promotional material" not in reasons:
                    reasons.append("Content appears to be spam or promotional material")

        # ── 3. Enrich URL analysis ──
        url_analysis = results.get("url_analysis") or {}
        url_sus = url_analysis.get("suspicious_urls", [])
        for u in url_sus:
            url_str = u.get("full_url", "") if isinstance(u, dict) else str(u)
            if url_str and url_str not in flagged_phrases:
                flagged_phrases.append(url_str)

        # ── 4. Tech relevance context ──
        tech_context = self._build_tech_context(decision, results)

        # ── 5. Image context ──
        image_context = self._build_image_context(results)

        # ── 6. Determine effective severity ──
        severity = self.severity_levels.get(primary_category, "low")

        # Escalate if multiple harm categories triggered
        text_analysis = results.get("text_analysis") or {}
        flagged_cats = text_analysis.get("flagged_categories", [])
        critical_cats = {"self_harm", "sexual", "violence"}
        if len(flagged_cats) >= 2 and any(c in critical_cats for c in flagged_cats):
            severity = "critical"

        severity_label = self.severity_labels.get(severity, "🟡 Medium")

        # ── 7. Build one-sentence summary ──
        summary = self._build_summary(allowed, primary_category, tech_context, flagged_phrases)

        # Deduplicate
        reasons = list(dict.fromkeys(filter(None, reasons)))
        flagged_phrases = list(dict.fromkeys(filter(None, flagged_phrases)))

        return {
            "reasons": reasons,
            "flagged_phrases": flagged_phrases,
            "severity": severity,
            "severity_label": severity_label,
            "score": decision.get("score", 0.0),
            "primary_category": primary_category,
            "allowed": allowed,
            "summary": summary,
            "tech_context": tech_context,
            "image_context": image_context,
        }

    # ──────────────────────────────────────────────────────────
    #  Tech context builder
    # ──────────────────────────────────────────────────────────

    def _build_tech_context(
        self,
        decision: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build tech relevance context block for the explanation.

        Pulls data from:
          - results["tech_relevance"]    (from rule engine in moderation_service)
          - results["text_analysis"]     (tech_zone, tech_matched_categories from multitask model)
          - decision["primary_category"] (for outcome mapping)
        """
        tech_relevance = results.get("tech_relevance") or {}
        text_analysis = results.get("text_analysis") or {}

        # Prefer rule engine score (authoritative); fall back to ML model score
        score = tech_relevance.get("tech_relevance_score") or \
                text_analysis.get("tech_relevance_score") or \
                text_analysis.get("scores", {}).get("tech_relevance", 0.0)

        zone = tech_relevance.get("zone") or \
               text_analysis.get("tech_zone") or \
               decision.get("primary_category")

        matched_categories = tech_relevance.get("matched_categories") or \
                             text_analysis.get("tech_matched_categories") or []

        matched_terms = tech_relevance.get("matched_terms", [])
        non_tech_signals = tech_relevance.get("non_tech_signals", [])

        # Human-readable zone description
        zone_descriptions: Dict[str, str] = {
            "tech":      "Confirmed tech-related content",
            "review":    "Borderline — tech relevance unclear",
            "off_topic": "Not tech-related",
        }
        zone_description = zone_descriptions.get(zone or "", "Unknown")

        # Off-topic detail (what non-tech signals triggered)
        off_topic_detail: Optional[str] = None
        if zone == "off_topic" and non_tech_signals:
            off_topic_detail = f"Post {self._describe_non_tech_signals(non_tech_signals)}"

        return {
            "score": round(float(score), 3),
            "zone": zone,
            "zone_description": zone_description,
            "matched_categories": matched_categories,
            "matched_terms": matched_terms[:10],  # cap for readability
            "non_tech_signals": non_tech_signals,
            "off_topic_detail": off_topic_detail,
        }

    def _describe_non_tech_signals(self, signals: List[str]) -> str:
        """Convert matched non-tech signal words into a readable description."""
        if not signals:
            return "appears to be off-topic"

        # Map keywords to topic labels
        topic_map = {
            "recipe": "food/cooking", "cooking": "food/cooking", "restaurant": "food/cooking",
            "cricket": "sports", "football": "sports", "soccer": "sports", "ipl": "sports",
            "celebrity": "entertainment", "bollywood": "entertainment", "actor": "entertainment",
            "election": "politics", "politician": "politics", "parliament": "politics",
            "temple": "religion", "mosque": "religion", "church": "religion", "prayer": "religion",
            "outfit": "fashion/lifestyle", "makeup": "fashion/lifestyle", "salon": "fashion/lifestyle",
            "girlfriend": "personal relationships", "boyfriend": "personal relationships",
            "wedding": "personal relationships",
        }

        topics = set()
        for signal in signals:
            for keyword, topic in topic_map.items():
                if keyword in signal.lower():
                    topics.add(topic)
                    break
            else:
                topics.add(signal)

        topic_list = list(topics)[:3]
        if len(topic_list) == 1:
            return f"appears to be about {topic_list[0]}"
        return f"appears to be about {', '.join(topic_list[:-1])} and {topic_list[-1]}"

    # ──────────────────────────────────────────────────────────
    #  Image context builder
    # ──────────────────────────────────────────────────────────

    def _build_image_context(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Build image analysis context block for the explanation."""
        image_analysis = results.get("image_analysis") or {}
        relevance_analysis = results.get("relevance_analysis") or {}

        if not image_analysis and not relevance_analysis:
            return {"has_image": False}

        context: Dict[str, Any] = {"has_image": True}

        # NSFW
        if image_analysis:
            nsfw_prob = image_analysis.get("nsfw_probability", 0.0)
            context["nsfw_probability"] = round(float(nsfw_prob), 3)
            context["is_nsfw"] = image_analysis.get("is_nsfw", False)
            context["image_category"] = image_analysis.get("primary_category", "unknown")

        # CLIP similarity + mismatch
        if relevance_analysis:
            sim = relevance_analysis.get("similarity_score", 0.0)
            context["text_image_similarity"] = round(float(sim), 3)
            context["is_relevant"] = relevance_analysis.get("is_relevant", True)
            context["mismatch_detected"] = relevance_analysis.get("mismatch_detected", False)

            # Tech image signal
            context["tech_image_score"] = round(
                float(relevance_analysis.get("tech_image_score", 0.0)), 3
            )
            context["is_tech_image"] = relevance_analysis.get("is_tech_image", False)
            context["off_topic_image_score"] = round(
                float(relevance_analysis.get("off_topic_image_score", 0.0)), 3
            )

            # Top relevant concepts (human-readable)
            top_concepts = relevance_analysis.get("relevant_concepts", [])
            context["top_image_concepts"] = [
                c["concept"] for c in top_concepts[:3]
            ]

            # Harmful concepts detected in image
            harmful = relevance_analysis.get("harmful_concepts", [])
            context["harmful_image_concepts"] = [
                c["concept"] for c in harmful if c.get("score", 0) > 0.20
            ]

        return context

    # ──────────────────────────────────────────────────────────
    #  Summary builder
    # ──────────────────────────────────────────────────────────

    def _build_summary(
        self,
        allowed: bool,
        primary_category: str,
        tech_context: Dict[str, Any],
        flagged_phrases: List[str],
    ) -> str:
        """Build a single-sentence human-readable summary."""
        if allowed:
            zone = tech_context.get("zone", "tech")
            cats = tech_context.get("matched_categories", [])
            if cats:
                cat_str = ", ".join(cats[:3])
                return f"✅ Tech content approved — matched categories: {cat_str}."
            return "✅ Content approved — no issues detected."

        # Blocked
        if primary_category == "off_topic":
            detail = tech_context.get("off_topic_detail")
            if detail:
                return f"❌ Blocked — {detail}."
            return "❌ Blocked — content does not appear to be tech-related."

        if primary_category == "needs_review":
            return "⚠️ Held for review — tech relevance could not be confirmed."

        template = self.templates.get(primary_category, "")
        if template:
            return f"❌ Blocked — {template.lower()}."

        if flagged_phrases:
            sample = flagged_phrases[0]
            return f"❌ Blocked — flagged content detected (e.g. '{sample}')."

        return "❌ Blocked — content violated platform policies."

    # ──────────────────────────────────────────────────────────
    #  Utility
    # ──────────────────────────────────────────────────────────

    def get_summary(self, reasons: List[str], allowed: bool = True) -> str:
        """Get a brief summary string from a list of reasons."""
        if not reasons:
            return "Content approved" if allowed else "Content rejected"

        if len(reasons) == 1:
            return f"{'Approved' if allowed else 'Rejected'}: {reasons[0]}"

        return (
            f"{'Approved' if allowed else 'Rejected'}: "
            f"{len(reasons)} policy violation(s) detected"
        )

    def format_for_api(self, explanation: Dict[str, Any]) -> Dict[str, Any]:
        """Return a slimmed-down version safe to include in public API responses.

        Strips internal debug fields; keeps only what the client needs.
        """
        return {
            "allowed": explanation.get("allowed"),
            "summary": explanation.get("summary"),
            "reasons": explanation.get("reasons", []),
            "severity": explanation.get("severity"),
            "severity_label": explanation.get("severity_label"),
            "flagged_phrases": explanation.get("flagged_phrases", []),
            "tech_zone": explanation.get("tech_context", {}).get("zone"),
            "tech_score": explanation.get("tech_context", {}).get("score"),
        }