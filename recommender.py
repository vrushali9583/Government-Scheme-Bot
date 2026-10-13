"""
recommender.py - Recommendation Engine for GovSchemeBot
Categorizes schemes into:
1. Eligible Schemes (100% criteria met)
2. Partially Eligible Schemes (Only 1 unmet criterion, with clear reason)
3. Not Eligible Schemes (Multiple unmet criteria)
"""

from typing import Dict, Any, List
from database import get_all_schemes
from eligibility import evaluate_eligibility, generate_explanation


def recommend_schemes(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the user profile against all schemes in the database.
    Sorts schemes into Eligible, Partially Eligible, and Not Eligible.
    """
    schemes = get_all_schemes()

    eligible_list = []
    partially_eligible_list = []
    not_eligible_list = []

    for scheme in schemes:
        eval_result = evaluate_eligibility(profile, scheme)
        explanation = generate_explanation(eval_result)

        card_data = {
            "scheme_id": scheme["scheme_id"],
            "scheme_name": scheme["scheme_name"],
            "ministry": scheme["ministry"],
            "description": scheme["description"],
            "min_age": scheme["min_age"],
            "max_age": scheme["max_age"],
            "max_income": scheme["max_income"],
            "eligible_categories": scheme["eligible_categories"],
            "eligible_occupations": scheme["eligible_occupations"],
            "eligible_states": scheme["eligible_states"],
            "required_documents": scheme["required_documents"],
            "official_url": scheme["official_url"],
            "data_source": scheme["data_source"],
            "last_updated": scheme["last_updated"],
            "status": eval_result["status"],
            "passed_checks": eval_result["passed_checks"],
            "failed_checks": eval_result["failed_checks"],
            "unmet_criteria": eval_result["unmet_criteria"],
            "explanation": explanation
        }

        if eval_result["status"] == "Eligible":
            eligible_list.append(card_data)
        elif eval_result["status"] == "Partially Eligible":
            partially_eligible_list.append(card_data)
        else:
            not_eligible_list.append(card_data)

    return {
        "eligible": eligible_list,
        "partially_eligible": partially_eligible_list,
        "not_eligible": not_eligible_list,
        "total_evaluated": len(schemes)
    }


def get_recommendation_summary(recommendations: Dict[str, Any]) -> Dict[str, int]:
    """Returns quick metrics count for dashboard display."""
    return {
        "eligible_count": len(recommendations.get("eligible", [])),
        "partial_count": len(recommendations.get("partially_eligible", [])),
        "not_eligible_count": len(recommendations.get("not_eligible", [])),
        "total": recommendations.get("total_evaluated", 0)
    }
