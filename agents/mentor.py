"""Mentor agent: explains feedback, roadmap changes, and delivers guidance."""
from typing import Dict, Any
from agents.base import BaseAgent


class Mentor(BaseAgent):
    """Explains feedback, assessment results, and plan changes in plain language."""

    def __init__(self):
        super().__init__(name="Mentor")

    def run(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate plain-language mentor advice tailored to the current event.
        """
        learner_name = context.get("learner_name", "Learner")
        target_role = context.get("target_role", "Target Role")

        if event_type == "new_profile":
            readiness = context.get("readiness_score", 0.0)
            gaps = context.get("missing_skills", [])
            fallback = (
                f"Welcome aboard, {learner_name}! You're currently {readiness}% ready for the {target_role} role. "
                f"We've structured your initial roadmap focusing on {', '.join(gaps[:2]) if gaps else 'next steps'}. "
                f"Work through each tutorial and hands-on exercise, then take the skill assessment to unlock subsequent milestones!"
            )
            prompt = (
                f"You are an encouraging AI mentor. Greet {learner_name} who is aiming for {target_role}. "
                f"Readiness score is {readiness}%, and main gaps are {', '.join(gaps)}. "
                f"Provide concise, actionable advice (under 60 words) on how to start their roadmap."
            )
        elif event_type == "quiz_result":
            skill = context.get("skill", "this skill")
            score = context.get("score", 0.0)
            if score < 60:
                fallback = (
                    f"Good effort on the {skill} assessment ({score}%), {learner_name}! "
                    f"Because your score is below 60%, I've added targeted revision resources to your roadmap. "
                    f"Review the core concepts and try again when you feel confident."
                )
            elif score >= 80:
                fallback = (
                    f"Outstanding job, {learner_name}! You scored {score}% on {skill}. "
                    f"This skill is officially marked as mastered, and the next step on your roadmap is unlocked!"
                )
            else:
                fallback = (
                    f"Solid work on {skill} ({score}%), {learner_name}! "
                    f"You have a working grasp of the material. Review any incorrect answers before proceeding."
                )
            prompt = (
                f"You are an AI mentor. {learner_name} scored {score}% on the {skill} quiz. "
                f"Give brief, empathetic, and constructive feedback (under 40 words)."
            )
        elif event_type == "goal_change":
            old_role = context.get("old_role", "Previous Role")
            fallback = (
                f"Great pivot, {learner_name}! Shifting from {old_role} to {target_role}. "
                f"I've re-analyzed your skill set against the new role and rebuilt your personalized roadmap."
            )
            prompt = (
                f"You are an AI mentor. {learner_name} changed career target from {old_role} to {target_role}. "
                f"Explain encouragingly in 2 sentences that their roadmap has been dynamically adapted."
            )
        else:
            fallback = f"Keep pushing forward, {learner_name}! Every milestone brings you closer to {target_role}."
            prompt = fallback

        message = self.call_llm(prompt=prompt, fallback_text=fallback)
        log_message = f"{self.name}: delivered personalized guidance for event '{event_type}'"

        return {
            "message": message,
            "log_message": log_message
        }
