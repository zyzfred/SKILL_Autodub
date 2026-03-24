#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from delivery_common import build_ass_filter, run


def parse_args():
    parser = argparse.ArgumentParser(
        description="Burn a styled ASS subtitle file into a video with ffmpeg/libass.",
    )
    parser.add_argument("input_video", help="Source video path")
    parser.add_argument("input_ass", help="Styled ASS subtitle path")
    parser.add_argument("output_video", help="Burned MP4 output path")
    parser.add_argument(
        "--fonts-dir",
        default="",
        help="Optional fonts directory exposed to libass",
    )
    parser.add_argument(
        "--video-codec",
        default="libx264",
        help="Video codec for burned videos (default: libx264)",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="CRF used when video codec is libx264/libx265 (default: 18)",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        help="Encoder preset (default: medium)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_video = Path(args.input_video).expanduser().resolve()
    input_ass = Path(args.input_ass).expanduser().resolve()
    output_video = Path(args.output_video).expanduser().resolve()
    output_video.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        build_ass_filter(input_ass, args.fonts_dir or None),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        args.video_codec,
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    run(command)
    print(
        json.dumps(
            {
                "input_video": str(input_video),
                "input_ass": str(input_ass),
                "output_video": str(output_video),
                "fonts_dir": args.fonts_dir or None,
                "video_codec": args.video_codec,
                "crf": args.crf,
                "preset": args.preset,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
