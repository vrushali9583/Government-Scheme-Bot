"""
app.py - Main Streamlit Application for GovSchemeBot
AI-Powered Government Scheme Eligibility and Recommendation Chatbot
Suitable for MCA AI & Data Science Portfolio & Hackathon Demonstration.
"""

import streamlit as st
import os
import sys

# Ensure local imports work reliably
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_all_schemes, search_schemes, get_database_stats
from extractor import INDIAN_STATES, CATEGORIES, EDUCATION_LEVELS, get_missing_fields
from recommender import recommend_schemes, get_recommendation_summary
from chatbot import SchemeChatbot

# Page configuration
st.set_page_config(
    page_title="GovSchemeBot | Government Scheme Eligibility Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Responsive, Modern Government Portal aesthetic)
st.markdown("""
<style>
    /* Theme Accents */
    :root {
        --primary-blue: #1B365D;
        --secondary-orange: #FF9933;
        --accent-green: #138808;
    }
    .main-header {
        background: linear-gradient(135deg, #0d233a 0%, #1B365D 50%, #20406b 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: #ffffff !important;
        margin: 0;
        font-size: 2.1rem;
        font-weight: 700;
    }
    .main-header p {
        color: #d1dbe5 !important;
        margin-top: 6px;
        font-size: 1.05rem;
    }
    .badge-bar {
        display: flex;
        gap: 10px;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .custom-badge {
        background-color: rgba(255, 255, 255, 0.15);
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .scheme-card {
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        background-color: #ffffff;
        border-left: 6px solid #1B365D;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .scheme-card-eligible {
        border-left-color: #138808 !important;
    }
    .scheme-card-partial {
        border-left-color: #f59e0b !important;
    }
    .metric-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .disclaimer-card {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        padding: 14px 18px;
        border-radius: 8px;
        color: #92400e;
        font-size: 0.9rem;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Database once on startup
@st.cache_resource
def setup_database():
    return init_db()

setup_database()


# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Namaste & Welcome to GovSchemeBot!**\n\n"
                "I am your AI-powered assistant for discovering Central and State Government Schemes you may qualify for.\n\n"
                "💬 **How to use:** Simply introduce yourself in natural language! For example:\n"
                "> *\"I am a 22 year old MCA student from Maharashtra. My family income is 2 lakh. I belong to OBC category.\"*\n\n"
                "🔒 **Privacy Guarantee:** We will *never* ask for or store sensitive credentials like Aadhaar, PAN, or Bank passwords."
            )
        }
    ]

if "profile" not in st.session_state:
    st.session_state.profile = {
        "name": None,
        "age": None,
        "gender": "Male",
        "state": "Maharashtra",
        "education": "Post Graduation",
        "occupation": "Student",
        "income": 200000,
        "category": "OBC",
        "disability": "No"
    }

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "bot" not in st.session_state:
    st.session_state.bot = SchemeChatbot()


# ==========================================
# SIDEBAR: USER PROFILE & SECURITY CONTROLS
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=65)
    st.title("User Profile")
    st.caption("Active attributes evaluated by the Rule Engine")

    prof = st.session_state.profile
    missing = get_missing_fields(prof)

    # Status Badge
    if not missing and prof.get("age"):
        st.success("✅ Profile Complete & Verified")
    else:
        st.warning(f"⚠️ Incomplete: Missing {len(missing)} fields")

    # Profile Details Display
    st.markdown(f"""
    - **Age:** {prof.get('age') or '*(Not set)*'}
    - **Gender:** {prof.get('gender') or '*(Not set)*'}
    - **State:** {prof.get('state') or '*(Not set)*'}
    - **Occupation:** {prof.get('occupation') or '*(Not set)*'}
    - **Education:** {prof.get('education') or '*(Not set)*'}
    - **Family Income:** {'Rs ' + f"{prof['income']:,}" if prof.get('income') is not None else '*(Not set)*'}
    - **Category:** {prof.get('category') or '*(Not set)*'}
    - **Disability (PwD):** {prof.get('disability') or 'No'}
    """)

    st.divider()

    # Quick Actions
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🔄 Evaluate", use_container_width=True, help="Run rule engine on current profile"):
            st.session_state.recommendations = recommend_schemes(st.session_state.profile)
            st.toast("Evaluation complete! Check Dashboard tab.", icon="✅")
    with col_s2:
        if st.button("🗑️ Reset", use_container_width=True, help="Clear conversation and profile"):
            st.session_state.messages = [st.session_state.messages[0]]
            st.session_state.profile = {
                "name": None, "age": None, "gender": "Male", "state": "Maharashtra",
                "education": "Post Graduation", "occupation": "Student",
                "income": 200000, "category": "OBC", "disability": "No"
            }
            st.session_state.recommendations = None
            st.rerun()

    st.divider()

    # Privacy & Safety Box
    st.markdown("### 🛡️ Privacy & Safety")
    st.info(
        "**Strict Zero-PII Policy:**\n"
        "• No Aadhaar Card\n"
        "• No PAN Card\n"
        "• No Bank Credentials\n\n"
        "All calculations run deterministically via python rules."
    )

    # Optional Gemini API Key configuration
    with st.expander("⚙️ Optional Gemini API Settings"):
        user_key = st.text_input("Gemini API Key (Optional)", type="password", help="Enables Gemini conversational formatting.")
        if user_key:
            os.environ["GEMINI_API_KEY"] = user_key
            st.session_state.bot = SchemeChatbot()
            st.success("API Key configured for session!")


# ==========================================
# MAIN INTERFACE HEADER
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>🏛️ GovSchemeBot</h1>
    <p>AI-Powered Government Scheme Eligibility & Explainable Recommendation Engine</p>
    <div class="badge-bar">
        <span class="custom-badge">🔒 Privacy First (Zero PII)</span>
        <span class="custom-badge">⚖️ Deterministic Rule Engine (0% Hallucination)</span>
        <span class="custom-badge">📚 Verified Gov Portals</span>
        <span class="custom-badge">💡 Explainable AI (XAI)</span>
    </div>
</div>
""", unsafe_allow_html=True)


# TABS NAVIGATION
tab_chat, tab_form, tab_dash, tab_search = st.tabs([
    "💬 Chatbot Assistant",
    "👤 Direct Profile Form",
    "📊 Recommendations Dashboard",
    "🔍 Search & Browse Schemes"
])


# ==========================================
# TAB 1: CONVERSATIONAL CHATBOT
# ==========================================
with tab_chat:
    st.markdown("#### Conversational Scheme Discovery")
    st.caption("Chat naturally with GovSchemeBot. The chatbot extracts key profile attributes and deterministic rules evaluate your eligibility.")

    # Quick Starter Prompts
    st.markdown("**Quick Prompts:**")
    prompt_cols = st.columns(3)
    with prompt_cols[0]:
        if st.button("🎓 22yo MCA Student (OBC, 2L income)", use_container_width=True):
            user_text = "I am a 22 year old MCA student from Maharashtra. My family income is 2 lakh. I belong to OBC category."
            st.session_state.messages.append({"role": "user", "content": user_text})
            reply, updated_prof, recs = st.session_state.bot.process_message(user_text, st.session_state.profile)
            st.session_state.profile = updated_prof
            if recs:
                st.session_state.recommendations = recs
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    with prompt_cols[1]:
        if st.button("🌾 Small Farmer in UP (Family income 1.5L)", use_container_width=True):
            user_text = "I am a 35 year old farmer living in Uttar Pradesh. My annual income is 1.5 lakh, General category."
            st.session_state.messages.append({"role": "user", "content": user_text})
            reply, updated_prof, recs = st.session_state.bot.process_message(user_text, st.session_state.profile)
            st.session_state.profile = updated_prof
            if recs:
                st.session_state.recommendations = recs
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    with prompt_cols[2]:
        if st.button("💼 Woman Entrepreneur (Loan / Seed Fund)", use_container_width=True):
            user_text = "I am a 28 year old female entrepreneur from Karnataka looking for business loans, SC category."
            st.session_state.messages.append({"role": "user", "content": user_text})
            reply, updated_prof, recs = st.session_state.bot.process_message(user_text, st.session_state.profile)
            st.session_state.profile = updated_prof
            if recs:
                st.session_state.recommendations = recs
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    st.divider()

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if chat_input := st.chat_input("Tell me about yourself (e.g. age, occupation, state, category, income)..."):
        # Append User Message
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)

        # Process with Bot
        with st.spinner("Analyzing profile & evaluating eligibility rules..."):
            reply, updated_profile, recommendations = st.session_state.bot.process_message(
                chat_input,
                current_profile=st.session_state.profile
            )
            st.session_state.profile = updated_profile
            if recommendations:
                st.session_state.recommendations = recommendations

        # Append Assistant Response
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
            st.rerun()


# ==========================================
# TAB 2: DIRECT PROFILE FORM
# ==========================================
with tab_form:
    st.markdown("#### Manual Profile Verification & Eligibility Calculator")
    st.caption("Use this form to directly customize your profile and test deterministic eligibility logic.")

    with st.form("manual_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name_val = st.text_input("Name (Optional)", value=st.session_state.profile.get("name") or "")
            age_val = st.number_input("Age (Years)", min_value=1, max_value=100, value=int(st.session_state.profile.get("age") or 22))
            gender_val = st.selectbox("Gender", ["Male", "Female", "Transgender", "Other"], index=0)
            state_val = st.selectbox("State / Union Territory", INDIAN_STATES, index=INDIAN_STATES.index(st.session_state.profile.get("state", "Maharashtra")) if st.session_state.profile.get("state") in INDIAN_STATES else 0)
            disability_val = st.radio("Specially-Abled / Person with Disability (PwD)?", ["No", "Yes"], horizontal=True)

        with col2:
            occ_list = ["Student", "Farmer", "Self-Employed", "Entrepreneur", "Artisan", "Street Vendor", "Unemployed", "Unorganized Worker", "Senior Citizen"]
            occ_idx = occ_list.index(st.session_state.profile.get("occupation", "Student")) if st.session_state.profile.get("occupation") in occ_list else 0
            occ_val = st.selectbox("Occupation", occ_list, index=occ_idx)
            
            edu_idx = EDUCATION_LEVELS.index(st.session_state.profile.get("education", "Post Graduation")) if st.session_state.profile.get("education") in EDUCATION_LEVELS else 5
            edu_val = st.selectbox("Education Level", EDUCATION_LEVELS, index=edu_idx)

            income_val = st.number_input("Annual Family Income (INR)", min_value=0, max_value=10000000, step=10000, value=int(st.session_state.profile.get("income") or 200000))
            cat_list = ["General", "OBC", "SC", "ST", "EWS"]
            cat_idx = cat_list.index(st.session_state.profile.get("category", "OBC")) if st.session_state.profile.get("category") in cat_list else 1
            cat_val = st.selectbox("Social Category", cat_list, index=cat_idx)

        submitted = st.form_submit_button("🔍 Check Scheme Eligibility", use_container_width=True)
        if submitted:
            st.session_state.profile = {
                "name": name_val.strip() if name_val else None,
                "age": age_val,
                "gender": gender_val,
                "state": state_val,
                "education": edu_val,
                "occupation": occ_val,
                "income": income_val,
                "category": cat_val,
                "disability": disability_val
            }
            st.session_state.recommendations = recommend_schemes(st.session_state.profile)
            st.success("Profile updated! Switched to Recommendations Dashboard.")


# ==========================================
# TAB 3: RECOMMENDATIONS DASHBOARD
# ==========================================
with tab_dash:
    st.markdown("#### Comprehensive Scheme Recommendations")

    # If no recommendations evaluated yet, auto-evaluate with current profile
    if not st.session_state.recommendations:
        st.session_state.recommendations = recommend_schemes(st.session_state.profile)

    recs = st.session_state.recommendations
    summary = get_recommendation_summary(recs)

    # Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Evaluated Schemes", summary["total"])
    with m2:
        st.metric("Eligible Schemes", summary["eligible_count"], delta="100% Match")
    with m3:
        st.metric("Partially Eligible", summary["partial_count"], delta="Near Match", delta_color="normal")
    with m4:
        st.metric("Not Eligible", summary["not_eligible_count"], delta="Criteria Mismatch", delta_color="inverse")

    st.divider()

    # Category Breakdown Tabs
    sub_tab_el, sub_tab_part, sub_tab_not = st.tabs([
        f"✅ Eligible Schemes ({summary['eligible_count']})",
        f"⚠️ Partially Eligible Schemes ({summary['partial_count']})",
        f"❌ Not Eligible Schemes ({summary['not_eligible_count']})"
    ])

    # 1. Eligible Schemes
    with sub_tab_el:
        if recs["eligible"]:
            for item in recs["eligible"]:
                with st.expander(f"🟢 **{item['scheme_name']}** — {item['ministry']}", expanded=True):
                    col_l, col_r = st.columns([3, 1])
                    with col_l:
                        st.markdown(f"**Description:** {item['description']}")
                        st.markdown(f"**Required Documents:** `{item['required_documents']}`")
                        st.markdown("**Why You Qualify:**")
                        for p in item["passed_checks"]:
                            st.markdown(f"- ✅ {p}")
                    with col_r:
                        st.caption(f"**Source:** {item['data_source']}")
                        st.caption(f"**Updated:** {item['last_updated']}")
                        st.link_button("🌐 Apply on Official Portal", item["official_url"], use_container_width=True)
        else:
            st.info("No schemes met 100% of the criteria with current profile parameters.")

    # 2. Partially Eligible Schemes
    with sub_tab_part:
        if recs["partially_eligible"]:
            st.info("💡 **Partially Eligible Schemes:** You meet almost all requirements, but fail exactly one parameter (such as income limit or specific reservation).")
            for item in recs["partially_eligible"]:
                with st.expander(f"🟡 **{item['scheme_name']}** — {item['ministry']}"):
                    col_l, col_r = st.columns([3, 1])
                    with col_l:
                        st.markdown(f"**Description:** {item['description']}")
                        st.markdown("⚠️ **Missing Requirement:**")
                        for u in item["unmet_criteria"]:
                            st.warning(u)
                        st.markdown("**Requirements Met:**")
                        for p in item["passed_checks"]:
                            st.markdown(f"- ✅ {p}")
                        st.markdown(f"**Required Documents:** `{item['required_documents']}`")
                    with col_r:
                        st.caption(f"**Source:** {item['data_source']}")
                        st.caption(f"**Updated:** {item['last_updated']}")
                        st.link_button("🌐 View Official Portal", item["official_url"], use_container_width=True)
        else:
            st.write("No partially eligible schemes.")

    # 3. Not Eligible Schemes
    with sub_tab_not:
        if recs["not_eligible"]:
            for item in recs["not_eligible"]:
                with st.expander(f"⚪ {item['scheme_name']}"):
                    st.markdown(f"**Description:** {item['description']}")
                    st.markdown("**Unmet Criteria:**")
                    for u in item["unmet_criteria"]:
                        st.markdown(f"- ❌ {u}")
                    st.link_button("View Scheme Link", item["official_url"])


# ==========================================
# TAB 4: SEARCH & BROWSE SCHEMES
# ==========================================
with tab_search:
    st.markdown("#### Search Government Scheme Repository")
    st.caption("Filter and explore all structured schemes stored in the SQLite database.")

    col_q, col_cat, col_occ, col_st = st.columns([2, 1, 1, 1])
    with col_q:
        search_query = st.text_input("Search by Name or Keyword", placeholder="e.g. Scholarship, MUDRA, Farmer, Housing")
    with col_cat:
        search_cat = st.selectbox("Social Category", ["ALL", "General", "OBC", "SC", "ST", "EWS"])
    with col_occ:
        search_occ = st.selectbox("Occupation", ["ALL", "Student", "Farmer", "Self-Employed", "Entrepreneur", "Artisan", "Street Vendor"])
    with col_st:
        search_state = st.selectbox("State Filter", ["ALL"] + INDIAN_STATES)

    results = search_schemes(query=search_query, category=search_cat, occupation=search_occ, state=search_state)
    st.write(f"Showing **{len(results)}** schemes:")

    for s in results:
        with st.container():
            st.markdown(f"""
            <div class="scheme-card">
                <h4><a href="{s['official_url']}" target="_blank" style="text-decoration:none; color:#1B365D;">{s['scheme_name']}</a></h4>
                <p><strong>Ministry / Department:</strong> {s['ministry']}</p>
                <p>{s['description']}</p>
                <p><strong>Eligible Groups:</strong> {s['eligible_categories']} | {s['eligible_occupations']} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Age:</strong> {s['min_age']} - {s['max_age']} yrs &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Max Income:</strong> {'Rs ' + f"{s['max_income']:,}" if s['max_income'] > 0 else 'No Limit'}</p>
                <p><strong>Required Documents:</strong> <code>{s['required_documents']}</code></p>
                <p><small>Source: {s['data_source']} | Updated: {s['last_updated']}</small></p>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# GLOBAL TRUST & COMPLIANCE FOOTER
# ==========================================
st.markdown("""
<div class="disclaimer-card">
    <strong>⚖️ Official Disclaimer & Data Trustworthiness:</strong><br>
    This application is an educational prototype and portfolio project built for MCA AI & Data Science research.
    All scheme data is curated based on public guidelines published on <em>data.gov.in</em>, <em>myscheme.gov.in</em>, and respective Ministry portals.
    <strong>AI does NOT make eligibility decisions.</strong> All evaluations are performed strictly by a deterministic rule engine.
    Final approval, fund disbursement, and eligibility validation are solely determined by authorized Government Authorities upon official application submission.
</div>
""", unsafe_allow_html=True)
