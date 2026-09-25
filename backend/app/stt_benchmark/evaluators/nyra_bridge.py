"""Isolated bridge for a Nyra benchmark source checkout.

This module is invoked in a child process because the upstream repository is
not a Python distribution and imports sibling modules by their top-level names.
"""

import importlib.util
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        return 2
    checkout = Path(argv[1]).resolve()
    input_path = Path(argv[2]).resolve()
    output_path = Path(argv[3]).resolve()
    evaluate_path = checkout / "evaluate.py"
    sys.path.insert(0, str(checkout))
    specification = importlib.util.spec_from_file_location("nyra_benchmark_evaluate", evaluate_path)
    if specification is None or specification.loader is None:
        return 3
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    gold = module.preprocess_gold(
        payload["gold_verbatim"],
        payload["gold_intended"],
        payload["sample_id"],
        language=payload["language"],
    )
    result = module.evaluate_sample(
        gold,
        payload["prediction_verbatim"],
        payload.get("prediction_intended"),
    )
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
