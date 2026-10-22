#!/usr/bin/env python3
"""Validate the minimal youtube-production plugin package."""

import ast
import json
import sys
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
ROOT = PLUGIN.parents[1]
EXPECTED_SKILL = PLUGIN / "skills" / "youtube" / "SKILL.md"
ANALYZE_STDLIB = {"__future__", "argparse", "csv", "json", "math", "pathlib", "statistics", "sys"}
FILES = [
    ROOT / ".claude-plugin" / "marketplace.json",
    PLUGIN / ".claude-plugin" / "plugin.json",
    EXPECTED_SKILL,
    PLUGIN / "scripts" / "analyze.py",
    Path(__file__).resolve(),
    PLUGIN / "README.md",
]


def load_json(path, errors):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return {}


def frontmatter(text):
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    block = text.split("\n---\n", 1)[0].splitlines()[1:]
    result = {}
    for line in block:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def validate_stdlib(path, errors):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [item.name.split(".")[0] for item in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            if name not in ANALYZE_STDLIB:
                errors.append(f"analyze.py imports non-stdlib module: {name}")


def main():
    errors = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing required file: {path}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    marketplace = load_json(FILES[0], errors)
    manifest = load_json(FILES[1], errors)
    plugins = marketplace.get("plugins", [])
    if marketplace.get("name") != "youtube-production" or len(plugins) != 1:
        errors.append("marketplace must contain exactly the youtube-production plugin")
    elif plugins[0].get("name") != "youtube-production" or plugins[0].get("source") != "./plugins/youtube-production":
        errors.append("marketplace plugin name/source is invalid")
    if manifest.get("name") != "youtube-production" or manifest.get("version") != "0.1.0":
        errors.append("plugin manifest must identify youtube-production v0.1.0")

    skills = list((PLUGIN / "skills").glob("*/SKILL.md"))
    if skills != [EXPECTED_SKILL]:
        errors.append("package must contain exactly skills/youtube/SKILL.md")
    skill_text = EXPECTED_SKILL.read_text(encoding="utf-8")
    metadata = frontmatter(skill_text)
    if metadata.get("name") != "youtube" or not metadata.get("description"):
        errors.append("skill frontmatter requires name youtube and a description")
    for phrase in ("plan", "production handoff", "review", "${CLAUDE_PLUGIN_ROOT}", "SKILL.md"):
        if phrase.lower() not in skill_text.lower():
            errors.append(f"skill is missing required portable workflow text: {phrase}")

    validate_stdlib(PLUGIN / "scripts" / "analyze.py", errors)
    total_lines = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in FILES)
    if total_lines >= 700:
        errors.append(f"distributable is {total_lines} lines; expected fewer than 700")

    if errors:
        print("plugin validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"youtube-production v0.1.0 valid: one skill, stdlib analysis, {total_lines} distributable lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
