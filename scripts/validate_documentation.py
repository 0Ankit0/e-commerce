#!/usr/bin/env python3
"""Validate the canonical documentation tree used by this repository."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
SYSTEM_DESIGN_ROOT = DOCS_ROOT / "system-design"

REQUIRED_ROOT_DOCS = {
    "docs/README.md": [
        "# Project Documentation",
        "## Canonical Structure",
        "## Runtime Guides",
        "## Validation",
    ],
    "docs/system-design/README.md": [
        "# E-Commerce System Design Documentation",
        "## Documentation Structure",
        "## Current Backend Docs",
        "## Diagram Generation",
    ],
    "backend/README.md": ["#"],
    "frontend/README.md": ["# Frontend Runtime Guide"],
    "mobile/README.md": ["# Mobile Runtime Guide"],
}

REQUIRED_SYSTEM_DESIGN_FILES = {
    "requirements": ["requirements.md", "user-stories.md"],
    "analysis": [
        "activity-diagrams.md",
        "swimlane-diagrams.md",
        "system-context-diagram.md",
        "use-case-descriptions.md",
        "use-case-diagram.md",
    ],
    "high-level-design": [
        "architecture-diagram.md",
        "c4-diagrams.md",
        "data-flow-diagrams.md",
        "domain-model.md",
        "system-sequence-diagrams.md",
    ],
    "detailed-design": [
        "api-design.md",
        "c4-component-diagram.md",
        "class-diagrams.md",
        "component-diagrams.md",
        "erd-database-schema.md",
        "recommendation-engine.md",
        "sequence-diagrams.md",
        "state-machine-diagrams.md",
    ],
    "infrastructure": [
        "cloud-architecture.md",
        "deployment-diagram.md",
        "network-infrastructure.md",
    ],
    "implementation": [
        "backend-status-matrix.md",
        "c4-code-diagram.md",
        "implementation-guidelines.md",
    ],
}


def is_empty(path: Path) -> bool:
    return not path.exists() or not path.read_text(encoding="utf-8").strip()


def validate_headings(path: Path, required_headings: list[str], errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for heading in required_headings:
        if heading not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing heading/text: {heading}")


def main() -> int:
    errors: list[str] = []

    for relative_path, headings in REQUIRED_ROOT_DOCS.items():
        path = REPO_ROOT / relative_path
        if is_empty(path):
            errors.append(f"Missing or empty file: {relative_path}")
            continue
        validate_headings(path, headings, errors)

    for directory, filenames in REQUIRED_SYSTEM_DESIGN_FILES.items():
        dir_path = SYSTEM_DESIGN_ROOT / directory
        if not dir_path.exists():
            errors.append(f"Missing directory: docs/system-design/{directory}")
            continue

        for filename in filenames:
            path = dir_path / filename
            if is_empty(path):
                errors.append(f"Missing or empty file: docs/system-design/{directory}/{filename}")
                continue

            if "diagram" in filename or filename.startswith("c4-"):
                text = path.read_text(encoding="utf-8")
                if "```mermaid" not in text:
                    errors.append(f"Diagram file missing Mermaid content: docs/system-design/{directory}/{filename}")

    if errors:
        print("Documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
