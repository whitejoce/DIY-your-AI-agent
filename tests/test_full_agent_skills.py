import json

from full_agent.skills import SkillLoader


def write_skill(root, name="pytest-helper", trigger="pytest", instructions="SKILL.md"):
    skill_dir = root / name
    skill_dir.mkdir()
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "name": name,
                "description": "Help with tests",
                "triggers": [trigger],
                "instructions": instructions,
            }
        ),
        encoding="utf-8",
    )
    (skill_dir / instructions).write_text("Run focused tests first.", encoding="utf-8")
    return skill_dir


def test_skill_loader_discovers_manifest(tmp_path):
    write_skill(tmp_path)

    skills = SkillLoader(tmp_path).discover()

    assert len(skills) == 1
    assert skills[0].name == "pytest-helper"
    assert skills[0].triggers == ["pytest"]


def test_skill_loader_selects_by_trigger_and_loads_only_selected_instructions(tmp_path):
    write_skill(tmp_path, name="pytest-helper", trigger="pytest")
    write_skill(tmp_path, name="docs-helper", trigger="readme")
    loader = SkillLoader(tmp_path)

    selected = loader.select("please fix pytest failure")
    instructions = loader.load_instructions(selected)

    assert [skill.name for skill in selected] == ["pytest-helper"]
    assert "Run focused tests first." in instructions
    assert "docs-helper" not in instructions


def test_skill_loader_reports_bad_manifest(tmp_path):
    skill_dir = tmp_path / "bad"
    skill_dir.mkdir()
    (skill_dir / "skill.json").write_text("{bad json", encoding="utf-8")

    try:
        SkillLoader(tmp_path).discover()
    except ValueError as e:
        assert "Invalid skill manifest" in str(e)
        assert "skill.json" in str(e)
    else:
        raise AssertionError("expected bad manifest to fail clearly")
