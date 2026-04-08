from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI schema to a JSON file.")
    parser.add_argument(
        "--output",
        default="../frontend/contracts/openapi.snapshot.json",
        help="Path to the output file (default: ../frontend/contracts/openapi.snapshot.json)",
    )
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI schema to {output}")


if __name__ == "__main__":
    main()
