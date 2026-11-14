"""SkillForge AI — Phase A
Details form → Main app (Skill Gap tab, Course placeholder, Mentor placeholder)
No sidebar · No demo button · No landing cards · No step bar
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
from dotenv import load_dotenv

# ── Environment ──────────────────────────────────────────────────────────────
load_dotenv()

# ── Agent layer ──────────────────────────────────────────────────────────────
from agents.orchestrator import Orchestrator

# ── File paths ───────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
ROLES_FILE  = DATA_DIR / "roles.json"
QUIZZES_FILE = DATA_DIR / "quizzes.json"
LEARNER_FILE = DATA_DIR / "learner.json"
EXPL_CACHE_FILE = DATA_DIR / "skill_explanations.json"


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: Path, data: Dict[str, Any]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def save_learner_data(data: Dict[str, Any]):
    save_json(LEARNER_FILE, data)


def normalize_skill(s: str) -> str:
    """Light normalization: strip + title-case."""
    return s.strip().title()


@st.cache_resource
def get_orchestrator():
    return Orchestrator()


# ── Static data ───────────────────────────────────────────────────────────────
roles_data   = load_json(ROLES_FILE)
quizzes_data = load_json(QUIZZES_FILE)
orchestrator = get_orchestrator()

ALL_SKILLS = sorted(
    list(
        {
            skill
            for role in roles_data.values()
            for skill in role.get("skills", {}).keys()
        }
    )
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkillForge",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Hide sidebar + toggle ── */
    [data-testid="stSidebar"]                        { display: none !important; }
    section[data-testid="stSidebarCollapsedControl"] { display: none !important; }
    button[data-testid="collapsedControl"]           { display: none !important; }

    /* ── Layout ── */
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 820px;
    }

    /* ── Cards ── */
    .sf-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .sf-card-center { text-align: center; }

    /* ── Chips ── */
    .chip-have {
        background: #ecfdf5; color: #047857;
        border: 1px solid #a7f3d0;
        padding: 5px 14px; border-radius: 9999px;
        font-weight: 600; font-size: 0.88rem;
        display: inline-block; margin: 4px;
    }
    .chip-need {
        background: #fff7ed; color: #c2410c;
        border: 1px solid #fed7aa;
        padding: 5px 14px; border-radius: 9999px;
        font-weight: 600; font-size: 0.88rem;
        display: inline-block; margin: 4px;
    }

    /* ── Header bar ── */
    .sf-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 0 18px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 24px;
    }
    .sf-header-title {
        font-size: 1.35rem; font-weight: 800; color: #0f172a;
    }
    .sf-header-user {
        font-size: 0.9rem; color: #475569;
    }

    /* ── AI-status badge ── */
    .badge-online  { background:#f0fdf4; border:1px solid #bbf7d0; color:#166534; }
    .badge-offline { background:#f8fafc; border:1px solid #e2e8f0; color:#475569; }
    .ai-badge {
        display:inline-block; padding:4px 12px;
        border-radius:9999px; font-size:0.78rem; font-weight:600;
        margin-top:4px;
    }

    /* ── Agent log items ── */
    .agent-item {
        padding: 8px 12px;
        border-left: 3px solid #3b82f6;
        background: #f8fafc;
        margin-bottom: 6px;
        border-radius: 0 8px 8px 0;
        font-size: 0.84rem; color: #334155;
    }

    /* ── Explanation text ── */
    .expl-text {
        font-size: 0.95rem; color: #334155; line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state defaults ─────────────────────────────────────────────────────
if "current_step"       not in st.session_state:
    st.session_state.current_step      = "details"
if "learner"            not in st.session_state:
    st.session_state.learner           = load_json(LEARNER_FILE)
if "analysis_result"    not in st.session_state:
    st.session_state.analysis_result   = {}
if "skill_explanations" not in st.session_state:
    # Load persisted cache first so explanations survive reloads
    st.session_state.skill_explanations = load_json(EXPL_CACHE_FILE)
if "editing_profile"    not in st.session_state:
    st.session_state.editing_profile   = False


# ── Utility functions ──────────────────────────────────────────────────────────
def add_agent_log(message: str):
    if "activity_log" not in st.session_state.learner:
        st.session_state.learner["activity_log"] = []
    st.session_state.learner["activity_log"].insert(0, message)


def humanize_log(log_str: str) -> str:
    if "CareerMatch:" in log_str:
        parts = log_str.split("CareerMatch:")[1].strip()
        return f"<strong>Career Match Agent:</strong> {parts}"
    elif "SkillAnalyst:" in log_str:
        return "<strong>Skill Analyst Agent:</strong> Reviewed your strengths and identified what to focus on."
    elif "CurriculumPlanner:" in log_str:
        inner = log_str.split("CurriculumPlanner:")[1].strip()
        if "structured" in inner:
            return "<strong>Curriculum Planner Agent:</strong> Built your ordered learning steps with curated guides."
        elif "revision" in inner or "< 60%" in inner:
            return "<strong>Curriculum Planner Agent:</strong> Added review materials to help you practice."
        return f"<strong>Curriculum Planner Agent:</strong> {inner}"
    elif "Assessment:" in log_str:
        inner = log_str.split("Assessment:")[1].strip()
        return f"<strong>Assessment Agent:</strong> {inner}"
    elif "Mentor:" in log_str:
        return "<strong>Mentor Agent:</strong> Shared personalised advice and explained your plan."
    elif "Orchestrator:" in log_str:
        return f"<strong>Coordinator:</strong> {log_str.split('Orchestrator:')[1].strip()}"
    return f"<strong>Learning Assistant:</strong> {log_str}"


def reset_progress():
    """Clear all progress so a new goal/profile starts clean."""
    st.session_state.learner["progress"]     = {"completed": [], "status_map": {}}
    st.session_state.learner["quiz_history"] = []


def get_skill_explanation(skill: str, role: str, roles_data: dict) -> str:
    """Return a cached explanation; generate only when missing."""
    cache = st.session_state.skill_explanations
    key   = f"{skill}::{role}"
    if key in cache:
        return cache[key]

    # Gather a fallback resource title + difficulty from roles.json
    skill_info   = roles_data.get(role, {}).get("skills", {}).get(skill, {})
    difficulty   = skill_info.get("difficulty", "foundational")
    resources    = skill_info.get("resources", [])
    first_res    = resources[0]["title"] if resources else "online tutorials"
    fallback_txt = (
        f"{skill} is a {difficulty} skill that is essential for {role}. "
        f"A great place to start is '{first_res}'."
    )

    # Try LLM
    try:
        from agents.base import BaseAgent
        _agent = BaseAgent("SkillExplainer")
        prompt = (
            f"In exactly 2 plain sentences (no jargon, no bullet points): "
            f"what is {skill}, why does a {role} need it, "
            f"and what can someone build with it?"
        )
        explanation = _agent.call_llm(prompt, fallback_txt)
    except Exception:
        explanation = fallback_txt

    cache[key] = explanation
    st.session_state.skill_explanations = cache
    # Persist to file so it survives page refresh
    save_json(EXPL_CACHE_FILE, cache)
    return explanation


def run_new_profile(learner: dict) -> dict:
    res = orchestrator.handle_event(
        event_type="new_profile",
        payload=learner,
        roles_data=roles_data,
        quizzes_data=quizzes_data,
    )
    for line in reversed(res.get("logs", [])):
        add_agent_log(line)
    return res


def run_goal_change(old_role: str, new_role: str, learner: dict) -> dict:
    res = orchestrator.handle_event(
        event_type="goal_change",
        payload={
            "old_role": old_role,
            "new_role": new_role,
            "profile": learner.get("profile", {}),
        },
        roles_data=roles_data,
        quizzes_data=quizzes_data,
    )
    for line in reversed(res.get("logs", [])):
        add_agent_log(line)
    return res


# ── AI status badge ────────────────────────────────────────────────────────────
def ai_status_html() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return '<span class="ai-badge badge-online">● AI Mentor: Connected</span>'
    return '<span class="ai-badge badge-offline">○ AI Mentor: Offline (basic tips)</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  DETAILS FORM  (first screen, also shown when editing profile)
# ══════════════════════════════════════════════════════════════════════════════
def show_details_form():
    # Centered card via column trick
    _, card_col, _ = st.columns([1, 3, 1])
    with card_col:
        st.markdown(
            """
            <div style="text-align:center; margin-bottom:28px;">
                <div style="font-size:2rem; font-weight:800; color:#0f172a;">SkillForge</div>
                <div style="font-size:1rem; color:#64748b; margin-top:6px; line-height:1.5;">
                    Tell us about yourself and we'll build your<br>personal learning plan.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        prof = st.session_state.learner.get("profile", {})
        is_editing = st.session_state.editing_profile

        # ── Fields ──
        user_name = st.text_input(
            "Your name",
            value=prof.get("name", ""),
            placeholder="e.g. Alex",
        )

        role_list    = list(roles_data.keys())
        default_role = prof.get("target_role", role_list[0])
        role_idx     = role_list.index(default_role) if default_role in role_list else 0
        target_role  = st.selectbox("Dream job", role_list, index=role_idx)

        saved_skills = prof.get("skills", [])
        default_sel  = [s for s in saved_skills if s in ALL_SKILLS]
        selected_skills = st.multiselect(
            "Skills you already have",
            options=ALL_SKILLS,
            default=default_sel,
            placeholder="Choose skills…",
        )

        saved_extra  = [s for s in saved_skills if s not in ALL_SKILLS]
        extra_skills = st.text_input(
            "Other skills (comma-separated)",
            value=", ".join(saved_extra),
            placeholder="e.g. Git, Figma, Basic Linux",
        )

        with st.expander("Optional: certifications & projects", expanded=False):
            certs = st.text_area(
                "Certifications (one per line)",
                value="\n".join(prof.get("certifications", [])),
                placeholder="Python Essentials\nCS50x",
                height=80,
            )
            projects = st.text_area(
                "Projects you've built (one per line)",
                value="\n".join(prof.get("projects", [])),
                placeholder="Personal portfolio\nCLI expense tracker",
                height=80,
            )

        st.write("")
        label = "Save and rebuild my plan" if is_editing else "Show my skill gaps"
        submit = st.button(label, type="primary", use_container_width=True)

        if submit:
            # ── Validation ──
            extras_list = [
                normalize_skill(s)
                for s in extra_skills.split(",")
                if s.strip()
            ]
            combined = list(selected_skills) + [
                s for s in extras_list if s not in selected_skills
            ]

            if not user_name.strip():
                st.warning("Please enter your name.")
                st.stop()
            if not combined:
                st.warning("Please select or enter at least one skill.")
                st.stop()

            # ── Build profile ──
            new_profile = {
                "name":           user_name.strip(),
                "target_role":    target_role,
                "skills":         combined,
                "certifications": [c.strip() for c in certs.split("\n") if c.strip()],
                "projects":       [p.strip() for p in projects.split("\n") if p.strip()],
            }

            old_role = st.session_state.learner.get("profile", {}).get("target_role")
            st.session_state.learner["profile"] = new_profile

            # Reset progress whenever profile is saved
            reset_progress()

            if is_editing and old_role and old_role != target_role:
                # Goal changed → goal_change event + clear skill explanation cache
                res = run_goal_change(old_role, target_role, st.session_state.learner)
                st.session_state.skill_explanations = {}
                save_json(EXPL_CACHE_FILE, {})
            else:
                # New profile (or same goal re-save)
                res = run_new_profile(st.session_state.learner)
                if is_editing:
                    # Same goal but profile changed: clear cache for safety
                    st.session_state.skill_explanations = {}
                    save_json(EXPL_CACHE_FILE, {})

            st.session_state.analysis_result  = res
            save_learner_data(st.session_state.learner)

            st.session_state.current_step    = "main"
            st.session_state.editing_profile = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP  (header + three tabs)
# ══════════════════════════════════════════════════════════════════════════════
def show_main_app():
    learner  = st.session_state.learner
    profile  = learner.get("profile", {})
    name     = profile.get("name", "Learner")
    role     = profile.get("target_role", "")

    # ── Header ──────────────────────────────────────────────────────────────
    h_left, h_right = st.columns([3, 2])
    with h_left:
        st.markdown(
            '<span style="font-size:1.4rem;font-weight:800;color:#0f172a;">SkillForge</span>',
            unsafe_allow_html=True,
        )
    with h_right:
        st.markdown(
            f'<div style="text-align:right;">'
            f'<span style="font-size:0.95rem;color:#334155;">Hi, <strong>{name}</strong></span><br>'
            f'{ai_status_html()}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Edit profile / change goal", key="edit_btn"):
            st.session_state.editing_profile = True
            st.session_state.current_step    = "details"
            st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 20px 0;">', unsafe_allow_html=True)

    # ── Three tabs ───────────────────────────────────────────────────────────
    tab_gap, tab_course, tab_mentor = st.tabs(["Skill Gap", "Course", "Mentor"])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1 · SKILL GAP
    # ──────────────────────────────────────────────────────────────────────────
    with tab_gap:
        analysis = st.session_state.analysis_result
        cm       = analysis.get("career_match", {})
        sa       = analysis.get("skill_analysis", {})

        matched   = cm.get("matched_skills", [])
        missing   = cm.get("missing_skills", [])
        readiness = int(cm.get("readiness_score", 0))
        n_missing = len(missing)

        # Summary sentence
        if n_missing == 0:
            summary = f"You are **{readiness}% ready** for {role}. You have all the core skills — great work!"
        elif n_missing == 1:
            summary = f"You are **{readiness}% ready** for {role}. Just 1 skill to go."
        else:
            summary = f"You are **{readiness}% ready** for {role}. {n_missing} skills to go."

        st.markdown(
            f'<p style="font-size:1.05rem;color:#334155;margin-bottom:12px;">{summary}</p>',
            unsafe_allow_html=True,
        )

        # Progress bar
        st.progress(readiness / 100)
        st.write("")

        # Green chips — skills you have
        if matched:
            chips_have = "".join(f'<span class="chip-have">{s}</span>' for s in matched)
            st.markdown(
                f'<div style="margin-bottom:6px;"><strong style="font-size:0.9rem;color:#065f46;">Skills you already have</strong></div>'
                f'<div style="margin-bottom:20px;">{chips_have}</div>',
                unsafe_allow_html=True,
            )

        # Orange chips — skills you need
        if missing:
            chips_need = "".join(f'<span class="chip-need">{s}</span>' for s in missing)
            st.markdown(
                f'<div style="margin-bottom:6px;"><strong style="font-size:0.9rem;color:#9a3412;">Skills you need to learn</strong></div>'
                f'<div style="margin-bottom:24px;">{chips_need}</div>',
                unsafe_allow_html=True,
            )
        elif n_missing == 0:
            st.success("You have mastered all core skills for this role!")

        # Coach note from SkillAnalyst
        coach_note = sa.get("summary", "")
        if coach_note:
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;'
                f'padding:14px 18px;font-size:0.93rem;color:#334155;line-height:1.55;margin-bottom:24px;">'
                f'<strong>Coach note:</strong> {coach_note}</div>',
                unsafe_allow_html=True,
            )

        # Per-skill expanders with AI explanations
        if missing:
            st.markdown(
                '<p style="font-size:0.9rem;font-weight:700;color:#1e293b;margin-bottom:8px;">'
                'What each skill is and why you need it</p>',
                unsafe_allow_html=True,
            )
            for skill in missing:
                with st.expander(skill):
                    expl = get_skill_explanation(skill, role, roles_data)
                    st.markdown(f'<div class="expl-text">{expl}</div>', unsafe_allow_html=True)

        st.write("")

        # Agent activity log (hackathon judges)
        with st.expander("See how your AI team worked", expanded=False):
            logs = learner.get("activity_log", [])[:10]
            if logs:
                for log in logs:
                    st.markdown(
                        f'<div class="agent-item">{humanize_log(log)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No agent activity recorded yet.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2 · COURSE  (Phase B placeholder)
    # ──────────────────────────────────────────────────────────────────────────
    with tab_course:
        st.info("Your personalised course plan is coming in the next phase.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3 · MENTOR  (Phase B placeholder)
    # ──────────────────────────────────────────────────────────────────────────
    with tab_mentor:
        st.info("Your AI mentor chat is coming in the next phase.")


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step == "details" or st.session_state.editing_profile:
    show_details_form()
else:
    show_main_app()
