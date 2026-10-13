"""
chatbot.py - Conversational Workflow & Response Generation
Coordinates conversational state, missing field inquiries, scheme searches,
and deterministic eligibility presentation.
Uses an intelligent local dialog manager with optional Gemini API enhancement.
"""

import os
from typing import Dict, Any, List, Tuple, Optional
from extractor import extract_profile_from_text, get_missing_fields, detect_sensitive_data
from recommender import recommend_schemes, get_recommendation_summary
from database import search_schemes

LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Disclaimer:** *Final eligibility and benefits are strictly subject to verification "
    "by the respective government ministry upon submitting valid documents on the official portal. "
    "This system provides recommendations based on current scheme guidelines and does not issue approvals.*"
)


class SchemeChatbot:
    """Manages conversational state and generates grounded scheme advice."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception:
                self.gemini_model = None

    def process_message(
        self,
        user_message: str,
        current_profile: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Processes an incoming user message.
        Returns:
            (bot_reply_markdown, updated_profile, recommendation_results_or_None)
        """
        # Step 1: Detect sensitive data (Aadhaar, PAN, Card numbers)
        security_warnings = detect_sensitive_data(user_message)
        security_notice = ""
        if security_warnings:
            security_notice = (
                "> 🛡️ **Privacy & Security Alert:**\n"
                + "\n".join([f"> - {w}" for w in security_warnings])
                + "\n> *Your sensitive credentials were NOT stored.*\n\n"
            )

        # Step 2: Check for specific scheme lookups (e.g., 'What is PM MUDRA?', 'Tell me about scholarship')
        lower_msg = user_message.lower()
        if any(trigger in lower_msg for trigger in ["what is", "tell me about", "details of", "info on", "how to apply for"]):
            search_results = search_schemes(query=user_message)
            if search_results:
                reply = security_notice + self._format_scheme_search_reply(search_results[:3])
                return reply, current_profile or {}, None

        # Step 3: Extract or update profile attributes
        updated_profile, _ = extract_profile_from_text(user_message, existing_profile=current_profile)
        missing_fields = get_missing_fields(updated_profile)

        # Step 4: Check if we have enough information to run recommendation engine
        # Mandatory: at least age, category, and occupation or income known
        critical_fields_count = sum(
            1 for f in ["age", "occupation", "category", "income"]
            if updated_profile.get(f) is not None
        )

        # Case A: Missing critical attributes -> Ask targeted follow-up questions
        if critical_fields_count < 3 and missing_fields:
            followup_reply = security_notice + self._generate_followup_question(updated_profile, missing_fields)
            return followup_reply, updated_profile, None

        # Case B: We have substantial profile data -> Run Rule-Based Eligibility Engine
        recommendations = recommend_schemes(updated_profile)
        summary = get_recommendation_summary(recommendations)

        reply = security_notice + self._format_recommendation_reply(updated_profile, recommendations, summary)
        return reply, updated_profile, recommendations

    def _generate_followup_question(
        self,
        profile: Dict[str, Any],
        missing: List[str]
    ) -> str:
        """Constructs a friendly follow-up question requesting missing attributes."""
        known_parts = []
        if profile.get("age"):
            known_parts.append(f"age: **{profile['age']}**")
        if profile.get("occupation"):
            known_parts.append(f"occupation: **{profile['occupation']}**")
        if profile.get("state"):
            known_parts.append(f"state: **{profile['state']}**")
        if profile.get("category"):
            known_parts.append(f"category: **{profile['category']}**")
        if profile.get("income") is not None:
            known_parts.append(f"family income: **Rs {profile['income']:,}**")

        greeting = "Namaste! "
        if profile.get("name"):
            greeting = f"Hello **{profile['name']}**! "

        msg = greeting
        if known_parts:
            msg += f"I have noted your profile details ({', '.join(known_parts)}).\n\n"
        else:
            msg += "I'm here to help you discover Government Schemes tailored specifically to you.\n\n"

        msg += "To accurately check your eligibility across our official scheme database, could you please provide:\n\n"

        field_prompts = {
            "age": "🎂 **Your Age** (e.g., 22 years)",
            "state": "📍 **Your State** (e.g., Maharashtra, Uttar Pradesh, etc.)",
            "occupation": "💼 **Your Occupation** (e.g., Student, Farmer, Self-Employed, Unemployed)",
            "income": "💰 **Annual Family Income** (e.g., 2 lakh, 1.5L, 200000)",
            "category": "🏷️ **Social Category** (General / OBC / SC / ST / EWS)"
        }

        for idx, field in enumerate(missing, 1):
            prompt = field_prompts.get(field, f"**{field.title()}**")
            msg += f"{idx}. {prompt}\n"

        msg += "\n*You can type your answer in natural language, for example:*\n"
        msg += "> *\"I am a 22 year old student from Maharashtra, OBC category with 2 lakh family income.\"*"
        return msg

    def _format_recommendation_reply(
        self,
        profile: Dict[str, Any],
        recommendations: Dict[str, Any],
        summary: Dict[str, int]
    ) -> str:
        """Formats comprehensive, transparent recommendations with official links and document lists."""
        user_name = profile.get("name", "User")
        eligible = recommendations.get("eligible", [])
        partial = recommendations.get("partially_eligible", [])

        res = f"### 🎯 Government Scheme Recommendations for You\n\n"
        res += (
            f"Based on your profile (**Age: {profile.get('age', 'N/A')}**, "
            f"**Occupation: {profile.get('occupation', 'N/A')}**, "
            f"**Category: {profile.get('category', 'N/A')}**, "
            f"**Income: Rs {profile.get('income', 0):,}**, "
            f"**State: {profile.get('state', 'All India')}**), here are the results:\n\n"
        )

        res += f"- ✅ **{summary['eligible_count']} Eligible Schemes**\n"
        res += f"- ⚠️ **{summary['partial_count']} Partially Eligible Schemes**\n\n"

        # Highlight Eligible Schemes
        if eligible:
            res += "#### 🌟 Schemes You Qualify For:\n\n"
            for s in eligible[:4]:  # Show top 4 directly in chat
                res += f"##### 1. [{s['scheme_name']}]({s['official_url']})\n"
                res += f"- **Ministry:** {s['ministry']}\n"
                res += f"- **Description:** {s['description']}\n"
                res += f"- **Required Documents:** `{s['required_documents']}`\n"
                res += f"- 🔗 **Official Portal:** [Apply / Verify on {s['data_source']}]({s['official_url']})\n\n"

            if len(eligible) > 4:
                res += f"*(+ {len(eligible) - 4} more eligible schemes available in the **Dashboard** tab)*\n\n"
        else:
            res += "Currently, no direct 100% matches were found for this exact profile combination.\n\n"

        # Highlight Partially Eligible Schemes
        if partial:
            res += "#### ⚠️ Schemes You Partially Qualify For:\n"
            res += "*You meet almost all requirements except for one specific criterion:*\n\n"
            for s in partial[:3]:
                res += f"##### • [{s['scheme_name']}]({s['official_url']})\n"
                for unmet in s["unmet_criteria"]:
                    res += f"  - 📌 **Reason:** {unmet}\n"
                res += f"  - 🔗 [Official Portal Link]({s['official_url']})\n\n"

        res += "\n👉 *Tip: Open the **Dashboard & Schemes** tabs for in-depth filters, document checklists, and full comparisons!*"
        res += LEGAL_DISCLAIMER
        return res

    def _format_scheme_search_reply(self, schemes: List[Dict[str, Any]]) -> str:
        """Formats direct scheme information query results."""
        res = "### 📋 Government Scheme Details\n\n"
        for s in schemes:
            res += f"#### [{s['scheme_name']}]({s['official_url']})\n"
            res += f"- **Ministry:** {s['ministry']}\n"
            res += f"- **Overview:** {s['description']}\n"
            res += f"- **Eligibility Age:** {s['min_age']} - {s['max_age']} years\n"
            income_txt = f"Up to Rs {s['max_income']:,}" if s['max_income'] > 0 else "No Income Ceiling"
            res += f"- **Income Limit:** {income_txt}\n"
            res += f"- **Target Group:** {s['eligible_categories']} | {s['eligible_occupations']}\n"
            res += f"- **Documents:** `{s['required_documents']}`\n"
            res += f"- 🔗 **Official Website:** [{s['official_url']}]({s['official_url']})\n\n"

        res += LEGAL_DISCLAIMER
        return res
