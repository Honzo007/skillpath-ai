"""SkillForge AI — Phase A
Details form → Main app (Skill Gap tab, Course placeholder, Mentor placeholder)
No sidebar · No demo button · No landing cards · No step bar
"""
import os
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import quote_plus

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
SKILL_CONTENT_FILE = DATA_DIR / "skill_content.json"
SKILL_QUESTIONS_FILE = DATA_DIR / "skill_questions.json"


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
    st.session_state.learner["progress"] = {
        "completed": [],
        "status_map": {},
        "revision_skills": [],
        "ready_for_quiz": [],
        "course_agent_log": [],
    }
    st.session_state.learner["progress_role"] = st.session_state.learner.get("profile", {}).get("target_role", "")
    st.session_state.learner["quiz_history"] = []
    for key in list(st.session_state.keys()):
        if key.startswith("course_"):
            del st.session_state[key]


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


SKILL_SUBTOPICS = {
    "HTML & CSS": ["Semantic page structure", "Links, images, and forms", "Selectors and the cascade", "Box model and spacing", "Flexbox and Grid", "Responsive layouts", "Accessible markup"],
    "JavaScript": ["Values and variables", "Functions and scope", "Arrays and objects", "Conditions and loops", "DOM selection and updates", "Events and event delegation", "Promises and async/await"],
    "React": ["Components and JSX", "Props and reusable UI", "State and event handlers", "Rendering lists with keys", "Conditional rendering", "Effects and data loading", "Sharing state between components"],
    "Node.js": ["The Node.js runtime", "Modules and npm packages", "Asynchronous work and promises", "Reading and writing files", "HTTP servers and routes", "Express middleware", "Error handling for API requests"],
    "Python": ["Values and variables", "Conditions and loops", "Functions and arguments", "Lists, dictionaries, and sets", "Reading and writing files", "Exceptions and context managers", "Iterators and generators"],
    "SQL": ["Selecting and filtering rows", "Sorting and limiting results", "Joining related tables", "Grouping and aggregate functions", "Subqueries and common table expressions", "Constraints and data integrity", "Transactions and safe updates"],
    "Pandas & Data Analysis": ["Loading tabular data", "Selecting rows and columns", "Cleaning missing and duplicate values", "Grouping and summarizing", "Combining datasets", "Exploring distributions and outliers", "Avoiding data leakage in analysis"],
    "Machine Learning": ["Features, labels, and splits", "Choosing a baseline model", "Training and validation", "Overfitting and generalization", "Metrics for different tasks", "Cross-validation and tuning", "Preventing data leakage"],
    "Deep Learning": ["Tensors and batches", "Layers and forward passes", "Loss functions and gradients", "Training loops and optimizers", "Convolutional and sequence models", "Regularization and dropout", "Monitoring validation performance"],
    "Linux & Bash": ["Navigating files and directories", "Reading and editing files", "Pipes and redirection", "Permissions and ownership", "Variables and quoting", "Conditions and loops in scripts", "Handling errors and exit codes"],
    "Git & CI/CD": ["Working tree and staging", "Commits and branches", "Merging and resolving conflicts", "Remote repositories", "Automated test workflows", "Secrets and environment variables", "Reading pipeline failures"],
    "Docker": ["Images and containers", "Writing a Dockerfile", "Build context and caching", "Ports and environment settings", "Volumes and persistent data", "Networks and service communication", "Multi-stage builds"],
    "Kubernetes": ["Pods and containers", "Deployments and desired replicas", "Services and stable networking", "Configuration and secrets", "Readiness and liveness probes", "Scaling and resource requests", "Diagnosing failed workloads"],
}

VIDEO_SEARCHES = {
    "HTML & CSS": ["HTML CSS full course for beginners", "responsive web design project tutorial"],
    "JavaScript": ["JavaScript full course for beginners", "JavaScript DOM project tutorial"],
    "React": ["React full course for beginners", "React hooks project tutorial"],
    "Node.js": ["Node.js crash course", "Node.js Express REST API tutorial"],
    "Python": ["Python full course for beginners", "Python practical project tutorial"],
    "SQL": ["SQL full course for beginners", "SQL joins and aggregation practice"],
    "Pandas & Data Analysis": ["Pandas data analysis full course", "Pandas data cleaning project"],
    "Machine Learning": ["machine learning practical course for beginners", "scikit-learn classification project tutorial"],
    "Deep Learning": ["deep learning full course for beginners", "PyTorch image classification project tutorial"],
    "Linux & Bash": ["Linux command line full course for beginners", "Bash scripting practical tutorial"],
    "Git & CI/CD": ["Git and GitHub full course for beginners", "GitHub Actions CI workflow tutorial"],
    "Docker": ["Docker full course for beginners", "Docker multi-stage build tutorial"],
    "Kubernetes": ["Kubernetes full course for beginners", "Kubernetes deployment troubleshooting tutorial"],
}


def course_cache_key(role: str, skill: str) -> str:
    return f"{role}::{skill}"


def get_skill_subtopics(skill: str, role: str) -> List[str]:
    cache = load_json(SKILL_CONTENT_FILE)
    key = skill
    cached = cache.get(key)
    if isinstance(cached, list) and 5 <= len(cached) <= 8 and all(isinstance(item, str) for item in cached):
        return cached

    fallback = SKILL_SUBTOPICS.get(skill, [
        f"Core ideas behind {skill}",
        f"Common {skill} tools and workflows",
        f"Using {skill} to solve a practical problem",
        f"Testing and checking {skill} work",
        f"Building a small project with {skill}",
    ])
    try:
        from agents.base import BaseAgent
        prompt = (
            f"Create 5 to 8 concise plain-English checklist subtopics for learning {skill} "
            f"for a {role}. Return only a JSON array of strings, with no markdown or extra text."
        )
        response = BaseAgent("CourseContent").call_llm(prompt, "")
        generated = json.loads(response)
        if isinstance(generated, dict):
            generated = generated.get("subtopics")
        if isinstance(generated, list) and 5 <= len(generated) <= 8 and all(
            isinstance(item, str) and item.strip() for item in generated
        ):
            fallback = [item.strip() for item in generated]
    except Exception:
        pass

    cache[key] = fallback
    save_json(SKILL_CONTENT_FILE, cache)
    return fallback


def valid_course_quiz(questions: Any) -> bool:
    return (
        isinstance(questions, list)
        and len(questions) == 5
        and all(
            isinstance(question, dict)
            and isinstance(question.get("question"), str)
            and isinstance(question.get("options"), list)
            and len(question["options"]) == 4
            and all(isinstance(option, str) for option in question["options"])
            and question.get("correct_answer") in question["options"]
            and isinstance(question.get("explanation"), str)
            for question in questions
        )
    )


def parse_generated_quiz(response: str, skill: str) -> List[dict]:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].removesuffix("```").strip()
    payload = json.loads(cleaned)
    generated = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(generated, list) or len(generated) != 5:
        raise ValueError("Expected exactly five questions")

    questions = []
    for index, item in enumerate(generated):
        if not isinstance(item, dict):
            raise ValueError("Question must be an object")
        options = item.get("options")
        answer_index = item.get("answer_index")
        if (
            not isinstance(item.get("question"), str)
            or not item["question"].strip()
            or not isinstance(options, list)
            or len(options) != 4
            or not all(isinstance(option, str) and option.strip() for option in options)
            or isinstance(answer_index, bool)
            or not isinstance(answer_index, int)
            or answer_index < 0
            or answer_index >= 4
            or not isinstance(item.get("explanation"), str)
            or not item["explanation"].strip()
        ):
            raise ValueError("Question has an invalid shape")
        questions.append({
            "id": f"course_{index + 1}",
            "question": item["question"].strip(),
            "options": options,
            "correct_answer": options[answer_index],
            "explanation": item["explanation"].strip(),
        })
    if not valid_course_quiz(questions):
        raise ValueError(f"Invalid generated quiz for {skill}")
    return questions


def get_skill_quiz(skill: str, role: str) -> List[dict]:
    cache = load_json(SKILL_QUESTIONS_FILE)
    key = skill
    cached = cache.get(key)
    if valid_course_quiz(cached):
        return cached

    questions = None
    try:
        from agents.base import BaseAgent
        prompt = (
            f"Write exactly five challenging scenario-based multiple-choice questions about {skill} for a learner "
            f"preparing for {role}. Each must test applying concepts, not definitions. Use four plausible options, "
            f"one correct answer, and a short explanation. Return strict JSON only in this shape: "
            f"{{\"questions\":[{{\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],"
            f"\"answer_index\":0,\"explanation\":\"...\"}}]}}."
        )
        response = BaseAgent("CourseQuiz").call_llm(prompt, "")
        questions = parse_generated_quiz(response, skill)
    except Exception:
        fallback = quizzes_data.get(skill, [])
        questions = fallback if valid_course_quiz(fallback) else []

    cache[key] = questions
    save_json(SKILL_QUESTIONS_FILE, cache)
    return questions


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


def show_course_tab():
    learner = st.session_state.learner
    profile = learner.get("profile", {})
    role = profile.get("target_role", "")
    progress = learner.get("progress", {})
    if not isinstance(progress, dict) or learner.get("progress_role") != role:
        progress = {
            "completed": [],
            "status_map": {},
            "revision_skills": [],
            "ready_for_quiz": [],
            "course_agent_log": [],
        }
        learner["progress"] = progress
        learner["progress_role"] = role
        save_learner_data(learner)

    analysis = st.session_state.analysis_result
    missing_skills = analysis.get("career_match", {}).get("missing_skills", [])
    plan = orchestrator.curriculum_planner.run(
        missing_skills=missing_skills,
        target_role=role,
        roles_data=roles_data,
        existing_progress=progress,
    )
    roadmap = plan.get("roadmap", [])
    skills = [step for step in roadmap if not step.get("is_revision")]
    completed = set(progress.get("completed", []))
    ready_for_quiz = set(progress.get("ready_for_quiz", []))
    mastered_count = sum(step["skill"] in completed for step in skills)

    st.markdown("## Course")
    st.caption("Work through your skills in order. Learn, watch, practice, then take the quiz.")
    st.markdown(f"**{mastered_count} of {len(skills)} skills mastered**")
    st.progress(mastered_count / len(skills) if skills else 1.0)

    if not skills:
        st.success("There are no missing skills in your current learning plan.")

    revision_skills = {
        step["skill"] for step in roadmap if step.get("is_revision")
    }

    for step in skills:
        skill = step["skill"]
        status = step.get("status", "locked")
        card_key = quote_plus(course_cache_key(role, skill), safe="")
        result_key = f"course_quiz_result_{card_key}"
        skill_info = roles_data.get(role, {}).get("skills", {}).get(skill, {})

        with st.expander(
            f"{'🔒 ' if status == 'locked' else ''}{skill}",
            expanded=status == "in_progress" or bool(st.session_state.get(result_key)),
        ):
            if status == "locked":
                st.info("Finish the previous skill first.")
                continue

            title_suffix = " · Mastered" if status == "done" else ""
            if title_suffix:
                st.markdown(f"**{title_suffix.strip(' ·')}**")
            if skill in revision_skills:
                st.info("Revision step added. Review the material and retake the quiz.")

            st.markdown("**WHAT YOU'LL LEARN**")
            for topic_index, topic in enumerate(get_skill_subtopics(skill, role)):
                st.checkbox(topic, key=f"course_topic_{card_key}_{topic_index}")

            st.markdown("**WHERE TO LEARN**")
            for resource in skill_info.get("resources", [])[:3]:
                st.markdown(f"- [{resource['title']}]({resource['url']})")

            st.markdown("**WATCH**")
            queries = VIDEO_SEARCHES.get(skill, [
                f"{skill} full course for beginners",
                f"{skill} practical tutorial",
            ])
            for query in queries[:3]:
                search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                st.markdown(f"- [Watch: {query}]({search_url})")

            if status != "done" and skill not in ready_for_quiz:
                if st.button("Mark as done", key=f"course_mark_done_{card_key}"):
                    ready_for_quiz.add(skill)
                    progress["ready_for_quiz"] = sorted(ready_for_quiz)
                    learner["progress"] = progress
                    save_learner_data(learner)
                    st.rerun()

            if skill in ready_for_quiz or status == "done":
                questions = get_skill_quiz(skill, role)
                if not questions:
                    st.warning("A quiz is not available for this skill yet.")
                    continue

                st.markdown("**SKILL QUIZ**")
                attempt_key = f"course_quiz_attempt_{card_key}"
                result = st.session_state.get(result_key)

                if result is None:
                    attempt = st.session_state.get(attempt_key, 0)
                    with st.form(f"course_quiz_form_{card_key}_{attempt}"):
                        selections = []
                        for question_index, question in enumerate(questions):
                            selections.append(
                                st.radio(
                                    f"{question_index + 1}. {question['question']}",
                                    question["options"],
                                    index=None,
                                    key=f"course_answer_{card_key}_{attempt}_{question_index}",
                                )
                            )
                        submit_quiz = st.form_submit_button("Submit", type="primary")

                    if submit_quiz:
                        if any(answer is None for answer in selections):
                            st.warning("Answer all five questions before submitting.")
                        else:
                            answers = {
                                question["id"]: answer
                                for question, answer in zip(questions, selections)
                            }
                            course_quizzes = dict(quizzes_data)
                            course_quizzes[skill] = questions
                            event_result = orchestrator.handle_event(
                                event_type="quiz_result",
                                payload={
                                    "skill": skill,
                                    "user_answers": answers,
                                    "profile": profile,
                                    "progress": progress,
                                },
                                roles_data=roles_data,
                                quizzes_data=course_quizzes,
                            )
                            assessment = event_result.get("assessment", {})
                            mentor_message = event_result.get("mentor", {}).get("message", "")
                            correct_count = assessment.get("correct_count", 0)
                            total_questions = assessment.get("total_questions", 0)
                            passed = assessment.get("score", 0) >= 60
                            if passed:
                                summary = (
                                    f"Assessment Agent scored {skill} {correct_count}/{total_questions}. "
                                    "Curriculum Planner marked the skill mastered and unlocked the next skill. "
                                )
                            else:
                                summary = (
                                    f"Assessment Agent scored {skill} {correct_count}/{total_questions}. "
                                    "Curriculum Planner added a revision step. "
                                )
                            if mentor_message:
                                summary += f"Mentor: {mentor_message}"

                            updated_progress = event_result.get("updated_progress", {})
                            updated_progress["ready_for_quiz"] = sorted(ready_for_quiz)
                            course_agent_log = list(progress.get("course_agent_log", []))
                            course_agent_log.insert(0, summary)
                            updated_progress["course_agent_log"] = course_agent_log[:20]
                            learner["progress"] = updated_progress
                            learner["progress_role"] = role
                            for line in reversed(event_result.get("logs", [])):
                                add_agent_log(line)
                            save_learner_data(learner)
                            st.session_state[result_key] = event_result
                            st.rerun()
                else:
                    assessment = result.get("assessment", {})
                    correct_count = assessment.get("correct_count", 0)
                    total_questions = assessment.get("total_questions", 0)
                    passed = assessment.get("score", 0) >= 60
                    st.markdown(f"### Score: {correct_count}/{total_questions}")
                    for item in assessment.get("breakdown", []):
                        label = "Right" if item.get("is_correct") else "Wrong"
                        st.markdown(f"**{label}: {item.get('question', '')}**")
                        st.write(f"Your answer: {item.get('user_answer', '')}")
                        st.write(f"Correct answer: {item.get('correct_answer', '')}")
                        st.caption(item.get("explanation", ""))

                    if passed:
                        st.success("Skill mastered. The next skill is now unlocked.")
                    else:
                        st.info(result.get("mentor", {}).get("message", "Review the material and try again."))
                        if st.button("Retake quiz", key=f"course_retake_{card_key}"):
                            st.session_state[attempt_key] = st.session_state.get(attempt_key, 0) + 1
                            st.session_state[result_key] = None
                            st.rerun()

    with st.expander("See how your AI team worked", expanded=False):
        agent_lines = progress.get("course_agent_log", [])
        if agent_lines:
            for line in agent_lines[:10]:
                st.write(line)
        else:
            st.caption("Your assessment activity will appear here.")


def get_quiz_attempts(learner: dict) -> Dict[str, List[dict]]:
    attempts: Dict[str, List[dict]] = {}
    quiz_history = learner.get("quiz_history", [])
    if quiz_history:
        for item in quiz_history:
            skill = item.get("skill")
            score = item.get("score", item.get("score_pct"))
            correct = item.get("correct_count")
            total = item.get("total_questions")
            if score is None and total:
                score = (float(correct or 0) / total) * 100
            if skill and score is not None:
                score = float(score)
                if 0 <= score <= 1:
                    score *= 100
                attempts.setdefault(skill, []).append({
                    "score": round(score, 1),
                    "correct_count": correct,
                    "total_questions": total,
                })
        return attempts

    assessment_pattern = re.compile(
        r"Assessment: evaluated (.+?) quiz -> (\d+)/(\d+) correct \(([\d.]+)%\)"
    )
    for line in reversed(learner.get("activity_log", [])):
        if "Orchestrator: Target role switched" in line or (
            "Mentor: delivered personalized guidance for event 'new_profile'" in line
        ):
            attempts = {}
        if "Mentor: delivered personalized guidance for event 'goal_change'" in line:
            attempts = {}
        match = assessment_pattern.search(line)
        if match:
            skill, correct, total, score = match.groups()
            attempts.setdefault(skill, []).append({
                "score": float(score),
                "correct_count": int(correct),
                "total_questions": int(total),
            })
    return attempts


def find_plan_change_note(activity_log: List[str], target_role: str) -> str:
    for line in activity_log:
        role_change = re.search(r"Target role switched from '(.+?)' to '(.+?)'", line)
        if role_change:
            old_role, new_role = role_change.groups()
            if new_role == target_role:
                return f"Your goal changed from {old_role} to {new_role}, so your skill plan was rebuilt for {new_role}."
            break

        revision = re.search(r"Score ([\d.]+)% on '(.+?)' < 60%", line)
        if revision:
            score, skill = revision.groups()
            return f"Your {skill} quiz score was {score}%, so a revision step was added before moving on."

        mastered = re.search(r"Mastered '(.+?)' \(score ([\d.]+)%\)", line)
        if mastered:
            skill, score = mastered.groups()
            return f"You scored {score}% on {skill}, so it was marked mastered and the next step unlocked."

        if "Mentor: delivered personalized guidance for event 'new_profile'" in line:
            break
    return ""


def build_mentor_summary(learner: dict, analysis: dict) -> dict:
    profile = learner.get("profile", {})
    role = profile.get("target_role", "")
    role_skills = list(roles_data.get(role, {}).get("skills", {}).keys())
    progress = learner.get("progress", {})
    completed = set(progress.get("completed", []))
    status_map = progress.get("status_map", {})
    ready_for_quiz = set(progress.get("ready_for_quiz", []))
    career_match = analysis.get("career_match", {})
    matched = set(career_match.get("matched_skills", []))
    missing = set(career_match.get("missing_skills", []))
    if not matched and profile.get("skills"):
        matched.update(skill for skill in profile["skills"] if skill in role_skills)

    mastered = [skill for skill in role_skills if skill in matched or skill in completed]
    missing_skills = [
        skill for skill in role_skills
        if (skill in missing or skill not in matched) and skill not in completed
    ]
    quiz_attempts = get_quiz_attempts(learner)
    latest_scores = {
        skill: history[-1]["score"]
        for skill, history in quiz_attempts.items()
        if history
    }
    weak_skills = [
        skill for skill in role_skills
        if latest_scores.get(skill, 100) < 60
    ]
    in_progress = [
        skill for skill in role_skills
        if skill not in mastered and (
            status_map.get(skill) == "in_progress"
            or skill in ready_for_quiz
            or latest_scores.get(skill, 100) < 60
        )
    ]
    not_started = [
        skill for skill in role_skills
        if skill not in mastered and skill not in in_progress
    ]

    weak_next = next((skill for skill in role_skills if skill in weak_skills), None)
    if weak_next:
        next_step = f"Retake your {weak_next} quiz ({latest_scores[weak_next]:g}%)"
    elif in_progress:
        next_step = f"Continue {in_progress[0]} in the Course tab"
    elif not_started:
        next_step = f"Start {not_started[0]} in the Course tab"
    else:
        next_step = f"Practice an interview question for {role}"

    total_skills = len(role_skills)
    average_quiz_score = (
        round(sum(latest_scores.values()) / len(latest_scores), 1)
        if latest_scores else None
    )
    readiness_value = career_match.get("readiness_score")
    readiness = (
        round(float(readiness_value))
        if readiness_value is not None
        else round(len(mastered) / total_skills * 100) if total_skills else 0
    )
    rating = "Getting started" if readiness < 40 else "On track" if readiness < 75 else "Strong progress"
    activity_log = learner.get("activity_log", [])
    weakest_skill = min(
        (skill for skill in role_skills if skill in latest_scores),
        key=lambda skill: latest_scores[skill],
        default=None,
    )

    return {
        "name": profile.get("name", "Learner"),
        "target_role": role,
        "readiness": readiness,
        "overall_rating": rating,
        "mastered_count": len(mastered),
        "total_skills": total_skills,
        "average_quiz_score": average_quiz_score,
        "skill_status_counts": {
            "Mastered": len(mastered),
            "In progress": len(in_progress),
            "Not started": len(not_started),
        },
        "matched_skills": [skill for skill in role_skills if skill in matched],
        "mastered_skills": mastered,
        "missing_skills": missing_skills,
        "weak_quiz_skills": weak_skills,
        "latest_quiz_scores": [
            {"skill": skill, "score": latest_scores[skill]}
            for skill in role_skills if skill in latest_scores
        ],
        "weakest_skill": weakest_skill,
        "quiz_attempt_counts": {
            skill: len(quiz_attempts.get(skill, [])) for skill in role_skills
        },
        "quiz_table": [
            {
                "Skill": skill,
                "Latest score": f"{latest_scores[skill]}%" if skill in latest_scores else "Not taken",
                "Attempts": len(quiz_attempts.get(skill, [])),
            }
            for skill in role_skills
        ],
        "next_step": next_step,
        "plan_change_note": find_plan_change_note(activity_log, role),
    }


def fallback_mentor_note(summary: dict) -> str:
    name = summary["name"]
    role = summary["target_role"]
    latest = summary["latest_quiz_scores"]
    if latest:
        weakest = min(latest, key=lambda item: item["score"])
        next_sentence = (
            f"Your weakest latest quiz is {weakest['skill']} at {weakest['score']}%; "
            f"your next step is to {summary['next_step'][0].lower() + summary['next_step'][1:]}."
        )
    else:
        next_sentence = f"Your next step is to {summary['next_step'][0].lower() + summary['next_step'][1:]}."
    return (
        f"{name}, your target role is {role}, and you are {summary['overall_rating'].lower()} "
        f"at {summary['readiness']}% readiness. {next_sentence}"
    )


def log_mentor_action(agent_result: dict, plain_sentence: str):
    learner = st.session_state.learner
    add_agent_log(agent_result.get("log_message", "Mentor: completed a learning task"))
    add_agent_log(f"Mentor Agent: {plain_sentence}")
    mentor_lines = st.session_state.setdefault("mentor_agent_log", [])
    mentor_lines.insert(0, plain_sentence)
    st.session_state.mentor_agent_log = mentor_lines[:20]
    save_learner_data(learner)


def show_mentor_tab():
    learner = st.session_state.learner
    summary = build_mentor_summary(learner, st.session_state.analysis_result)

    role = summary["target_role"] or "Target role not set"
    st.markdown("## Mentor")
    st.caption("Your progress at a glance.")
    st.write(f"Target role: **{role}**")
    refresh_note = st.button("Refresh analysis", key="mentor_refresh_analysis")

    fingerprint = hashlib.sha256(
        json.dumps(summary, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    report_cache = st.session_state.setdefault("mentor_report_cache", {})
    if refresh_note or fingerprint not in report_cache:
        report_result = orchestrator.mentor.run(
            event_type="mentor_report",
            context={
                "summary": summary,
                "fallback_message": fallback_mentor_note(summary),
            },
        )
        report_cache[fingerprint] = {
            "message": report_result["message"],
            "offline": report_result.get("offline", False),
        }
        st.session_state.mentor_report_cache = report_cache
        quiz_count = sum(summary["quiz_attempt_counts"].values())
        log_mentor_action(
            report_result,
            f"Reviewed {quiz_count} quiz attempts and recommended: {summary['next_step']}.",
        )
    report_note = report_cache[fingerprint]

    overview = st.columns(4)
    card_values = [
        ("Readiness", f"{summary['readiness']}%"),
        ("Skills mastered", f"{summary['mastered_count']} of {summary['total_skills']}"),
        ("Average quiz score", f"{summary['average_quiz_score']}%" if summary["average_quiz_score"] is not None else "—"),
        ("Overall rating", summary["overall_rating"]),
    ]
    for column, (label, value) in zip(overview, card_values):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"### {value}")

    import altair as alt

    readiness_col, status_col = st.columns(2)
    with readiness_col:
        st.markdown("#### Readiness")
        st.progress(summary["readiness"] / 100)
        st.caption(f"You are {summary['readiness']}% ready for your target role.")

    with status_col:
        st.markdown("#### Skill status")
        status_data = [
            {"status": status, "skills": count}
            for status, count in summary["skill_status_counts"].items()
        ]
        status_colors = alt.Scale(
            domain=["Mastered", "In progress", "Not started"],
            range=["#15803d", "#2563eb", "#cbd5e1"],
        )
        status_chart = (
            alt.Chart(alt.Data(values=status_data))
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("status:N", title=None, sort=["Mastered", "In progress", "Not started"]),
                y=alt.Y("skills:Q", title="Skills", scale=alt.Scale(domain=[0, max(1, summary['total_skills'])])),
                color=alt.Color("status:N", scale=status_colors, legend=None),
                tooltip=[alt.Tooltip("status:N", title="Status"), alt.Tooltip("skills:Q", title="Skills")],
            )
            .properties(height=170)
        )
        st.altair_chart(status_chart, use_container_width=True)
        st.caption("Each bar counts skills by their current learning status.")

    quiz_scores = summary["latest_quiz_scores"]
    st.markdown("#### Quiz scores by skill")
    if quiz_scores:
        score_data = [{"skill": item["skill"], "score": item["score"]} for item in quiz_scores]
        score_chart = alt.Chart(alt.Data(values=score_data)).mark_bar(size=18).encode(
            y=alt.Y("skill:N", title=None, sort=alt.SortField(field="score", order="ascending")),
            x=alt.X("score:Q", title="Latest score (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.condition(
                alt.datum.score >= 60,
                alt.value("#15803d"),
                alt.value("#ea580c"),
            ),
            tooltip=[alt.Tooltip("skill:N", title="Skill"), alt.Tooltip("score:Q", title="Latest score", format=".1f")],
        )
        pass_mark = alt.Chart(alt.Data(values=[{"score": 60}])).mark_rule(
            color="#2563eb", strokeDash=[5, 4], size=2
        ).encode(x="score:Q")
        quiz_chart = (score_chart + pass_mark).properties(
            height=max(120, 32 * len(score_data)),
            title=alt.TitleParams(text="Latest quiz score by skill", subtitle="Vertical line: Pass mark (60%)"),
        )
        st.altair_chart(quiz_chart, use_container_width=True)
        st.caption("Each bar shows the latest attempt; orange is below the 60% pass mark.")
    else:
        st.info("No quiz scores yet. Your latest scores will appear here after your first Course quiz.")
        st.caption("The score chart appears after your first quiz attempt.")

    with st.container(border=True):
        st.markdown("#### Your next step")
        st.write(summary["next_step"])

    if summary["plan_change_note"]:
        st.markdown(f"**What changed and why:** {summary['plan_change_note']}")

    st.markdown("### Mentor's note")
    st.write(report_note["message"])
    if report_note["offline"]:
        st.caption("Mentor is in offline mode")

    with st.expander("View quiz details", expanded=False):
        if quiz_scores:
            st.dataframe(summary["quiz_table"], hide_index=True, use_container_width=True)
        else:
            st.caption("No quiz attempts to show yet.")

    with st.expander("See how your AI team worked", expanded=False):
        mentor_lines = st.session_state.get("mentor_agent_log", [])
        if not mentor_lines:
            mentor_lines = [
                line.removeprefix("Mentor Agent: ")
                for line in learner.get("activity_log", [])
                if line.startswith("Mentor Agent: ")
            ]
        if mentor_lines:
            for line in mentor_lines[:10]:
                sentence = line[0].lower() + line[1:] if line else "completed a task."
                st.write(f"Mentor Agent {sentence}")
        else:
            st.caption("Mentor report activity will appear here.")


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
    # TAB 2 · COURSE  (Phase B1)
    # ──────────────────────────────────────────────────────────────────────────
    with tab_course:
        show_course_tab()

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3 · MENTOR  (Phase B placeholder)
    # ──────────────────────────────────────────────────────────────────────────
    with tab_mentor:
        show_mentor_tab()


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step == "details" or st.session_state.editing_profile:
    show_details_form()
else:
    show_main_app()
