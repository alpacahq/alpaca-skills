#!/usr/bin/env python3
"""Validate alpaca-skills layout, frontmatter, and basic secret heuristics."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
NAME_PATTERN = re.compile(r"^alpaca-(trading|broker)-[a-z0-9-]+$")

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "secret-alpaca-key",
        re.compile(r"ALPACA_SECRET_KEY\s*=\s*[^.\s]{8,}"),
    ),
    (
        "secret-sk-prefix",
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    ),
    (
        "secret-pk-prefix",
        re.compile(r"PK[A-Z0-9]{18,}"),
    ),
]

PLACEHOLDER_MARKERS = (
    "placeholder",
    "your-secret",
    "your_secret",
    "example",
    "xxx",
    "redacted",
    "<secret",
    "changeme",
)


class ValidationError(Exception):
    def __init__(self, rule: str, path: Path, message: str) -> None:
        self.rule = rule
        self.path = path
        self.message = message
        super().__init__(f"{path}: [{rule}] {message}")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if current_key is not None:
                fields[current_key] += "\n" + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        fields[current_key] = value.strip()
    return fields


def is_skill_dir(path: Path) -> bool:
    return (path / "SKILL.md").is_file()


def find_skill_md_files() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.rglob("SKILL.md"))


def validate_skill_layout(skill_md: Path) -> None:
    rel = skill_md.relative_to(ROOT)
    parts = rel.parts
    if len(parts) != 4 or parts[0] != "skills" or parts[3] != "SKILL.md":
        raise ValidationError(
            "skill-layout",
            skill_md,
            "SKILL.md must live at skills/<product>/<skill-name>/SKILL.md",
        )


def validate_no_top_level_skills() -> None:
    top_level = SKILLS_DIR / "SKILL.md"
    if top_level.is_file():
        raise ValidationError(
            "no-top-level-skills",
            top_level,
            "SKILL.md must not exist directly under skills/",
        )


def validate_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    if "name" not in fields or not fields["name"].strip():
        raise ValidationError("frontmatter-name", skill_md, "missing name in frontmatter")
    if "description" not in fields or not fields["description"].strip():
        raise ValidationError(
            "frontmatter-description",
            skill_md,
            "missing description in frontmatter",
        )
    return fields


def validate_name(skill_md: Path, name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise ValidationError(
            "name-pattern",
            skill_md,
            f"name '{name}' must match alpaca-(trading|broker)-<skill-name>",
        )


def is_placeholder_context(text: str, match_start: int) -> bool:
    window_start = max(0, match_start - 80)
    window_end = min(len(text), match_start + 80)
    window = text[window_start:window_end].lower()
    return any(marker in window for marker in PLACEHOLDER_MARKERS)


def scan_secrets(path: Path) -> None:
    rel = path.relative_to(ROOT)
    rel_str = rel.as_posix()
    if rel_str.startswith("templates/"):
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    for rule, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            if is_placeholder_context(text, match.start()):
                continue
            raise ValidationError(
                rule,
                path,
                f"suspicious secret-like content: {match.group()[:24]}...",
            )


def scan_secret_directories() -> None:
    for subdir in ("skills", "scripts"):
        base = ROOT / subdir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix in {".pyc"}:
                continue
            scan_secrets(path)


def validate_skills() -> list[str]:
    errors: list[str] = []
    validate_no_top_level_skills()

    skill_files = find_skill_md_files()
    for skill_md in skill_files:
        try:
            validate_skill_layout(skill_md)
            fields = validate_frontmatter(skill_md)
            validate_name(skill_md, fields["name"])
        except ValidationError as exc:
            errors.append(str(exc))

    try:
        scan_secret_directories()
    except ValidationError as exc:
        errors.append(str(exc))

    return errors


def main() -> int:
    errors = validate_skills()
    if errors:
        print("validate_skills.py failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("validate_skills.py: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
