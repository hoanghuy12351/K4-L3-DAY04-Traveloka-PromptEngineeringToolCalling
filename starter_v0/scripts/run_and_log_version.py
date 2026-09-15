from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = ROOT / "artifacts" / "version_log.csv"
DEFAULT_EVAL_CASES = ROOT / "data" / "eval_travel_base.json"
DEFAULT_RUNS_DIR = ROOT / "runs"
CSV_FIELDS = [
    "version",
    "author",
    "changed_artifact",
    "artifact_version",
    "prompt_hash",
    "tools_hash",
    "reason",
    "hypothesis",
    "metric_name",
    "metric_before",
    "metric_after",
    "run_file",
]


def resolve_from_root(path_value: str) -> Path:
    """Resolve CLI paths from either the repository root or starter_v0."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    repository_candidate = (Path.cwd() / path).resolve()
    if repository_candidate.exists():
        return repository_candidate
    return (ROOT / path).resolve()


def previous_version(version: str) -> str:
    """Map a sequential version label such as v2 to its direct predecessor."""
    match = re.fullmatch(r"v([1-9][0-9]*)", version)
    if not match:
        raise ValueError("version must use a sequential label such as v2 or v3.")
    number = int(match.group(1))
    if number < 2:
        raise ValueError("version must have a previous version; use v2 or later.")
    return f"v{number - 1}"


def read_log(path: Path) -> list[dict[str, str]]:
    """Read the version log without changing its existing rows."""
    if not path.exists():
        raise FileNotFoundError(f"Version log does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def find_previous_run(
    *, previous: str, log_rows: list[dict[str, str]], runs_dir: Path
) -> Path:
    """Prefer an existing logged run, then fall back to the newest matching run."""
    for row in reversed(log_rows):
        if row.get("version") != previous or not row.get("run_file"):
            continue
        run_path = ROOT / row["run_file"]
        if run_path.exists():
            return run_path

    candidates = sorted(
        runs_dir.glob(f"{previous}_B_base_openai_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No {previous} OpenAI base run exists in {runs_dir}.")
    return candidates[0]


def load_run(path: Path) -> dict[str, Any]:
    """Load one evaluator-generated run file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_run(run: dict[str, Any], *, expected_provider: str) -> None:
    """Reject incomplete or provider-error runs before they enter the version log."""
    summary = run.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Run has no summary.")
    failures: list[str] = []
    if run.get("provider") != expected_provider:
        failures.append(f"provider={run.get('provider')!r}, expected {expected_provider!r}")
    if summary.get("provider_error_cases") != 0:
        failures.append(f"provider_error_cases={summary.get('provider_error_cases')!r}, expected 0")
    if summary.get("measured_cases") != summary.get("total_cases"):
        failures.append(
            f"measured_cases={summary.get('measured_cases')!r}, total_cases={summary.get('total_cases')!r}"
        )
    if summary.get("total_cases") != 30:
        failures.append(f"total_cases={summary.get('total_cases')!r}, expected 30")
    if failures:
        raise ValueError("Invalid evaluation run: " + "; ".join(failures))


def relative_run_path(path: Path) -> str:
    """Return the repository-relative run location used by version_log.csv."""
    return path.resolve().relative_to(ROOT).as_posix()


def append_log_row(path: Path, row: dict[str, str], existing_rows: list[dict[str, str]]) -> None:
    """Append one unique run row while preserving the established CSV schema."""
    duplicate = any(
        item.get("version") == row["version"] and item.get("run_file") == row["run_file"]
        for item in existing_rows
    )
    if duplicate:
        raise ValueError("This version and run_file pair already exists in version_log.csv.")
    conflicting_version = [item for item in existing_rows if item.get("version") == row["version"]]
    if conflicting_version:
        raise ValueError(
            f"version_log.csv already contains version {row['version']}; refusing to append another iteration silently."
        )
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Travel Planner evaluation and append a validated version log row.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--provider", required=True, choices=["openai", "openrouter", "anthropic", "gemini"])
    parser.add_argument("--reason", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--changed-artifact", required=True)
    parser.add_argument("--metric-name", default="case_accuracy")
    parser.add_argument("--eval-cases", default=str(DEFAULT_EVAL_CASES))
    parser.add_argument("--version-log", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    args = parser.parse_args()

    if args.provider != "openai":
        raise SystemExit("This version-comparison helper requires --provider openai.")
    try:
        previous = previous_version(args.version)
        log_path = resolve_from_root(args.version_log)
        runs_dir = resolve_from_root(args.runs_dir)
        eval_cases = resolve_from_root(args.eval_cases)
        log_rows = read_log(log_path)
        previous_run_path = find_previous_run(previous=previous, log_rows=log_rows, runs_dir=runs_dir)
        previous_run = load_run(previous_run_path)
        validate_run(previous_run, expected_provider=args.provider)
        metric_before = previous_run["summary"].get(args.metric_name)
        if not isinstance(metric_before, (int, float)):
            raise ValueError(f"Previous run has no numeric {args.metric_name!r} metric.")

        before_files = {path.resolve() for path in runs_dir.glob(f"{args.version}_B_base_{args.provider}_*.json")}
        command = [
            sys.executable,
            str(ROOT / "run_eval.py"),
            "--provider",
            args.provider,
            "--version",
            args.version,
            "--suite",
            "base",
            "--eval-cases",
            str(eval_cases),
            "--runs-dir",
            str(runs_dir),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"run_eval.py exited with code {completed.returncode}.")

        new_files = [
            path for path in runs_dir.glob(f"{args.version}_B_base_{args.provider}_*.json")
            if path.resolve() not in before_files
        ]
        if not new_files:
            raise FileNotFoundError("Evaluation finished without creating a new versioned run file.")
        current_run_path = max(new_files, key=lambda path: path.stat().st_mtime)
        current_run = load_run(current_run_path)
        validate_run(current_run, expected_provider=args.provider)
        metric_after = current_run["summary"].get(args.metric_name)
        if not isinstance(metric_after, (int, float)):
            raise ValueError(f"Current run has no numeric {args.metric_name!r} metric.")

        row = {
            "version": args.version,
            "author": "hoanghuy12351",
            "changed_artifact": args.changed_artifact,
            "artifact_version": str(current_run.get("artifact_version", "")),
            "prompt_hash": str(current_run.get("prompt_hash", "")),
            "tools_hash": str(current_run.get("tools_hash", "")),
            "reason": args.reason,
            "hypothesis": args.hypothesis,
            "metric_name": args.metric_name,
            "metric_before": str(metric_before),
            "metric_after": str(metric_after),
            "run_file": relative_run_path(current_run_path),
        }
        append_log_row(log_path, row, log_rows)
        print("Logged validated run:")
        print(json.dumps(row, ensure_ascii=False))
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
