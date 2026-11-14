"""CareerMatch agent: compares learner skills against target role requirements."""
from typing import Dict, List, Any
from agents.base import BaseAgent


def _normalize_skill(skill: str) -> str:
    """Normalize skill name for matching (lowercase, trimmed, strip versioning)."""
    s = skill.lower().strip()
    s = s.replace("basic ", "").replace("core ", "")
    if s in ["html", "css", "html/css", "html5", "css3", "html & css"]:
        return "html & css"
    if s in ["js", "javascript (es6)", "es6", "vanilla js"]:
        return "javascript"
    if s in ["python3", "python 3", "py"]:
        return "python"
    if s in ["postgres", "postgresql", "mysql", "sqlite", "relational sql"]:
        return "sql"
    if s in ["react.js", "reactjs"]:
        return "react"
    if s in ["nodejs", "node"]:
        return "node.js"
    if s in ["pandas", "pandas & numpy", "data analysis"]:
        return "pandas & data analysis"
    if s in ["ml", "machine learning basics"]:
        return "machine learning"
    if s in ["dl", "neural networks", "pytorch", "tensorflow"]:
        return "deep learning"
    if s in ["linux", "bash", "shell scripting"]:
        return "linux & bash"
    if s in ["git", "github actions", "ci/cd"]:
        return "git & ci/cd"
    return s


class CareerMatch(BaseAgent):
    """Compares learner skills against role requirements to compute gaps and readiness."""

    def __init__(self):
        super().__init__(name="CareerMatch")

    def run(self, learner_skills: List[str], target_role: str, roles_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare skills vs role requirements.
        Returns matched skills, missing skills, readiness percentage, and one-line log message.
        """
        role_info = roles_data.get(target_role)
        if not role_info or "skills" not in role_info:
            return {
                "role": target_role,
                "matched_skills": [],
                "missing_skills": [],
                "readiness_score": 0.0,
                "total_skills": [],
                "log_message": f"{self.name}: Unknown role '{target_role}'",
            }

        role_skills = role_info["skills"]
        normalized_learner_skills = {_normalize_skill(s) for s in learner_skills}

        matched = []
        missing = []

        for skill_name in role_skills.keys():
            norm_role_skill = _normalize_skill(skill_name)
            # Check if normalized skill matches any learner skill
            if any(norm_role_skill == ls or ls in norm_role_skill or norm_role_skill in ls for ls in normalized_learner_skills):
                matched.append(skill_name)
            else:
                missing.append(skill_name)

        total_count = len(role_skills)
        readiness_score = round((len(matched) / total_count * 100), 1) if total_count > 0 else 0.0

        gap_str = ", ".join(missing) if missing else "None"
        log_message = f"{self.name}: found {len(missing)} gaps ({gap_str}), readiness {readiness_score}%"

        return {
            "role": target_role,
            "matched_skills": matched,
            "missing_skills": missing,
            "readiness_score": readiness_score,
            "total_skills": list(role_skills.keys()),
            "log_message": log_message,
        }
