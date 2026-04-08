#!/usr/bin/env python3
"""Validate FR requirements-to-implementation traceability matrix."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_PATH = REPO_ROOT / "docs/system-design/requirements/requirements.md"
TRACEABILITY_PATH = REPO_ROOT / "docs/system-design/implementation/requirements-traceability.md"

FR_PATTERN = re.compile(r"\b(FR-[A-Z]{2}-\d{3})\b")
MATRIX_ROW_PATTERN = re.compile(r"^\|\s*(FR-[A-Z]{2}-\d{3})\s*\|")
STATUS_VALUES = {"complete", "partial", "missing"}
ISSUE_REFERENCE_PATTERN = re.compile(r"(#\d+|issues?/\d+)", re.IGNORECASE)


def parse_requirement_ids() -> list[str]:
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    return FR_PATTERN.findall(text)


def parse_matrix_rows() -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for raw_line in TRACEABILITY_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not MATRIX_ROW_PATTERN.match(line):
            continue
        columns = [part.strip() for part in line.strip("|").split("|")]
        if len(columns) != 6:
            raise ValueError(f"Invalid matrix row (expected 6 columns): {raw_line}")
        rows.append((columns[0], columns))
    return rows


def main() -> int:
    errors: list[str] = []

    if not REQUIREMENTS_PATH.exists():
        print(f"Missing requirements file: {REQUIREMENTS_PATH}")
        return 1

    if not TRACEABILITY_PATH.exists():
        print(f"Missing traceability file: {TRACEABILITY_PATH}")
        return 1

    requirement_ids = parse_requirement_ids()
    matrix_rows = parse_matrix_rows()

    matrix_ids = [item[0] for item in matrix_rows]

    for requirement_id in requirement_ids:
        count = matrix_ids.count(requirement_id)
        if count == 0:
            errors.append(f"Requirement {requirement_id} is missing from the traceability matrix")
        elif count > 1:
            errors.append(
                f"Requirement {requirement_id} appears {count} times in the traceability matrix"
            )

    for matrix_id in sorted(set(matrix_ids) - set(requirement_ids)):
        errors.append(f"Unexpected requirement ID in matrix: {matrix_id}")

    if len(matrix_rows) != len(requirement_ids):
        errors.append(
            "Matrix row count does not match requirements count "
            f"({len(matrix_rows)} != {len(requirement_ids)})"
        )

    for requirement_id, columns in matrix_rows:
        status = columns[4].strip().lower()
        edge_cases = columns[5]

        if status not in STATUS_VALUES:
            errors.append(
                f"Requirement {requirement_id} has invalid status '{columns[4]}'; "
                f"expected one of {sorted(STATUS_VALUES)}"
            )

        if status == "missing" and not ISSUE_REFERENCE_PATTERN.search(edge_cases):
            errors.append(
                f"Requirement {requirement_id} is marked missing without an open issue reference"
            )

    if errors:
        print("Requirements traceability validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Requirements traceability validation passed "
        f"({len(requirement_ids)} requirements, {len(matrix_rows)} matrix rows)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
