#!/usr/bin/env python3

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)
EPSILON = 1e-6


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lint SRT or VTT subtitle files for timing and readability issues.",
    )
    parser.add_argument("subtitle_path", help="Subtitle file")
    parser.add_argument("--max-line-length", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--max-cps", type=float, default=20.0)
    parser.add_argument("--min-duration", type=float, default=0.8)
    parser.add_argument("--max-duration", type=float, default=7.0)
    parser.add_argument("--min-gap", type=float, default=0.08)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def parse_timestamp(value):
    value = value.replace(",", ".")
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def split_blocks(text):
    return [block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]


def parse_srt(text):
    cues = []
    for block in split_blocks(text):
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if TIMESTAMP_RE.match(lines[0]):
            timestamp_line = lines[0]
            text_lines = lines[1:]
            cue_index = len(cues) + 1
        elif len(lines) >= 2 and TIMESTAMP_RE.match(lines[1]):
            cue_index = int(lines[0]) if lines[0].isdigit() else len(cues) + 1
            timestamp_line = lines[1]
            text_lines = lines[2:]
        else:
            raise ValueError(f"Could not parse SRT block:\n{block}")

        match = TIMESTAMP_RE.match(timestamp_line)
        cues.append(
            Cue(
                index=cue_index,
                start=parse_timestamp(match.group("start")),
                end=parse_timestamp(match.group("end")),
                text="\n".join(text_lines).strip(),
            )
        )
    return cues


def parse_vtt(text):
    stripped = text.lstrip("\ufeff").strip()
    if stripped.startswith("WEBVTT"):
        stripped = stripped[len("WEBVTT") :].lstrip()

    cues = []
    for block in split_blocks(stripped):
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        if TIMESTAMP_RE.match(lines[0]):
            timestamp_line = lines[0]
            text_lines = lines[1:]
        elif len(lines) >= 2 and TIMESTAMP_RE.match(lines[1]):
            timestamp_line = lines[1]
            text_lines = lines[2:]
        else:
            raise ValueError(f"Could not parse VTT block:\n{block}")

        match = TIMESTAMP_RE.match(timestamp_line)
        cues.append(
            Cue(
                index=len(cues) + 1,
                start=parse_timestamp(match.group("start")),
                end=parse_timestamp(match.group("end")),
                text="\n".join(text_lines).strip(),
            )
        )
    return cues


def parse_subtitle(path):
    text = path.read_text()
    suffix = path.suffix.lower()
    if suffix == ".srt":
        return parse_srt(text)
    if suffix == ".vtt":
        return parse_vtt(text)
    raise ValueError("Unsupported subtitle file type. Use .srt or .vtt")


def lint_cues(cues, args):
    errors = []
    warnings = []
    previous_end = None

    for cue in cues:
        duration = cue.end - cue.start
        text_no_space = re.sub(r"\s+", "", cue.text)
        cps = len(text_no_space) / duration if duration > 0 else float("inf")
        lines = cue.text.splitlines() or [cue.text]

        if not cue.text.strip():
            errors.append(f"Cue {cue.index}: empty text")
        if cue.end <= cue.start + EPSILON:
            errors.append(f"Cue {cue.index}: end time must be greater than start time")
        if previous_end is not None and cue.start + EPSILON < previous_end:
            errors.append(f"Cue {cue.index}: overlaps the previous cue")
        if previous_end is not None and cue.start - previous_end + EPSILON < args.min_gap:
            warnings.append(
                f"Cue {cue.index}: gap {cue.start - previous_end:.3f}s is below {args.min_gap:.3f}s"
            )
        if duration + EPSILON < args.min_duration:
            warnings.append(
                f"Cue {cue.index}: duration {duration:.3f}s is below {args.min_duration:.3f}s"
            )
        if duration > args.max_duration + EPSILON:
            warnings.append(
                f"Cue {cue.index}: duration {duration:.3f}s exceeds {args.max_duration:.3f}s"
            )
        if len(lines) > args.max_lines:
            warnings.append(
                f"Cue {cue.index}: {len(lines)} lines exceeds max {args.max_lines}"
            )
        longest_line = max((len(line) for line in lines), default=0)
        if longest_line > args.max_line_length:
            warnings.append(
                f"Cue {cue.index}: longest line {longest_line} exceeds {args.max_line_length}"
            )
        if cps > args.max_cps + EPSILON:
            warnings.append(
                f"Cue {cue.index}: reading speed {cps:.2f} cps exceeds {args.max_cps:.2f}"
            )

        previous_end = cue.end

    return errors, warnings


def main():
    args = parse_args()
    subtitle_path = Path(args.subtitle_path).expanduser().resolve()
    if not subtitle_path.exists():
        print(f"Input not found: {subtitle_path}", file=sys.stderr)
        return 1

    cues = parse_subtitle(subtitle_path)
    errors, warnings = lint_cues(cues, args)

    result = {
        "input": str(subtitle_path),
        "cues": len(cues),
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"File: {subtitle_path}")
        print(f"Cues: {len(cues)}")
        print(f"Errors: {len(errors)}")
        for message in errors:
            print(f"ERROR: {message}")
        print(f"Warnings: {len(warnings)}")
        for message in warnings:
            print(f"WARNING: {message}")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
