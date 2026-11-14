"""CurriculumPlanner agent: builds ordered roadmap from gaps using curated resources."""
from typing import Dict, List, Any
from agents.base import BaseAgent


class CurriculumPlanner(BaseAgent):
    """Orders learning steps respecting prerequisites and assigns curated resources."""

    def __init__(self):
        super().__init__(name="CurriculumPlanner")

    def run(self, missing_skills: List[str], target_role: str, roles_data: Dict[str, Any], existing_progress: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Builds an ordered roadmap from skill gaps respecting prerequisites.
        """
        role_info = roles_data.get(target_role, {})
        skills_info = role_info.get("skills", {})
        existing_progress = existing_progress or {}

        # Filter missing skills present in role_info
        gap_items = []
        for skill in missing_skills:
            if skill in skills_info:
                info = skills_info[skill]
                gap_items.append({
                    "skill": skill,
                    "order": info.get("order", 99),
                    "difficulty": info.get("difficulty", "Beginner"),
                    "prerequisites": info.get("prerequisites", []),
                    "resources": info.get("resources", [])
                })

        # Sort primarily by role defined order
        gap_items.sort(key=lambda x: x["order"])

        roadmap_steps = []
        completed_skills = set(existing_progress.get("completed", []))
        revision_skills = set(existing_progress.get("revision_skills", []))

        for idx, item in enumerate(gap_items):
            skill = item["skill"]
            prereqs = item["prerequisites"]
            # A step is unlocked if all its prerequisites are either not in missing_skills or already completed
            unmet_prereqs = [p for p in prereqs if p in missing_skills and p not in completed_skills]
            previous_skills_done = all(
                earlier["skill"] in completed_skills for earlier in gap_items[:idx]
            )
            
            if skill in completed_skills:
                status = "done"
            elif not unmet_prereqs and previous_skills_done:
                status = "in_progress"
            else:
                status = "locked"

            # Check if existing status takes precedence
            if skill in completed_skills and skill in existing_progress.get("status_map", {}):
                status = existing_progress["status_map"][skill]

            roadmap_steps.append({
                "step_number": len(roadmap_steps) + 1,
                "skill": skill,
                "status": status,
                "difficulty": item["difficulty"],
                "prerequisites": prereqs,
                "resources": item["resources"],
                "is_revision": False
            })

            if skill in revision_skills:
                roadmap_steps.append({
                    "step_number": len(roadmap_steps) + 1,
                    "skill": skill,
                    "status": "in_progress",
                    "difficulty": item["difficulty"],
                    "prerequisites": prereqs,
                    "resources": item["resources"],
                    "is_revision": True
                })

        log_message = f"{self.name}: structured {len(roadmap_steps)} sequential learning steps for {target_role}"

        return {
            "roadmap": roadmap_steps,
            "total_steps": len(roadmap_steps),
            "log_message": log_message
        }
