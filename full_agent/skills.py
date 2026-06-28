import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    triggers: List[str]
    instructions_path: Path


class SkillLoader:
    def __init__(self, skills_dir):
        self.skills_dir = Path(skills_dir)

    def discover(self):
        if not self.skills_dir.exists():
            return []

        skills = []
        for child in sorted(self.skills_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "skill.json"
            if not manifest_path.exists():
                continue
            skills.append(self._load_manifest(manifest_path))
        return skills

    def select(self, task):
        task_lower = (task or "").lower()
        selected = []
        for skill in self.discover():
            triggers = [trigger.lower() for trigger in skill.triggers]
            if skill.name.lower() in task_lower or any(trigger in task_lower for trigger in triggers):
                selected.append(skill)
        return selected

    def load_instructions(self, selected_skills):
        chunks = []
        for skill in selected_skills:
            if not skill.instructions_path.exists():
                raise ValueError(
                    "Skill instructions not found for {0}: {1}".format(
                        skill.name, skill.instructions_path
                    )
                )
            content = skill.instructions_path.read_text(encoding="utf-8")
            chunks.append(
                "## Skill: {0}\nDescription: {1}\n\n{2}".format(
                    skill.name, skill.description, content
                )
            )
        return "\n\n".join(chunks)

    def _load_manifest(self, manifest_path):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            name = self._require_string(data, "name", manifest_path)
            description = self._require_string(data, "description", manifest_path)
            instructions = self._require_string(data, "instructions", manifest_path)
            triggers = data.get("triggers", [])
            if not isinstance(triggers, list) or not all(
                isinstance(trigger, str) for trigger in triggers
            ):
                raise ValueError("triggers must be a list of strings")
        except json.JSONDecodeError as e:
            raise ValueError(
                "Invalid skill manifest {0}: {1}".format(manifest_path, e)
            )
        except ValueError as e:
            raise ValueError("Invalid skill manifest {0}: {1}".format(manifest_path, e))

        return AgentSkill(
            name=name,
            description=description,
            triggers=triggers,
            instructions_path=(manifest_path.parent / instructions),
        )

    def _require_string(self, data, key, manifest_path):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("{0} must be a non-empty string".format(key))
        return value
