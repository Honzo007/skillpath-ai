"""Orchestrator: routes system events and coordinates multi-agent workflow."""
from typing import Dict, Any, List
from agents.career_match import CareerMatch
from agents.skill_analyst import SkillAnalyst
from agents.curriculum_planner import CurriculumPlanner
from agents.assessment import Assessment
from agents.mentor import Mentor


class Orchestrator:
    """Dispatches events across the multi-agent system and tracks activity logs."""

    def __init__(self):
        self.career_match = CareerMatch()
        self.skill_analyst = SkillAnalyst()
        self.curriculum_planner = CurriculumPlanner()
        self.assessment = Assessment()
        self.mentor = Mentor()

    def handle_event(self, event_type: str, payload: Dict[str, Any], roles_data: Dict[str, Any], quizzes_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinates event execution:
        - new_profile: SkillAnalyst -> CareerMatch -> CurriculumPlanner -> Mentor
        - quiz_result: Assessment -> (conditional revision or unlock) -> Mentor
        - goal_change: CareerMatch -> CurriculumPlanner -> Mentor
        """
        new_logs: List[str] = []
        result: Dict[str, Any] = {"event_type": event_type}

        if event_type == "new_profile":
            profile = payload.get("profile", {})
            skills = profile.get("skills", [])
            target_role = profile.get("target_role", "Full Stack Developer")
            quiz_history = payload.get("quiz_history", [])

            # 1. CareerMatch
            cm_res = self.career_match.run(learner_skills=skills, target_role=target_role, roles_data=roles_data)
            new_logs.append(cm_res["log_message"])

            # 2. SkillAnalyst
            sa_res = self.skill_analyst.run(
                profile=profile,
                matched_skills=cm_res["matched_skills"],
                missing_skills=cm_res["missing_skills"],
                quiz_history=quiz_history
            )
            new_logs.append(sa_res["log_message"])

            # 3. CurriculumPlanner
            cp_res = self.curriculum_planner.run(
                missing_skills=cm_res["missing_skills"],
                target_role=target_role,
                roles_data=roles_data,
                existing_progress=payload.get("progress", {})
            )
            new_logs.append(cp_res["log_message"])

            # 4. Mentor
            mentor_context = {
                "learner_name": profile.get("name", "Learner"),
                "target_role": target_role,
                "readiness_score": cm_res["readiness_score"],
                "missing_skills": cm_res["missing_skills"]
            }
            m_res = self.mentor.run(event_type="new_profile", context=mentor_context)
            new_logs.append(m_res["log_message"])

            result.update({
                "career_match": cm_res,
                "skill_analysis": sa_res,
                "curriculum": cp_res,
                "mentor": m_res,
                "logs": new_logs
            })

        elif event_type == "quiz_result":
            skill = payload.get("skill", "")
            user_answers = payload.get("user_answers", {})
            profile = payload.get("profile", {})
            target_role = profile.get("target_role", "Full Stack Developer")
            existing_progress = payload.get("progress", {})

            # 1. Assessment
            ass_res = self.assessment.run(skill=skill, user_answers=user_answers, quizzes_data=quizzes_data)
            new_logs.append(ass_res["log_message"])

            score = ass_res["score"]
            completed_skills = set(existing_progress.get("completed", []))
            status_map = dict(existing_progress.get("status_map", {}))
            revision_skills = set(existing_progress.get("revision_skills", []))

            # 2. Conditional Curriculum Planning
            rebuild_needed = False
            if score >= 60:
                completed_skills.add(skill)
                revision_skills.discard(skill)
                status_map[skill] = "done"
                rebuild_needed = True
                new_logs.append(f"CurriculumPlanner: Mastered '{skill}' (score {score}%). Unlocking subsequent prerequisite steps.")
            elif score < 60:
                completed_skills.discard(skill)
                revision_skills.add(skill)
                status_map[skill] = "in_progress"
                new_logs.append(f"CurriculumPlanner: Score {score}% on '{skill}' < 60%. Injecting revision resources and diagnostic review.")
                rebuild_needed = True
            else:
                status_map[skill] = "in_progress"

            updated_progress = {
                "completed": list(completed_skills),
                "status_map": status_map,
                "revision_skills": list(revision_skills)
            }

            # Re-run career match & curriculum planner
            cm_res = self.career_match.run(learner_skills=profile.get("skills", []), target_role=target_role, roles_data=roles_data)
            cp_res = self.curriculum_planner.run(
                missing_skills=cm_res["missing_skills"],
                target_role=target_role,
                roles_data=roles_data,
                existing_progress=updated_progress
            )
            if rebuild_needed:
                new_logs.append(cp_res["log_message"])

            # 3. Mentor
            mentor_context = {
                "learner_name": profile.get("name", "Learner"),
                "skill": skill,
                "score": score,
                "target_role": target_role
            }
            m_res = self.mentor.run(event_type="quiz_result", context=mentor_context)
            new_logs.append(m_res["log_message"])

            result.update({
                "assessment": ass_res,
                "updated_progress": updated_progress,
                "career_match": cm_res,
                "curriculum": cp_res,
                "mentor": m_res,
                "logs": new_logs
            })

        elif event_type == "goal_change":
            old_role = payload.get("old_role", "")
            new_role = payload.get("new_role", "")
            profile = payload.get("profile", {})
            profile["target_role"] = new_role
            skills = profile.get("skills", [])

            # 1. CareerMatch
            cm_res = self.career_match.run(learner_skills=skills, target_role=new_role, roles_data=roles_data)
            new_logs.append(f"Orchestrator: Target role switched from '{old_role}' to '{new_role}'")
            new_logs.append(cm_res["log_message"])

            # 2. CurriculumPlanner (rebuild)
            cp_res = self.curriculum_planner.run(
                missing_skills=cm_res["missing_skills"],
                target_role=new_role,
                roles_data=roles_data,
                existing_progress={"completed": [], "status_map": {}}
            )
            new_logs.append(cp_res["log_message"])

            # 3. Mentor
            mentor_context = {
                "learner_name": profile.get("name", "Learner"),
                "old_role": old_role,
                "target_role": new_role,
                "readiness_score": cm_res["readiness_score"],
                "missing_skills": cm_res["missing_skills"]
            }
            m_res = self.mentor.run(event_type="goal_change", context=mentor_context)
            new_logs.append(m_res["log_message"])

            result.update({
                "profile": profile,
                "career_match": cm_res,
                "curriculum": cp_res,
                "mentor": m_res,
                "logs": new_logs
            })

        return result
