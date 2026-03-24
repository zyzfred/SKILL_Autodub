#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize per-file subtitle run summaries into machine-readable and markdown batch reports.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing *.run-summary.json files (default: output)",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Optional batch summary JSON to use as the source of run-summary paths",
    )
    parser.add_argument(
        "--target-code",
        default="en",
        help="Target code used for default output filenames (default: en)",
    )
    parser.add_argument(
        "--json-output",
        default="",
        help="Optional explicit path for the summarized JSON output",
    )
    parser.add_argument(
        "--markdown-output",
        default="",
        help="Optional explicit path for the markdown summary output",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_summaries(output_dir, summary_path):
    if summary_path:
        payload = load_json(Path(summary_path).expanduser().resolve())
        paths = [
            Path(item.get("summary_path")).expanduser().resolve()
            for item in payload.get("videos") or []
            if item.get("summary_path")
        ]
        return [(path, load_json(path)) for path in paths]
    return [
        (path, load_json(path))
        for path in sorted(Path(output_dir).expanduser().resolve().glob("*.run-summary.json"))
    ]


def lint_counts(stage_payload):
    if not stage_payload:
        return 0, 0
    errors = stage_payload.get("errors")
    warnings = stage_payload.get("warnings")
    if isinstance(errors, list):
        errors = len(errors)
    if isinstance(warnings, list):
        warnings = len(warnings)
    return int(errors or 0), int(warnings or 0)


def summarize_video(summary_path, summary):
    input_path = Path(summary.get("input", ""))
    stages = summary.get("stages") or {}
    srt_errors, srt_warnings = lint_counts(stages.get("lint_srt"))
    vtt_errors, vtt_warnings = lint_counts(stages.get("lint_vtt"))
    return {
        "stem": input_path.stem,
        "input": str(input_path) if input_path else None,
        "status": summary.get("status"),
        "failed_stage": summary.get("failed_stage"),
        "error": summary.get("error"),
        "summary_path": str(summary_path),
        "srt": (summary.get("outputs") or {}).get("srt"),
        "vtt": (summary.get("outputs") or {}).get("vtt"),
        "lint": {
            "srt_errors": srt_errors,
            "srt_warnings": srt_warnings,
            "vtt_errors": vtt_errors,
            "vtt_warnings": vtt_warnings,
        },
    }


def build_summary(source_summaries):
    videos = [summarize_video(path, item) for path, item in source_summaries]
    failed_by_stage = {}
    total_srt_errors = 0
    total_srt_warnings = 0
    total_vtt_errors = 0
    total_vtt_warnings = 0
    for item in videos:
        if item.get("status") == "failed":
            stage_name = item.get("failed_stage") or "unknown"
            failed_by_stage[stage_name] = failed_by_stage.get(stage_name, 0) + 1
        lint = item.get("lint") or {}
        total_srt_errors += lint.get("srt_errors") or 0
        total_srt_warnings += lint.get("srt_warnings") or 0
        total_vtt_errors += lint.get("vtt_errors") or 0
        total_vtt_warnings += lint.get("vtt_warnings") or 0

    return {
        "videos": videos,
        "counts": {
            "total": len(videos),
            "ok": sum(1 for item in videos if item.get("status") == "ok"),
            "failed": sum(1 for item in videos if item.get("status") == "failed"),
            "total_srt_errors": total_srt_errors,
            "total_srt_warnings": total_srt_warnings,
            "total_vtt_errors": total_vtt_errors,
            "total_vtt_warnings": total_vtt_warnings,
        },
        "failed_by_stage": failed_by_stage,
    }


def to_markdown(summary):
    lines = [
        "# Batch Subtitle Summary",
        "",
        f"- Total videos: {summary['counts']['total']}",
        f"- OK: {summary['counts']['ok']}",
        f"- Failed: {summary['counts']['failed']}",
        f"- Total SRT warnings: {summary['counts']['total_srt_warnings']}",
        f"- Total VTT warnings: {summary['counts']['total_vtt_warnings']}",
        "",
        "## Per Video",
        "",
    ]
    for item in summary["videos"]:
        status = item.get("status")
        line = f"- `{item['stem']}`: `{status}`"
        if item.get("failed_stage"):
            line += f" at `{item['failed_stage']}`"
        line += (
            f" | SRT warnings `{item['lint']['srt_warnings']}`"
            f" | VTT warnings `{item['lint']['vtt_warnings']}`"
        )
        lines.append(line)
        if item.get("error"):
            lines.append(f"  error: {item['error']}")
    if summary["failed_by_stage"]:
        lines.extend(["", "## Failed By Stage", ""])
        for stage_name, count in sorted(summary["failed_by_stage"].items()):
            lines.append(f"- `{stage_name}`: {count}")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    summaries = collect_summaries(output_dir, args.summary_path)
    if not summaries:
        raise SystemExit(f"No run summaries found under {output_dir}")

    summary = build_summary(summaries)
    json_output = (
        Path(args.json_output).expanduser().resolve()
        if args.json_output
        else output_dir / f"batch.{args.target_code}.summary.json"
    )
    markdown_output = (
        Path(args.markdown_output).expanduser().resolve()
        if args.markdown_output
        else output_dir / f"batch.{args.target_code}.summary.md"
    )

    json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(to_markdown(summary), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_summary": str(json_output),
                "markdown_summary": str(markdown_output),
                "videos": summary["counts"]["total"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
