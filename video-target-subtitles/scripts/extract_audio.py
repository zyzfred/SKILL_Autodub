#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract ASR-friendly audio from a media file with ffmpeg.",
    )
    parser.add_argument("input_path", help="Input media file")
    parser.add_argument("output_path", help="Output audio file")
    parser.add_argument(
        "--audio-stream",
        type=int,
        default=0,
        help="Zero-based audio stream index to extract (default: 0)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Output sample rate in Hz (default: 16000)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        help="Output channel count (default: 1)",
    )
    parser.add_argument(
        "--codec",
        default="pcm_s16le",
        help="ffmpeg audio codec (default: pcm_s16le)",
    )
    parser.add_argument(
        "--start",
        type=float,
        help="Optional start time in seconds",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Optional extraction duration in seconds",
    )
    parser.add_argument(
        "--audio-filter",
        default="",
        help="Optional ffmpeg audio filter string",
    )
    return parser.parse_args()


def probe_audio(path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,channels,sample_rate",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    return streams[0] if streams else {}


def main():
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()

    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = ["ffmpeg", "-y"]
    if args.start is not None:
        command.extend(["-ss", str(args.start)])
    command.extend(["-i", str(input_path)])
    if args.duration is not None:
        command.extend(["-t", str(args.duration)])
    command.extend(
        [
            "-map",
            f"0:a:{args.audio_stream}",
            "-vn",
            "-ac",
            str(args.channels),
            "-ar",
            str(args.sample_rate),
            "-c:a",
            args.codec,
        ]
    )
    if args.audio_filter:
        command.extend(["-af", args.audio_filter])
    command.append(str(output_path))

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.strip() + "\n")
        return result.returncode

    audio_info = probe_audio(output_path)
    print(
        json.dumps(
            {
                "input": str(input_path),
                "output": str(output_path),
                "audio_stream": args.audio_stream,
                "sample_rate": int(audio_info.get("sample_rate", args.sample_rate)),
                "channels": int(audio_info.get("channels", args.channels)),
                "codec": audio_info.get("codec_name", args.codec),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
