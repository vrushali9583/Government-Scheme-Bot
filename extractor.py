"""
extractor.py - Natural Language Entity & Profile Extraction Module
Extracts user profile attributes from conversational messages using regex,
keyword mapping, spaCy (if available), and optional Gemini API integration.
Also implements security guards against sensitive PII (Aadhaar, PAN, Bank accounts).
"""

import re
import os
from typing import Dict, Any, Tuple, Optional, List

# List of Indian States and Union Territories for entity matching
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry", "Chandigarh",
    "Andaman and Nicobar Islands", "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep"
]

OCCUPATIONS = {
    "student": ["student", "studying", "mca", "btech", "b.tech", "mba", "bsc", "b.sc", "bcom", "b.com", "ba", "college", "school", "scholar", "undergraduate", "postgraduate"],
    "farmer": ["farmer", "farming", "agriculture", "kisan", "cultivator", "dairy farmer"],
    "artisan": ["artisan", "craftsman", "craftsperson", "carpenter", "blacksmith", "weaver", "potter", "sculptor"],
    "street vendor": ["street vendor", "vendor", "hawker", "thela", "cart puller"],
    "self-employed": ["self employed", "self-employed", "freelancer", "own business", "shopkeeper"],
    "entrepreneur": ["entrepreneur", "startup", "founder", "business owner", "micro-enterprise"],
    "unemployed": ["unemployed", "jobless", "looking for job", "fresher", "job seeker"],
    "unorganized worker": ["daily wage", "laborer", "labourer", "construction worker", "helper", "maid", "domestic worker"],
    "senior citizen": ["retired", "pensioner", "senior citizen", "elderly"]
}

CATEGORIES = {
    "SC": ["sc", "scheduled caste", "dalit"],
    "ST": ["st", "scheduled tribe", "adivasi", "tribal"],
    "OBC": ["obc", "other backward class", "other backward classes", "non creamy layer", "ncl"],
    "EWS": ["ews", "economically weaker section"],
    "General": ["general", "gen", "open category", "unreserved", "ur"]
}

GENDERS = {
    "Female": ["female", "woman", "girl", "lady", "she", "her"],
    "Male": ["male", "man", "boy", "guy", "he", "him"],
    "Transgender": ["transgender", "trans", "third gender"]
}

EDUCATION_LEVELS = [
    "10th Pass", "12th Pass", "Diploma", "ITI", "Graduation",
    "Post Graduation", "MCA", "B.Tech", "M.Tech", "Ph.D.", "Doctorate"
]


def detect_sensitive_data(text: str) -> List[str]:
    """
    Checks for sensitive PII such as Aadhaar, PAN, Credit Cards, or Bank Accounts.
    Returns list of detected sensitive data warnings.
    """
    warnings = []
    # Aadhaar: 12 digit number (with or without spaces/dashes)
    if re.search(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", text):
        warnings.append("Possible Aadhaar Number detected. For privacy and security, do NOT share your Aadhaar number.")

    # PAN: 5 letters, 4 digits, 1 letter
    if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", text, re.IGNORECASE):
        warnings.append("Possible PAN Number detected. Please do NOT share your PAN card details.")

    # Bank Account or Card Number (9-18 consecutive digits)
    if re.search(r"\b\d{9,18}\b", text):
        warnings.append("Possible Bank Account or Card Number detected. Do NOT enter financial credentials.")

    return warnings


def parse_income(text: str) -> Optional[int]:
    """
    Parses natural language income expressions:
    e.g. '2 lakh', '2.5 lakhs', '200000', '50k', '3.5L', 'Rs 2,00,000'
    Returns annual income as an integer in INR.
    """
    clean = text.lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "")

    # Matches: '2.5 lakh', '2 lakhs', '2 lac', '2l'
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lac|l\b)", clean)
    if lakh_match:
        try:
            val = float(lakh_match.group(1))
            return int(val * 100000)
        except ValueError:
            pass

    # Matches: '50k', '80 k'
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", clean)
    if k_match:
        try:
            val = float(k_match.group(1))
            return int(val * 1000)
        except ValueError:
            pass

    # Matches explicit numeric income after words like 'income', 'earn', 'salary', 'package'
    income_num = re.search(r"(?:income|earning|earn|salary|family income)(?:\s*(?:is|of|around|approx|:))?\s*(\d{4,8})", clean)
    if income_num:
        try:
            return int(income_num.group(1))
        except ValueError:
            pass

    # Matches standalone large numbers (e.g. 250000)
    standalone_num = re.search(r"\b(\d{5,8})\b", clean)
    if standalone_num:
        try:
            return int(standalone_num.group(1))
        except ValueError:
            pass

    return None


def parse_age(text: str) -> Optional[int]:
    """
    Extracts age from text like '22 years old', 'age 25', '22 yr old', 'i am 20'.
    """
    patterns = [
        r"(?:i am|age is|aged|age)\s*(\d{1,2})",
        r"(\d{1,2})\s*(?:years old|year old|yrs old|yr old|years of age|yrs|yo)",
        r"\b(\d{2})\s*(?:male|female|student|boy|girl)\b"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            age = int(match.group(1))
            if 1 <= age <= 100:
                return age
    return None


def parse_category(text: str) -> Optional[str]:
    """Matches social category from text."""
    lower = text.lower()
    for cat_name, aliases in CATEGORIES.items():
        for alias in aliases:
            # Word boundary matching
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return cat_name
    return None


def parse_gender(text: str) -> Optional[str]:
    """Matches gender from text."""
    lower = text.lower()
    for gender, aliases in GENDERS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return gender
    return None


def parse_state(text: str) -> Optional[str]:
    """Matches Indian state from text."""
    lower = text.lower()
    for state in INDIAN_STATES:
        if state.lower() in lower:
            return state
    return None


def parse_occupation(text: str) -> Optional[str]:
    """Matches user occupation from text."""
    lower = text.lower()
    for occ, keywords in OCCUPATIONS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                return occ.title()
    return None


def parse_education(text: str) -> Optional[str]:
    """Matches education level or course from text."""
    lower = text.lower()
    for edu in EDUCATION_LEVELS:
        if re.search(rf"\b{re.escape(edu.lower())}\b", lower):
            return edu
    if "college" in lower or "degree" in lower or "bachelor" in lower:
        return "Graduation"
    if "master" in lower or "pg" in lower or "mca" in lower:
        return "Post Graduation"
    return None


def parse_disability(text: str) -> Optional[str]:
    """Checks for mentions of disability or physically challenged status."""
    lower = text.lower()
    if any(kw in lower for kw in ["disabled", "disability", "handicap", "divyang", "specially abled", "pwd", "physically challenged"]):
        if any(neg in lower for kw in ["no disability", "not disabled", "non-disabled"] for neg in [kw]):
            return "No"
        return "Yes"
    if "no disability" in lower or "not disabled" in lower:
        return "No"
    return None


def parse_name(text: str) -> Optional[str]:
    """Extracts user name if introduced (e.g. 'My name is Rohan', 'I am Rahul')."""
    match = re.search(r"(?:my name is|i am|myself)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if match:
        name = match.group(1).strip()
        # Avoid common words mistakenly treated as names
        if name.lower() not in ["a", "an", "the", "student", "farmer", "looking", "interested"]:
            return name
    return None


def extract_profile_from_text(
    text: str,
    existing_profile: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Core extraction function. Analyzes natural language user input,
    identifies profile attributes, and merges them with existing profile state.
    Returns:
        (updated_profile_dict, security_warnings_list)
    """
    security_warnings = detect_sensitive_data(text)

    # Initialize or copy existing profile
    profile: Dict[str, Any] = {
        "name": None,
        "age": None,
        "gender": None,
        "state": None,
        "education": None,
        "occupation": None,
        "income": None,
        "category": None,
        "disability": "No"
    }

    if existing_profile:
        profile.update(existing_profile)

    # 1. Regex & Pattern-based extraction
    extracted_name = parse_name(text)
    if extracted_name and not profile.get("name"):
        profile["name"] = extracted_name

    extracted_age = parse_age(text)
    if extracted_age is not None:
        profile["age"] = extracted_age

    extracted_income = parse_income(text)
    if extracted_income is not None:
        profile["income"] = extracted_income

    extracted_category = parse_category(text)
    if extracted_category:
        profile["category"] = extracted_category

    extracted_occupation = parse_occupation(text)
    if extracted_occupation:
        profile["occupation"] = extracted_occupation

    extracted_state = parse_state(text)
    if extracted_state:
        profile["state"] = extracted_state

    extracted_gender = parse_gender(text)
    if extracted_gender:
        profile["gender"] = extracted_gender

    extracted_education = parse_education(text)
    if extracted_education:
        profile["education"] = extracted_education

    extracted_disability = parse_disability(text)
    if extracted_disability:
        profile["disability"] = extracted_disability

    # 2. Try spaCy entity extraction if installed
    try:
        import spacy
        # Load small english model if available
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "GPE" and not profile.get("state"):
                for state in INDIAN_STATES:
                    if ent.text.lower() == state.lower():
                        profile["state"] = state
                        break
            elif ent.label_ == "PERSON" and not profile.get("name"):
                if ent.text.strip().lower() not in ["student", "farmer", "mca", "obc", "sc", "st"]:
                    profile["name"] = ent.text.strip()
    except Exception:
        # spaCy model not installed or error; pattern matching handles extraction
        pass

    return profile, security_warnings


def get_missing_fields(profile: Dict[str, Any]) -> List[str]:
    """
    Determines which required profile fields are still needed
    to evaluate eligibility accurately.
    """
    required_keys = ["age", "state", "occupation", "income", "category"]
    missing = []
    for key in required_keys:
        val = profile.get(key)
        if val is None or val == "" or (isinstance(val, (int, float)) and val < 0):
            missing.append(key)
    return missing
