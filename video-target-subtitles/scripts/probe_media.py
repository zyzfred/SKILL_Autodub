#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize media streams with ffprobe.",
    )
    parser.add_argument("input_path", help="Input media file")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser.parse_args()


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def summarize_stream(stream):
    disposition = stream.get("disposition") or {}
    tags = stream.get("tags") or {}
    summary = {
        "index": stream.get("index"),
        "type": stream.get("codec_type"),
        "codec": stream.get("codec_name"),
        "language": tags.get("language"),
        "duration_seconds": to_float(stream.get("duration")),
        "default": bool(disposition.get("default")),
        "title": tags.get("title"),
    }

    if stream.get("codec_type") == "audio":
        summary.update(
            {
                "channels": to_int(stream.get("channels")),
                "sample_rate": to_int(stream.get("sample_rate")),
                "channel_layout": stream.get("channel_layout"),
            }
        )
    elif stream.get("codec_type") == "video":
        summary.update(
            {
                "width": to_int(stream.get("width")),
                "height": to_int(stream.get("height")),
                "pix_fmt": stream.get("pix_fmt"),
            }
        )
    elif stream.get("codec_type") == "subtitle":
        summary.update({"codec_long_name": stream.get("codec_long_name")})

    return summary


def main():
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.strip() + "\n")
        return result.returncode

    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    format_info = payload.get("format") or {}

    summary = {
        "input": str(input_path),
        "format_name": format_info.get("format_name"),
        "duration_seconds": to_float(format_info.get("duration")),
        "size_bytes": to_int(format_info.get("size")),
        "bit_rate": to_int(format_info.get("bit_rate")),
        "video_streams": [],
        "audio_streams": [],
        "subtitle_streams": [],
    }

    for stream in streams:
        stream_summary = summarize_stream(stream)
        stream_type = stream_summary["type"]
        if stream_type == "video":
            summary["video_streams"].append(stream_summary)
        elif stream_type == "audio":
            summary["audio_streams"].append(stream_summary)
        elif stream_type == "subtitle":
            summary["subtitle_streams"].append(stream_summary)

    summary["primary_video"] = next(
        (stream for stream in summary["video_streams"] if stream["default"]),
        summary["video_streams"][0] if summary["video_streams"] else None,
    )
    summary["primary_audio"] = next(
        (stream for stream in summary["audio_streams"] if stream["default"]),
        summary["audio_streams"][0] if summary["audio_streams"] else None,
    )

    if args.pretty:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
