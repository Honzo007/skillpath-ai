"""Assessment agent: serves quiz questions and evaluates scores."""
from typing import Dict, List, Any
from agents.base import BaseAgent


class Assessment(BaseAgent):
    """Handles skill diagnostic quizzes and scoring."""

    def __init__(self):
        super().__init__(name="Assessment")

    def run(self, skill: str, user_answers: Dict[str, str], quizzes_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores user answers against quizzes_data for the specified skill.
        """
        questions = quizzes_data.get(skill, [])
        if not questions:
            return {
                "skill": skill,
                "score": 0.0,
                "correct_count": 0,
                "total_questions": 0,
                "breakdown": [],
                "log_message": f"{self.name}: No quiz available for {skill}"
            }

        correct_count = 0
        breakdown = []

        for q in questions:
            q_id = q.get("id", "")
            user_ans = user_answers.get(q_id, "").strip()
            correct_ans = q.get("correct_answer", "").strip()
            is_correct = (user_ans.lower() == correct_ans.lower())

            if is_correct:
                correct_count += 1

            breakdown.append({
                "id": q_id,
                "question": q.get("question"),
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "")
            })

        total = len(questions)
        score_pct = round((correct_count / total * 100), 1) if total > 0 else 0.0
        log_message = f"{self.name}: evaluated {skill} quiz -> {correct_count}/{total} correct ({score_pct}%)"

        return {
            "skill": skill,
            "score": score_pct,
            "correct_count": correct_count,
            "total_questions": total,
            "breakdown": breakdown,
            "log_message": log_message
        }
