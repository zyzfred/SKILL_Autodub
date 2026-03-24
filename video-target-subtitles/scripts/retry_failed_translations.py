#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
STAGE_ORDER = [
    "audio",
    "asr",
    "rebalance",
    "semantic_repair",
    "translation",
    "timing_polish",
    "export_srt",
    "export_vtt",
    "lint_srt",
    "lint_vtt",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Retry failed batch subtitle runs from the translation stage or another selected stage.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing per-file run summaries (default: output)",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Optional batch summary JSON to use instead of scanning output-dir",
    )
    parser.add_argument(
        "--input-dir",
        default="",
        help="Optional input directory override. Defaults to the parent directories from the run summaries.",
    )
    parser.add_argument(
        "--target-language",
        default="English",
        help="Target subtitle language (default: English)",
    )
    parser.add_argument(
        "--target-locale",
        default="en-US",
        help="Target locale hint (default: en-US)",
    )
    parser.add_argument(
        "--target-code",
        default="en",
        help="Target code used in filenames (default: en)",
    )
    parser.add_argument(
        "--source-language",
        default="zh",
        help="Source language hint (default: zh)",
    )
    parser.add_argument(
        "--asr-language-hint",
        default="zh",
        help="FunASR language hint (default: zh)",
    )
    parser.add_argument(
        "--translation-batch-size",
        type=int,
        default=5,
        help="Subtitle cues per translation request (default: 5)",
    )
    parser.add_argument(
        "--command-timeout",
        type=int,
        default=900,
        help="Timeout in seconds for each stage command (default: 900)",
    )
    parser.add_argument(
        "--start-at",
        default="translation",
        choices=STAGE_ORDER,
        help="Stage to restart from (default: translation)",
    )
    parser.add_argument(
        "--include-stems",
        default="",
        help="Optional comma-separated stem filter",
    )
    parser.add_argument(
        "--only-failed-stage",
        default="",
        choices=[""] + STAGE_ORDER,
        help="Only retry videos whose recorded failed stage matches this value",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip stages whose outputs already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the retry plan without running the batch script",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_run_summaries(output_dir, summary_path):
    if summary_path:
        payload = load_json(Path(summary_path).expanduser().resolve())
        paths = [item.get("summary_path") for item in payload.get("videos") or [] if item.get("summary_path")]
        return [load_json(Path(path)) for path in paths]
    return [
        load_json(path)
        for path in sorted(Path(output_dir).expanduser().resolve().glob("*.run-summary.json"))
    ]


def collect_retry_targets(summaries, include_stems, only_failed_stage):
    allowed = {item.strip() for item in include_stems.split(",") if item.strip()}
    targets = []
    input_dirs = set()
    for summary in summaries:
        if summary.get("status") == "ok":
            continue
        stem = Path(summary.get("input", "")).stem
        if allowed and stem not in allowed:
            continue
        if only_failed_stage and summary.get("failed_stage") != only_failed_stage:
            continue
        if summary.get("input"):
            input_dirs.add(str(Path(summary["input"]).expanduser().resolve().parent))
        targets.append(
            {
                "stem": stem,
                "failed_stage": summary.get("failed_stage"),
                "error": summary.get("error"),
            }
        )
    return targets, sorted(input_dirs)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    summaries = load_run_summaries(output_dir, args.summary_path)
    retry_targets, input_dirs = collect_retry_targets(
        summaries,
        include_stems=args.include_stems,
        only_failed_stage=args.only_failed_stage,
    )

    if not retry_targets:
        print(json.dumps({"retry_stems": [], "count": 0}, ensure_ascii=False, indent=2))
        return 0

    if args.input_dir:
        input_dir = Path(args.input_dir).expanduser().resolve()
    elif len(input_dirs) == 1:
        input_dir = Path(input_dirs[0])
    else:
        raise SystemExit(
            "Could not infer a single input directory from the failed summaries. Pass --input-dir explicitly."
        )

    payload = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "start_at": args.start_at,
        "retry_stems": [item["stem"] for item in retry_targets],
        "targets": retry_targets,
    }
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    command = [
        sys.executable,
        str(SCRIPT_DIR / "batch_generate_subtitles.py"),
        "--input-dir",
        str(input_dir),
        "--output-dir",
        str(output_dir),
        "--target-language",
        args.target_language,
        "--target-locale",
        args.target_locale,
        "--target-code",
        args.target_code,
        "--source-language",
        args.source_language,
        "--asr-language-hint",
        args.asr_language_hint,
        "--translation-batch-size",
        str(args.translation_batch_size),
        "--command-timeout",
        str(args.command_timeout),
        "--start-at",
        args.start_at,
        "--include-stems",
        ",".join(item["stem"] for item in retry_targets),
    ]
    if args.skip_existing:
        command.append("--skip-existing")

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Retry batch failed"
        raise SystemExit(message)

    print(
        json.dumps(
            {
                "retried": len(retry_targets),
                "retry_stems": [item["stem"] for item in retry_targets],
                "batch_result": json.loads(result.stdout),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
