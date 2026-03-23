#!/usr/bin/env python3

import argparse
import json
import math
import re
import sys
from pathlib import Path


SOFT_BREAK_MARKER = "\uE000"
STRONG_BREAK_MARKER = "\uE001"
ELLIPSIS_RE = re.compile(r"(?:\.{3,}|…+)")
CLAUSE_PUNCT_RE = re.compile(r"[，,、;；:：]+")
TERMINAL_STOP_RE = re.compile(
    r"(?<=[\w\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff])[。.]+(?=(?:\s|$))"
)
SURROUNDED_DASH_RE = re.compile(r"\s+[—–-]+\s+")
HARD_BREAK_RE = re.compile(r"\r?\n+")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert normalized segment JSON into SRT or VTT subtitles.",
    )
    parser.add_argument("input_json", help="Segment JSON file")
    parser.add_argument("output_path", help="Output subtitle file")
    parser.add_argument(
        "--format",
        choices=("srt", "vtt"),
        help="Subtitle format. Defaults to the output file extension.",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=42,
        help="Preferred maximum line length for soft wrapping. Disabled at 0. Default: 42.",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=0,
        help="Soft target for wrapped lines per cue. Export keeps all wrapped lines. 0 means unlimited.",
    )
    parser.add_argument(
        "--punctuation-mode",
        choices=("preserve", "minimal"),
        default="minimal",
        help="How aggressively to simplify subtitle punctuation before export (default: minimal)",
    )
    return parser.parse_args()


def load_segments(path):
    payload = json.loads(path.read_text())
    if isinstance(payload, dict):
        segments = payload.get("segments")
    elif isinstance(payload, list):
        segments = payload
    else:
        raise ValueError("Input JSON must be a list or an object with a segments field")

    if not isinstance(segments, list):
        raise ValueError("segments must be a list")
    return segments


def split_long_token(token, max_line_length):
    return [token[i : i + max_line_length] for i in range(0, len(token), max_line_length)]


def normalize_punctuation(text, punctuation_mode):
    normalized = str(text).strip()
    if not normalized:
        return ""

    normalized = HARD_BREAK_RE.sub(f" {STRONG_BREAK_MARKER} ", normalized)
    if punctuation_mode == "minimal":
        normalized = ELLIPSIS_RE.sub(f" {STRONG_BREAK_MARKER} ", normalized)
        normalized = CLAUSE_PUNCT_RE.sub(f" {SOFT_BREAK_MARKER} ", normalized)
        normalized = SURROUNDED_DASH_RE.sub(f" {SOFT_BREAK_MARKER} ", normalized)
        normalized = TERMINAL_STOP_RE.sub(f" {STRONG_BREAK_MARKER} ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(
        rf"(?:\s*{STRONG_BREAK_MARKER}\s*)+",
        f" {STRONG_BREAK_MARKER} ",
        normalized,
    ).strip()
    normalized = re.sub(
        rf"(?:\s*{SOFT_BREAK_MARKER}\s*)+",
        f" {SOFT_BREAK_MARKER} ",
        normalized,
    ).strip()
    normalized = re.sub(
        rf"(?:\s*{SOFT_BREAK_MARKER}\s*)*(?:\s*{STRONG_BREAK_MARKER}\s*)+",
        f" {STRONG_BREAK_MARKER} ",
        normalized,
    ).strip()
    normalized = re.sub(rf"^(?:{STRONG_BREAK_MARKER}|{SOFT_BREAK_MARKER}\s*)+", "", normalized)
    normalized = re.sub(rf"(?:\s*(?:{STRONG_BREAK_MARKER}|{SOFT_BREAK_MARKER}))+$", "", normalized)
    return normalized.strip()


def prepare_units(text, max_line_length, punctuation_mode):
    normalized = normalize_punctuation(text, punctuation_mode)
    if not normalized:
        return []

    units = []
    for raw_token in normalized.split(" "):
        if raw_token in {SOFT_BREAK_MARKER, STRONG_BREAK_MARKER}:
            if units:
                units[-1]["break_priority"] = max(
                    units[-1]["break_priority"],
                    2 if raw_token == STRONG_BREAK_MARKER else 1,
                )
            continue
        token_parts = (
            split_long_token(raw_token, max_line_length)
            if max_line_length > 0 and len(raw_token) > max_line_length
            else [raw_token]
        )
        for index, token in enumerate(token_parts):
            units.append(
                {
                    "text": token,
                    "break_priority": 1 if index < len(token_parts) - 1 else 0,
                }
            )
    return units


def join_units(units):
    return " ".join(unit["text"] for unit in units if unit["text"]).strip()


def recalc_state(units):
    line_length = len(join_units(units))
    last_soft_break = 0
    last_strong_break = 0
    for index, unit in enumerate(units, start=1):
        if unit.get("break_priority", 0) >= 1:
            last_soft_break = index
        if unit.get("break_priority", 0) >= 2:
            last_strong_break = index
    return line_length, last_soft_break, last_strong_break


def wrap_text(text, max_line_length, max_lines, punctuation_mode):
    if max_line_length <= 0:
        return normalize_punctuation(text, punctuation_mode)

    units = prepare_units(text, max_line_length, punctuation_mode)
    if not units:
        return ""

    lines = []
    current = []
    current_length = 0
    last_soft_break = 0
    last_strong_break = 0

    for index, unit in enumerate(units):
        candidate = current + [unit]
        candidate_length = len(join_units(candidate))
        if candidate_length <= max_line_length or not current:
            current = candidate
            current_length = candidate_length
            current_length, last_soft_break, last_strong_break = recalc_state(current)
            has_more_units = index < len(units) - 1
            if (
                has_more_units
                and unit.get("break_priority", 0) >= 2
                and current_length >= max(12, int(max_line_length * 0.3))
            ):
                lines.append(join_units(current))
                current = []
                current_length = 0
                last_soft_break = 0
                last_strong_break = 0
            continue

        split_at = last_strong_break or last_soft_break or len(current)
        lines.append(join_units(current[:split_at]))
        current = current[split_at:] + [unit]
        current_length, last_soft_break, last_strong_break = recalc_state(current)

        while current and current_length > max_line_length:
            overflow_split_at = last_strong_break or last_soft_break or max(1, len(current) - 1)
            lines.append(join_units(current[:overflow_split_at]))
            current = current[overflow_split_at:]
            current_length, last_soft_break, last_strong_break = recalc_state(current)

    if current:
        lines.append(join_units(current))

    if max_lines > 0 and len(lines) > max_lines:
        # Export keeps all lines. max-lines is only a soft target for lint and review.
        pass

    return "\n".join(line for line in lines if line)


def format_timestamp(seconds, fmt):
    if seconds < 0:
        raise ValueError("Timestamps must be non-negative")

    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    minutes = (millis % 3_600_000) // 60_000
    secs = (millis % 60_000) // 1000
    ms = millis % 1000
    separator = "," if fmt == "srt" else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{ms:03d}"


def resolve_format(output_path, requested_format):
    if requested_format:
        return requested_format
    extension = output_path.suffix.lower().lstrip(".")
    if extension in {"srt", "vtt"}:
        return extension
    raise ValueError("Could not infer subtitle format. Pass --format srt or --format vtt.")


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()

    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    subtitle_format = resolve_format(output_path, args.format)
    segments = load_segments(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cues = []
    previous_end = -math.inf
    for index, segment in enumerate(segments, start=1):
        start = float(segment["start"])
        end = float(segment["end"])
        text = wrap_text(
            str(segment.get("text", "")),
            args.max_line_length,
            args.max_lines,
            args.punctuation_mode,
        )

        if end <= start:
            raise ValueError(f"Segment {index} has end <= start")
        if start < previous_end:
            raise ValueError(f"Segment {index} starts before the previous segment ends")
        previous_end = end

        start_stamp = format_timestamp(start, subtitle_format)
        end_stamp = format_timestamp(end, subtitle_format)

        if subtitle_format == "srt":
            cue = f"{index}\n{start_stamp} --> {end_stamp}\n{text}\n"
        else:
            cue = f"{start_stamp} --> {end_stamp}\n{text}\n"
        cues.append(cue)

    if subtitle_format == "vtt":
        body = "WEBVTT\n\n" + "\n".join(cues).rstrip() + "\n"
    else:
        body = "\n".join(cues).rstrip() + "\n"

    output_path.write_text(body)
    print(
        json.dumps(
            {
                "input": str(input_path),
                "output": str(output_path),
                "format": subtitle_format,
                "cues": len(segments),
                "max_line_length": args.max_line_length,
                "max_lines": args.max_lines,
                "punctuation_mode": args.punctuation_mode,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
