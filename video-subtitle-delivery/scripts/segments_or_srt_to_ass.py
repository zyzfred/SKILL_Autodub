#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from delivery_common import load_cues, probe_resolution, write_ass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert reviewed subtitles or final segments JSON into a styled ASS file.",
    )
    parser.add_argument("input_path", help="Input .srt or final segments .json")
    parser.add_argument("output_ass", help="Output ASS path")
    parser.add_argument(
        "--video-path",
        default="",
        help="Video used to infer the output resolution",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=0,
        help="Explicit output width when no video path is provided",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=0,
        help="Explicit output height when no video path is provided",
    )
    parser.add_argument(
        "--font-name",
        required=True,
        help="Resolved font family name used in the ASS style",
    )
    parser.add_argument(
        "--style-preset",
        default="default-english-burnin",
        help="Style preset name (default: default-english-burnin)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    output_ass = Path(args.output_ass).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    if args.video_path:
        width, height = probe_resolution(Path(args.video_path).expanduser().resolve())
    elif args.width and args.height:
        width, height = args.width, args.height
    else:
        raise SystemExit("Pass --video-path or both --width and --height")

    cues = load_cues(input_path)
    output_ass.parent.mkdir(parents=True, exist_ok=True)
    style = write_ass(output_ass, cues, width, height, args.font_name, args.style_preset)
    print(
        json.dumps(
            {
                "input": str(input_path),
                "output": str(output_ass),
                "cues": len(cues),
                "resolution": {"width": width, "height": height},
                "style": style,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
