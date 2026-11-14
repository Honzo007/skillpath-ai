"""SkillAnalyst agent: evaluates strengths, weaknesses, and generates summary."""
from typing import Dict, List, Any
from agents.base import BaseAgent


class SkillAnalyst(BaseAgent):
    """Rates strengths/weaknesses from profile and quiz scores."""

    def __init__(self):
        super().__init__(name="SkillAnalyst")

    def run(self, profile: Dict[str, Any], matched_skills: List[str], missing_skills: List[str], quiz_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synthesize learner profile, matched skills, and quiz history into strengths & weaknesses.
        """
        quiz_history = quiz_history or []
        strengths = list(matched_skills)
        weaknesses = list(missing_skills)

        # Include quiz insights if available
        low_score_skills = []
        for q in quiz_history:
            if q.get("score", 0) < 60 and q.get("skill") not in low_score_skills:
                low_score_skills.append(q["skill"])

        rule_summary = (
            f"Learner demonstrates core competencies in {', '.join(strengths) if strengths else 'foundational concepts'}. "
            f"Primary growth areas to reach the target role are {', '.join(weaknesses) if weaknesses else 'advanced mastery'}."
        )

        prompt = (
            f"You are an expert technical career coach. Write a concise 2-sentence summary of this learner's profile.\n"
            f"Learner Name: {profile.get('name', 'Learner')}\n"
            f"Target Role: {profile.get('target_role', 'Target Role')}\n"
            f"Verified Strengths: {', '.join(strengths)}\n"
            f"Skill Gaps: {', '.join(weaknesses)}\n"
            f"Certifications: {', '.join(profile.get('certifications', []))}\n"
            f"Projects: {', '.join(profile.get('projects', []))}\n"
            f"Keep it motivating, professional, and under 50 words."
        )

        llm_summary = self.call_llm(prompt=prompt, fallback_text=rule_summary)

        log_message = f"{self.name}: analyzed profile, identified {len(strengths)} strengths and {len(weaknesses)} focus areas"

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "summary": llm_summary,
            "log_message": log_message,
        }
