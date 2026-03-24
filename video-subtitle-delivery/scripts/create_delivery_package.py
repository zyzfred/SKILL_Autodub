#!/usr/bin/env python3

import argparse
import json
import shutil
from pathlib import Path

from delivery_common import (
    STYLE_PRESETS,
    collect_videos,
    copy_font_into_package,
    create_readme_text,
    ensure_dir,
    probe_resolution,
    resolve_font_choice,
    validate_delivery_root,
    write_ass,
    write_json,
    load_cues,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a final subtitle delivery folder with copied videos, subtitle files, styled ASS, burned videos, and a manifest.",
    )
    parser.add_argument(
        "--input-dir",
        default="data",
        help="Source video directory (default: data)",
    )
    parser.add_argument(
        "--subtitle-dir",
        default="output",
        help="Directory containing reviewed subtitle files (default: output)",
    )
    parser.add_argument(
        "--delivery-root",
        default="delivery/20260324_en_delivery",
        help="Target delivery folder (default: delivery/20260324_en_delivery)",
    )
    parser.add_argument(
        "--target-code",
        default="en",
        help="Target code used in subtitle filenames (default: en)",
    )
    parser.add_argument(
        "--style-preset",
        default="default-english-burnin",
        choices=sorted(STYLE_PRESETS.keys()),
        help="Style preset used for ASS generation (default: default-english-burnin)",
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
    parser.add_argument(
        "--include-stems",
        default="",
        help="Comma-separated video stems to include",
    )
    parser.add_argument(
        "--allow-download-font",
        action="store_true",
        help="Allow downloading a fallback font when no asset or system font is found",
    )
    parser.add_argument(
        "--package-zip",
        action="store_true",
        help="Create a zip archive after the delivery folder passes validation",
    )
    return parser.parse_args()


def build_ass_filter(ass_path, fonts_dir=None):
    escaped = ass_path.as_posix().replace("\\", "/").replace(":", r"\:")
    escaped = escaped.replace(",", r"\,").replace("[", r"\[").replace("]", r"\]")
    parts = [f"filename={escaped}"]
    if fonts_dir:
        font_escaped = Path(fonts_dir).as_posix().replace("\\", "/").replace(":", r"\:")
        font_escaped = font_escaped.replace(",", r"\,").replace("[", r"\[").replace("]", r"\]")
        parts.append(f"fontsdir={font_escaped}")
    return "ass=" + ":".join(parts)


def burn_video(video_path, ass_path, output_path, fonts_dir, args):
    import subprocess

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        build_ass_filter(ass_path, fonts_dir),
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
        str(output_path),
    ]
    subprocess.run(command, check=True)


def maybe_package(delivery_root):
    archive_root = delivery_root.with_suffix("")
    generated = shutil.make_archive(str(archive_root), "zip", root_dir=str(delivery_root))
    return str(Path(generated).resolve())


def main():
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    subtitle_dir = Path(args.subtitle_dir).expanduser().resolve()
    delivery_root = Path(args.delivery_root).expanduser().resolve()

    originals_dir = delivery_root / "original_videos"
    subtitles_out_dir = delivery_root / "subtitles"
    styled_ass_dir = delivery_root / "styled_ass"
    burned_dir = delivery_root / "burned_videos"
    fonts_dir = delivery_root / "fonts"
    for path in [originals_dir, subtitles_out_dir, styled_ass_dir, burned_dir]:
        ensure_dir(path)

    videos = collect_videos(input_dir, args.include_stems)
    if not videos:
        raise SystemExit(f"No supported video files found under {input_dir}")

    assets_fonts_dir = (Path(__file__).resolve().parent.parent / "assets/fonts").resolve()
    font_info = resolve_font_choice(
        assets_fonts_dir=assets_fonts_dir,
        preset_name=args.style_preset,
        allow_download_fallback=args.allow_download_font,
        download_dir=fonts_dir,
    )
    if font_info.get("font_source") in {"asset", "downloaded"}:
        font_info = copy_font_into_package(font_info, fonts_dir)

    manifest = {
        "delivery_root": str(delivery_root),
        "style_preset": args.style_preset,
        "font": font_info,
        "style": None,
        "files": [],
    }

    for video_path in videos:
        stem = video_path.stem
        srt_path = subtitle_dir / f"{stem}.{args.target_code}.srt"
        vtt_path = subtitle_dir / f"{stem}.{args.target_code}.vtt"
        if not srt_path.exists() or not vtt_path.exists():
            raise FileNotFoundError(
                f"Missing reviewed subtitles for {stem}. Expected both {srt_path.name} and {vtt_path.name}."
            )

        copied_video = originals_dir / video_path.name
        copied_srt = subtitles_out_dir / srt_path.name
        copied_vtt = subtitles_out_dir / vtt_path.name
        shutil.copy2(video_path, copied_video)
        shutil.copy2(srt_path, copied_srt)
        shutil.copy2(vtt_path, copied_vtt)

        width, height = probe_resolution(video_path)
        cues = load_cues(srt_path)
        ass_path = styled_ass_dir / f"{stem}.{args.target_code}.ass"
        style = write_ass(ass_path, cues, width, height, font_info["font_name"], args.style_preset)
        if manifest["style"] is None:
            manifest["style"] = style

        burned_path = burned_dir / f"{stem}.{args.target_code}.hardsub.mp4"
        burn_video(
            video_path=video_path,
            ass_path=ass_path,
            output_path=burned_path,
            fonts_dir=font_info.get("fonts_dir"),
            args=args,
        )

        manifest["files"].append(
            {
                "stem": stem,
                "source_video": str(video_path),
                "copied_video": str(copied_video),
                "srt": str(copied_srt),
                "vtt": str(copied_vtt),
                "ass": str(ass_path),
                "burned_video": str(burned_path),
                "resolution": {"width": width, "height": height},
                "style": style,
            }
        )

    write_json(delivery_root / "manifest.json", manifest)
    (delivery_root / "README.md").write_text(create_readme_text(manifest), encoding="utf-8")

    validation = validate_delivery_root(delivery_root)
    if not validation["ok"]:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 1

    archive_path = maybe_package(delivery_root) if args.package_zip else None
    print(
        json.dumps(
            {
                "delivery_root": str(delivery_root),
                "videos": len(videos),
                "manifest": str(delivery_root / "manifest.json"),
                "archive_path": archive_path,
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
