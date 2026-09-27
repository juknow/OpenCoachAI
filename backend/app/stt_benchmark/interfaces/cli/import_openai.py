"""Import already-saved OpenAI transcription JSON; never invoke the API."""

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.openai_response_import import import_openai_responses


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import saved OpenAI JSON as STT predictions.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--response", action="append", required=True, metavar="SAMPLE_ID=PATH")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--prompt-sha256", action="append", default=[], metavar="SAMPLE_ID=SHA256")
    return parser


def _sample_mapping(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        sample_id, separator, item = value.partition("=")
        if not separator or not sample_id or not item or sample_id in mapping:
            raise ValueError("expected unique SAMPLE_ID=VALUE entries")
        mapping[sample_id] = item
    return mapping


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    manifest_path = arguments.manifest.resolve()
    results_dir = (manifest_path.parent / "results").resolve()
    output = arguments.output.resolve()
    if not output.is_relative_to(results_dir) or output.suffix.lower() != ".json":
        parser.error("--output must be JSON under the manifest's private results directory")
    if output.exists():
        parser.error("--output already exists; choose a new run path")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", arguments.model) is None:
        parser.error("--model must be a lowercase OpenAI model ID")

    try:
        responses = {key: Path(value) for key, value in _sample_mapping(arguments.response).items()}
        prompt_hashes = _sample_mapping(arguments.prompt_sha256)
        dataset = TranscriptionDataset.model_validate_json(
            manifest_path.read_text(encoding="utf-8-sig")
        )
        run = import_openai_responses(
            dataset=dataset,
            results_dir=results_dir,
            responses=responses,
            experiment_id=arguments.experiment_id,
            model=arguments.model,
            prompt_version=arguments.prompt_version,
            prompt_hashes=prompt_hashes,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(run.model_dump_json(by_alias=True, indent=2) + "\n")
    except (OSError, UnicodeError, ValueError, ValidationError):
        parser.error("import failed; inspect private inputs, schema and output path locally")

    print(f"Imported {len(run.observations)} saved predictions to {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
