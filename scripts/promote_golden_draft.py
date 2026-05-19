#!/usr/bin/env python3
"""Strip _bootstrap metadata from golden_dataset.draft.json for promotion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DRAFT = REPO_ROOT / "backend/tests/eval/golden_dataset.draft.json"
DEFAULT_OUT = REPO_ROOT / "backend/tests/eval/golden_dataset.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = json.loads(args.draft.read_text(encoding="utf-8"))
    clean = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
    args.output.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(clean)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
