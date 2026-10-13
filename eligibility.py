"""
eligibility.py - Deterministic Rule-Based Eligibility Engine
CRITICAL DESIGN PRINCIPLE:
AI NEVER decides or overrides scheme eligibility.
This engine executes strictly deterministic boolean logic to evaluate
a user profile against government scheme criteria.
"""

from typing import Dict, Any, List, Tuple


def evaluate_eligibility(
    profile: Dict[str, Any],
    scheme: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates a user profile against a single scheme using deterministic rules.
    Returns:
        {
            "status": "Eligible" | "Partially Eligible" | "Not Eligible",
            "passed_checks": [str, ...],
            "failed_checks": [str, ...],
            "reasons": [str, ...],
            "unmet_criteria": [str, ...]
        }
    """
    passed_checks = []
    failed_checks = []
    unmet_criteria = []

    # 1. AGE CHECK
    min_age = int(scheme.get("min_age", 0) or 0)
    max_age = int(scheme.get("max_age", 100) or 100)
    user_age = profile.get("age")

    if user_age is not None:
        if min_age <= user_age <= max_age:
            passed_checks.append(f"Age {user_age} is within the required range ({min_age} - {max_age} years).")
        else:
            if user_age < min_age:
                failed = f"Age requirement not met: Minimum required age is {min_age} years (your age is {user_age})."
            else:
                failed = f"Age requirement not met: Maximum allowed age is {max_age} years (your age is {user_age})."
            failed_checks.append(failed)
            unmet_criteria.append(failed)

    # 2. INCOME CHECK
    max_income = int(scheme.get("max_income", 0) or 0)
    user_income = profile.get("income")

    if max_income > 0:
        if user_income is not None:
            if user_income <= max_income:
                passed_checks.append(f"Annual family income (Rs {user_income:,}) is within the threshold (Max Rs {max_income:,}).")
            else:
                failed = f"Income threshold exceeded: Maximum allowed family income is Rs {max_income:,} (your family income is Rs {user_income:,})."
                failed_checks.append(failed)
                unmet_criteria.append(failed)
    else:
        passed_checks.append("No maximum income ceiling specified for this scheme.")

    # 3. CATEGORY CHECK
    eligible_cats_str = str(scheme.get("eligible_categories", "ALL") or "ALL").strip()
    user_cat = profile.get("category")

    if eligible_cats_str.upper() == "ALL":
        passed_checks.append("Open to all social categories (General, OBC, SC, ST, EWS).")
    else:
        eligible_cats = [c.strip().upper() for c in eligible_cats_str.split(",")]
        if user_cat:
            if user_cat.upper() in eligible_cats:
                passed_checks.append(f"Category '{user_cat}' matches eligible categories ({eligible_cats_str}).")
            else:
                failed = f"Category mismatch: Scheme is reserved for ({eligible_cats_str}), but your category is {user_cat}."
                failed_checks.append(failed)
                unmet_criteria.append(failed)

    # 4. OCCUPATION CHECK
    eligible_occs_str = str(scheme.get("eligible_occupations", "ALL") or "ALL").strip()
    user_occ = profile.get("occupation")

    if eligible_occs_str.upper() == "ALL":
        passed_checks.append("Open to all occupations.")
    else:
        eligible_occs = [o.strip().lower() for o in eligible_occs_str.split(",")]
        if user_occ:
            user_occ_clean = user_occ.strip().lower()
            # Match substring or exact keyword
            matched = any(
                user_occ_clean in occ or occ in user_occ_clean
                for occ in eligible_occs
            )
            if matched:
                passed_checks.append(f"Occupation '{user_occ}' qualifies for this scheme ({eligible_occs_str}).")
            else:
                failed = f"Occupation mismatch: Scheme is intended for ({eligible_occs_str}), but your occupation is {user_occ}."
                failed_checks.append(failed)
                unmet_criteria.append(failed)

    # 5. STATE CHECK
    eligible_states_str = str(scheme.get("eligible_states", "ALL") or "ALL").strip()
    user_state = profile.get("state")

    if eligible_states_str.upper() == "ALL":
        passed_checks.append("National scheme applicable across all States and Union Territories.")
    else:
        eligible_states = [s.strip().lower() for s in eligible_states_str.split(",")]
        if user_state:
            if user_state.strip().lower() in eligible_states:
                passed_checks.append(f"Applicable in your state: {user_state}.")
            else:
                failed = f"State restriction: Scheme is only valid in ({eligible_states_str})."
                failed_checks.append(failed)
                unmet_criteria.append(failed)

    # 6. GENDER CHECK
    eligible_genders_str = str(scheme.get("eligible_genders", "ALL") or "ALL").strip()
    user_gender = profile.get("gender")

    if eligible_genders_str.upper() == "ALL":
        passed_checks.append("Applicable regardless of gender.")
    else:
        eligible_genders = [g.strip().lower() for g in eligible_genders_str.split(",")]
        if user_gender:
            if user_gender.strip().lower() in eligible_genders:
                passed_checks.append(f"Gender eligibility criteria met ({user_gender}).")
            else:
                failed = f"Gender requirement: Scheme is specifically for ({eligible_genders_str})."
                failed_checks.append(failed)
                unmet_criteria.append(failed)

    # 7. DISABILITY CHECK
    disability_req = str(scheme.get("disability_required", "NO") or "NO").strip().upper()
    user_disability = profile.get("disability", "No")

    if disability_req == "YES":
        if str(user_disability).strip().lower() in ["yes", "true", "y"]:
            passed_checks.append("Meets specially-abled / PwD criteria.")
        else:
            failed = "Disability status: This scheme is reserved exclusively for specially-abled individuals (PwD >= 40%)."
            failed_checks.append(failed)
            unmet_criteria.append(failed)

    # DETERMINE FINAL STATUS
    num_failed = len(failed_checks)

    if num_failed == 0:
        status = "Eligible"
    elif num_failed == 1:
        status = "Partially Eligible"
    else:
        status = "Not Eligible"

    return {
        "status": status,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "unmet_criteria": unmet_criteria,
        "scheme": scheme
    }


def generate_explanation(eval_result: Dict[str, Any]) -> str:
    """
    Generates a clear, beginner-friendly explanation of why a user
    is Eligible, Partially Eligible, or Not Eligible for a scheme.
    """
    status = eval_result["status"]
    scheme = eval_result["scheme"]
    scheme_name = scheme.get("scheme_name", "Scheme")
    passed = eval_result["passed_checks"]
    failed = eval_result["failed_checks"]

    if status == "Eligible":
        explanation = f"### You appear to qualify for **{scheme_name}**!\n\n"
        explanation += "**Why you qualify:**\n"
        for item in passed:
            explanation += f"- {item}\n"
        explanation += "\n> **Next Step:** Review the required documents below and apply through the official government portal."

    elif status == "Partially Eligible":
        explanation = f"### You are **Partially Eligible** for **{scheme_name}**.\n\n"
        explanation += "You meet most eligibility conditions, but have **one unmet requirement**:\n"
        for item in failed:
            explanation += f"- ⚠️ **{item}**\n"
        explanation += "\n**Requirements you meet:**\n"
        for item in passed:
            explanation += f"- {item}\n"

    else:
        explanation = f"### You are currently **Not Eligible** for **{scheme_name}**.\n\n"
        explanation += "**Unmet requirements:**\n"
        for item in failed:
            explanation += f"- ❌ {item}\n"

    return explanation
