#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from env_loader import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
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

load_dotenv(extra_roots=[Path.cwd(), SCRIPT_DIR])


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(text):
    value = "".join(char.lower() if char.isalnum() else "-" for char in text.strip())
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-") or "target"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate subtitles for every supported video in a folder while keeping per-file run summaries.",
    )
    parser.add_argument(
        "--input-dir",
        default="data",
        help="Directory containing source videos (default: data)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated subtitle outputs (default: output)",
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
        help="Target code used in filenames. If empty, it is derived from target language.",
    )
    parser.add_argument(
        "--source-language",
        default="zh",
        help="Source language hint for semantic repair and translation (default: zh)",
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
        "--include-stems",
        default="",
        help="Comma-separated stems to process, for example 真人,精品3D",
    )
    parser.add_argument(
        "--start-at",
        default="audio",
        choices=STAGE_ORDER,
        help="Start processing at this stage (default: audio)",
    )
    parser.add_argument(
        "--stop-after",
        default="",
        choices=[""] + STAGE_ORDER,
        help="Optional last stage to execute",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip stages whose outputs already exist or whose lint result is already recorded",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the batch immediately when one video fails",
    )
    return parser.parse_args()


def run_json_command(command, timeout):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        raise RuntimeError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON output: {exc}") from exc


def collect_videos(input_dir, include_stems):
    allowed = {item.strip() for item in include_stems.split(",") if item.strip()}
    videos = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if allowed and path.stem not in allowed:
            continue
        videos.append(path)
    return videos


def output_paths(output_dir, stem, target_code):
    work_dir = output_dir / f"{stem}.work"
    return {
        "work_dir": work_dir,
        "audio": work_dir / f"{stem}.funasr.wav",
        "source_segments": work_dir / f"{stem}.source.segments.json",
        "rebalanced_segments": work_dir / f"{stem}.source.rebalanced.segments.json",
        "semantic_segments": work_dir / f"{stem}.source.semantic.segments.json",
        "translated_segments": work_dir / f"{stem}.{target_code}.translated.segments.json",
        "polished_segments": work_dir / f"{stem}.{target_code}.segments.json",
        "srt": output_dir / f"{stem}.{target_code}.srt",
        "vtt": output_dir / f"{stem}.{target_code}.vtt",
        "summary": output_dir / f"{stem}.run-summary.json",
    }


def stage_output_path(stage_name, paths):
    return {
        "audio": paths["audio"],
        "asr": paths["source_segments"],
        "rebalance": paths["rebalanced_segments"],
        "semantic_repair": paths["semantic_segments"],
        "translation": paths["translated_segments"],
        "timing_polish": paths["polished_segments"],
        "export_srt": paths["srt"],
        "export_vtt": paths["vtt"],
    }.get(stage_name)


def summarize_stage_output(stage_name, payload, paths):
    if stage_name == "audio":
        return {
            "status": "ok",
            "output": str(paths["audio"]),
            "audio_stream": payload.get("audio_stream"),
            "sample_rate": payload.get("sample_rate"),
            "channels": payload.get("channels"),
            "duration_seconds": payload.get("duration_seconds"),
        }
    if stage_name == "asr":
        transcription = payload.get("transcription") or {}
        return {
            "status": "ok",
            "output": str(paths["source_segments"]),
            "provider": payload.get("provider"),
            "model": payload.get("model"),
            "request_id": payload.get("request_id"),
            "language_hint": payload.get("language_hint"),
            "segments": len(payload.get("segments") or []),
            "segmentation": payload.get("segmentation"),
            "mode": transcription.get("mode"),
            "fallback_used": transcription.get("fallback_used"),
            "fallback_reason": transcription.get("fallback_reason"),
            "sample_interval": payload.get("sample_interval"),
        }
    if stage_name == "rebalance":
        info = payload.get("rebalanced") or {}
        return {
            "status": "ok",
            "output": str(paths["rebalanced_segments"]),
            "input_segments": info.get("input_segments"),
            "output_segments": info.get("output_segments"),
            "settings": {
                "min_duration": info.get("min_duration"),
                "max_duration": info.get("max_duration"),
                "max_chars": info.get("max_chars"),
                "min_chars": info.get("min_chars"),
                "hard_gap": info.get("hard_gap"),
                "merge_gap": info.get("merge_gap"),
            },
        }
    if stage_name == "semantic_repair":
        info = payload.get("semantic_repair") or {}
        return {
            "status": "ok",
            "output": str(paths["semantic_segments"]),
            "input_segments": info.get("input_segments"),
            "output_segments": info.get("output_segments"),
            "model_enabled": info.get("model_enabled"),
            "source_language": info.get("source_language"),
            "settings": {
                "merge_gap": info.get("merge_gap"),
                "max_merge_duration": info.get("max_merge_duration"),
                "context_radius": info.get("context_radius"),
            },
        }
    if stage_name == "translation":
        info = payload.get("translation") or {}
        return {
            "status": "ok",
            "output": str(paths["translated_segments"]),
            "provider": info.get("provider"),
            "model": info.get("model"),
            "segments": len(payload.get("segments") or []),
            "target_language": info.get("target_language"),
            "target_locale": info.get("target_locale"),
        }
    if stage_name == "timing_polish":
        info = payload.get("timing_polish") or {}
        return {
            "status": "ok",
            "output": str(paths["polished_segments"]),
            "input_segments": info.get("input_segments"),
            "output_segments": info.get("output_segments"),
            "gap_adjustments": info.get("gap_adjustments"),
            "stretch_adjustments": info.get("stretch_adjustments"),
        }
    if stage_name in {"export_srt", "export_vtt"}:
        return {
            "status": "ok",
            "output": payload.get("output"),
            "format": payload.get("format"),
            "cues": payload.get("cues"),
            "max_line_length": payload.get("max_line_length"),
            "max_lines": payload.get("max_lines"),
            "punctuation_mode": payload.get("punctuation_mode"),
        }
    if stage_name in {"lint_srt", "lint_vtt"}:
        return {
            "status": "ok",
            "input": payload.get("input"),
            "cues": payload.get("cues"),
            "errors": len(payload.get("errors") or []),
            "warnings": len(payload.get("warnings") or []),
            "error_messages": payload.get("errors") or [],
            "warning_messages": payload.get("warnings") or [],
        }
    return {"status": "ok"}


def load_summary(summary_path):
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_summary(summary_path, summary):
    summary["updated_at"] = utc_now()
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_complete(stage_name, summary, paths):
    entry = (summary.get("stages") or {}).get(stage_name) or {}
    if stage_name in {"lint_srt", "lint_vtt"}:
        return entry.get("status") == "ok"
    output_path = stage_output_path(stage_name, paths)
    return bool(output_path and Path(output_path).exists())


def build_stage_commands(video_path, paths, args):
    return [
        (
            "audio",
            [
                sys.executable,
                str(SCRIPT_DIR / "extract_audio.py"),
                str(video_path),
                str(paths["audio"]),
                "--audio-stream",
                "0",
            ],
        ),
        (
            "asr",
            [
                sys.executable,
                str(SCRIPT_DIR / "transcribe_with_fallback.py"),
                str(paths["audio"]),
                str(paths["source_segments"]),
                "--video-path",
                str(video_path),
                "--asr-language-hint",
                args.asr_language_hint,
                "--disable-semantic-punctuation",
                "--max-sentence-silence",
                "200",
                "--multi-threshold-mode-enabled",
            ],
        ),
        (
            "rebalance",
            [
                sys.executable,
                str(SCRIPT_DIR / "rebalance_segments.py"),
                str(paths["source_segments"]),
                str(paths["rebalanced_segments"]),
                "--min-duration",
                "0.9",
                "--max-duration",
                "5.2",
                "--max-chars",
                "24",
                "--min-chars",
                "4",
                "--hard-gap",
                "0.8",
                "--merge-gap",
                "0.35",
            ],
        ),
        (
            "semantic_repair",
            [
                sys.executable,
                str(SCRIPT_DIR / "semantic_repair_segments.py"),
                str(paths["rebalanced_segments"]),
                str(paths["semantic_segments"]),
                "--merge-gap",
                "0.45",
                "--max-merge-duration",
                "6.0",
                "--source-language",
                args.source_language,
                "--disable-model-rewrite",
            ],
        ),
        (
            "translation",
            [
                sys.executable,
                str(SCRIPT_DIR / "translate_segments.py"),
                str(paths["semantic_segments"]),
                str(paths["translated_segments"]),
                "--target-language",
                args.target_language,
                "--target-locale",
                args.target_locale,
                "--source-language",
                args.source_language,
                "--batch-size",
                str(args.translation_batch_size),
            ],
        ),
        (
            "timing_polish",
            [
                sys.executable,
                str(SCRIPT_DIR / "polish_segment_timing.py"),
                str(paths["translated_segments"]),
                str(paths["polished_segments"]),
                "--min-duration",
                "0.8",
                "--min-gap",
                "0.08",
            ],
        ),
        (
            "export_srt",
            [
                sys.executable,
                str(SCRIPT_DIR / "segments_to_subtitles.py"),
                str(paths["polished_segments"]),
                str(paths["srt"]),
                "--format",
                "srt",
                "--max-line-length",
                "42",
                "--max-lines",
                "0",
                "--punctuation-mode",
                "minimal",
            ],
        ),
        (
            "export_vtt",
            [
                sys.executable,
                str(SCRIPT_DIR / "segments_to_subtitles.py"),
                str(paths["polished_segments"]),
                str(paths["vtt"]),
                "--format",
                "vtt",
                "--max-line-length",
                "42",
                "--max-lines",
                "0",
                "--punctuation-mode",
                "minimal",
            ],
        ),
        (
            "lint_srt",
            [
                sys.executable,
                str(SCRIPT_DIR / "lint_subtitles.py"),
                str(paths["srt"]),
                "--json",
            ],
        ),
        (
            "lint_vtt",
            [
                sys.executable,
                str(SCRIPT_DIR / "lint_subtitles.py"),
                str(paths["vtt"]),
                "--json",
            ],
        ),
    ]


def compact_video_result(video_path, summary, summary_path):
    stages = summary.get("stages") or {}
    return {
        "stem": video_path.stem,
        "input": str(video_path),
        "status": summary.get("status"),
        "failed_stage": summary.get("failed_stage"),
        "summary_path": str(summary_path),
        "srt": summary.get("outputs", {}).get("srt"),
        "vtt": summary.get("outputs", {}).get("vtt"),
        "lint": {
            "srt_errors": (stages.get("lint_srt") or {}).get("errors"),
            "srt_warnings": (stages.get("lint_srt") or {}).get("warnings"),
            "vtt_errors": (stages.get("lint_vtt") or {}).get("errors"),
            "vtt_warnings": (stages.get("lint_vtt") or {}).get("warnings"),
        },
    }


def process_video(video_path, output_dir, args):
    target_code = args.target_code or slugify(args.target_language)
    paths = output_paths(output_dir, video_path.stem, target_code)
    paths["work_dir"].mkdir(parents=True, exist_ok=True)

    existing = load_summary(paths["summary"])
    summary = {
        "input": str(video_path),
        "output_dir": str(output_dir),
        "work_dir": str(paths["work_dir"]),
        "target_language": args.target_language,
        "target_locale": args.target_locale,
        "target_code": target_code,
        "status": "running",
        "started_at": existing.get("started_at") or utc_now(),
        "attempts": int(existing.get("attempts") or 0) + 1,
        "stages": existing.get("stages") or {},
        "outputs": {
            "source_segments": str(paths["source_segments"]),
            "rebalanced_segments": str(paths["rebalanced_segments"]),
            "semantic_segments": str(paths["semantic_segments"]),
            "translated_segments": str(paths["translated_segments"]),
            "segments": str(paths["polished_segments"]),
            "srt": str(paths["srt"]),
            "vtt": str(paths["vtt"]),
            "summary": str(paths["summary"]),
        },
        "settings": {
            "start_at": args.start_at,
            "stop_after": args.stop_after or None,
            "translation_batch_size": args.translation_batch_size,
            "command_timeout": args.command_timeout,
            "skip_existing": args.skip_existing,
        },
    }
    summary.pop("failed_stage", None)
    summary.pop("error", None)

    stage_commands = build_stage_commands(video_path, paths, args)
    start_index = STAGE_ORDER.index(args.start_at)
    if args.stop_after:
        stop_index = STAGE_ORDER.index(args.stop_after)
        if stop_index < start_index:
            raise RuntimeError("--stop-after must be at or after --start-at")
    else:
        stop_index = len(STAGE_ORDER) - 1
    active_stages = [
        item
        for item in stage_commands
        if start_index <= STAGE_ORDER.index(item[0]) <= stop_index
    ]

    for stage_name in STAGE_ORDER[start_index : stop_index + 1]:
        summary["stages"].pop(stage_name, None)
    write_summary(paths["summary"], summary)

    try:
        for stage_name, command in active_stages:
            if args.skip_existing and stage_complete(stage_name, summary, paths):
                existing_entry = (existing.get("stages") or {}).get(stage_name)
                if existing_entry:
                    summary["stages"][stage_name] = existing_entry
                else:
                    output_path = stage_output_path(stage_name, paths)
                    summary["stages"][stage_name] = {
                        "status": "skipped",
                        "reason": "existing_output",
                        "output": str(output_path) if output_path else None,
                    }
                write_summary(paths["summary"], summary)
                continue

            payload = run_json_command(command, timeout=args.command_timeout)
            summary["stages"][stage_name] = summarize_stage_output(stage_name, payload, paths)
            write_summary(paths["summary"], summary)

        summary["status"] = "ok"
        summary["completed_at"] = utc_now()
    except subprocess.TimeoutExpired as exc:
        summary["status"] = "failed"
        summary["failed_stage"] = stage_name
        summary["error"] = f"Timeout after {exc.timeout}s"
    except Exception as exc:
        summary["status"] = "failed"
        summary["failed_stage"] = stage_name
        summary["error"] = str(exc)

    write_summary(paths["summary"], summary)
    return compact_video_result(video_path, summary, paths["summary"])


def build_batch_summary(args, input_dir, output_dir, target_code, results, started_at):
    failed_by_stage = {}
    for item in results:
        if item.get("status") != "failed":
            continue
        stage_name = item.get("failed_stage") or "unknown"
        failed_by_stage[stage_name] = failed_by_stage.get(stage_name, 0) + 1

    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "target_language": args.target_language,
        "target_locale": args.target_locale,
        "target_code": target_code,
        "started_at": started_at,
        "videos": results,
        "counts": {
            "total": len(results),
            "ok": sum(1 for item in results if item.get("status") == "ok"),
            "failed": sum(1 for item in results if item.get("status") == "failed"),
        },
        "failed_by_stage": failed_by_stage,
    }


def main():
    args = parse_args()
    target_code = args.target_code or slugify(args.target_language)
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    videos = collect_videos(input_dir, args.include_stems)
    if not videos:
        print(f"No supported video files found under {input_dir}", file=sys.stderr)
        return 1

    results = []
    failed = False
    batch_started_at = utc_now()
    for video_path in videos:
        result = process_video(video_path, output_dir, args)
        results.append(result)
        if result.get("status") != "ok":
            failed = True
            if args.fail_fast:
                break

    batch_summary = build_batch_summary(args, input_dir, output_dir, target_code, results, batch_started_at)
    batch_summary_path = output_dir / f"batch.{target_code}.summary.json"
    batch_summary["summary_path"] = str(batch_summary_path)
    batch_summary["completed_at"] = utc_now()
    batch_summary_path.write_text(
        json.dumps(batch_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "summary": str(batch_summary_path),
                "videos": len(results),
                "failed": failed,
            },
            ensure_ascii=False,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
