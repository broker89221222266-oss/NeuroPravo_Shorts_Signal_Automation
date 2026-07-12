from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = ROOT / "output" / "_smoke_tests"
REQUIRED_OUTPUTS = (
    "discovery_manifest.md",
    "scenario_cards.md",
    "scenario_cards.csv",
    "scenario_cards.json",
    "batch_summary.md",
    "source_candidates_review.md",
    "validation_report.csv",
)


@dataclass(frozen=True)
class SmokeCase:
    name: str
    input_path: str
    min_score: int
    metrics_mode: str
    min_selected: int
    expected_rows_hint: str


CASES = (
    SmokeCase("main_input", "data/input_videos.csv", 70, "normal", 1, "about 4"),
    SmokeCase("youtube_demo", "data/demos/youtube_shorts_demo.csv", 70, "normal", 1, "about 3"),
    SmokeCase("tiktok_demo", "data/demos/tiktok_apify_demo.csv", 70, "normal", 1, "about 3"),
    SmokeCase("mixed_demo", "data/demos/mixed_manual_import_demo.csv", 70, "normal", 1, "about 4"),
    SmokeCase("first_public_batch", "data/manual_batches/batch_2026-07-12.csv", 55, "public_search", 1, "about 24"),
)


class SmokeFailure(RuntimeError):
    pass


def parse_selected(stdout: str) -> tuple[int, int]:
    match = re.search(r"Selected videos:\s*(\d+)\s*of\s*(\d+)", stdout)
    if not match:
        raise SmokeFailure("Could not parse selected count from generator output.")
    return int(match.group(1)), int(match.group(2))


def parse_validation_issues(stdout: str) -> int:
    match = re.search(r"Validation issues:\s*(\d+)", stdout)
    if not match:
        raise SmokeFailure("Could not parse validation issue count from generator output.")
    return int(match.group(1))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_outputs(case: SmokeCase, out_dir: Path, stdout: str) -> tuple[int, int]:
    for filename in REQUIRED_OUTPUTS:
        output_path = out_dir / filename
        if not output_path.exists():
            raise SmokeFailure(f"{case.name}: missing output {filename}")
        if output_path.stat().st_size <= 0:
            raise SmokeFailure(f"{case.name}: empty output {filename}")

    selected_count, total_count = parse_selected(stdout)
    validation_issues = parse_validation_issues(stdout)

    if validation_issues != 0:
        raise SmokeFailure(f"{case.name}: expected 0 validation issues, got {validation_issues}")
    if selected_count < case.min_selected:
        raise SmokeFailure(f"{case.name}: expected selected >= {case.min_selected}, got {selected_count}")
    if total_count <= 0:
        raise SmokeFailure(f"{case.name}: expected rows > 0")

    cards_json = json.loads((out_dir / "scenario_cards.json").read_text(encoding="utf-8"))
    if len(cards_json.get("cards", [])) != total_count:
        raise SmokeFailure(f"{case.name}: JSON card count does not match generator output")

    csv_rows = read_csv_rows(out_dir / "scenario_cards.csv")
    if len(csv_rows) != total_count:
        raise SmokeFailure(f"{case.name}: CSV row count does not match generator output")

    summary = (out_dir / "batch_summary.md").read_text(encoding="utf-8")
    manifest = (out_dir / "discovery_manifest.md").read_text(encoding="utf-8")
    source_review = (out_dir / "source_candidates_review.md").read_text(encoding="utf-8")
    if "Discovery Manifest" not in manifest:
        raise SmokeFailure(f"{case.name}: discovery_manifest.md does not look valid")
    if "SOURCE-REVIEW-READY" not in manifest and "NEEDS-BETTER-SOURCE-BATCH" not in manifest:
        raise SmokeFailure(f"{case.name}: discovery manifest missing gate status")
    if "Source Candidates Review" not in source_review:
        raise SmokeFailure(f"{case.name}: source_candidates_review.md does not look valid")
    if "ЗАЛЕТЕВШИЙ-КАНДИДАТ" not in source_review and "ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ" not in source_review:
        raise SmokeFailure(f"{case.name}: source review missing candidate statuses")

    if "Batch Summary" not in summary:
        raise SmokeFailure(f"{case.name}: batch_summary.md does not look valid")
    if case.metrics_mode == "public_search" and "Data quality / Metrics completeness" not in summary:
        raise SmokeFailure(f"{case.name}: public_search summary missing data quality block")

    return selected_count, total_count


def run_case(case: SmokeCase) -> tuple[int, int]:
    out_dir = SMOKE_ROOT / case.name
    if out_dir.exists():
        shutil.rmtree(out_dir)

    command = [
        sys.executable,
        str(ROOT / "scripts" / "generate_cards.py"),
        "--input",
        case.input_path,
        "--out",
        str(out_dir),
        "--min-score",
        str(case.min_score),
        "--metrics-mode",
        case.metrics_mode,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise SmokeFailure(
            f"{case.name}: generator failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return validate_outputs(case, out_dir, result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local smoke tests for NeuroPravo Shorts generator.")
    parser.add_argument("--keep-output", action="store_true", help="Keep output/_smoke_tests for manual inspection.")
    args = parser.parse_args()

    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)

    print("Smoke tests: local generator only. No deploy, no render, no API.")
    try:
        for case in CASES:
            selected, total = run_case(case)
            print(
                f"OK {case.name}: mode={case.metrics_mode}, min_score={case.min_score}, "
                f"selected={selected}/{total}, expected_rows={case.expected_rows_hint}"
            )
    finally:
        if not args.keep_output and SMOKE_ROOT.exists():
            shutil.rmtree(SMOKE_ROOT)

    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
