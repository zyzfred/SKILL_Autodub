#!/usr/bin/env python3

import argparse
import base64
import difflib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from env_loader import load_dotenv
from segment_utils import write_json

load_dotenv()


DASHSCOPE_COMPAT_BASE_URLS = {
    "cn": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "intl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "us": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract subtitle-like text from sampled video frames with Qwen OCR.",
    )
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("output_json", help="Output segments JSON")
    parser.add_argument(
        "--model",
        default=os.environ.get(
            "SUBTITLE_OCR_MODEL",
            os.environ.get("QWEN_OCR_MODEL", "qwen-vl-ocr-latest"),
        ),
        help="Qwen OCR model name (default: SUBTITLE_OCR_MODEL, QWEN_OCR_MODEL, or qwen-vl-ocr-latest)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SUBTITLE_OCR_BASE_URL", ""),
        help="OpenAI-compatible DashScope OCR base URL override",
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.5,
        help="Seconds between OCR frame samples (default: 0.5)",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.88,
        help="Merge neighboring OCR samples when normalized text similarity reaches this threshold (default: 0.88)",
    )
    parser.add_argument(
        "--min-pixels",
        type=int,
        default=32 * 32 * 3,
        help="Minimum image pixel threshold passed to DashScope OCR (default: 3072)",
    )
    parser.add_argument(
        "--max-pixels",
        type=int,
        default=32 * 32 * 8192,
        help="Maximum image pixel threshold passed to DashScope OCR (default: 8388608)",
    )
    return parser.parse_args()


def resolve_api_key():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        return api_key
    raise RuntimeError("DASHSCOPE_API_KEY is not set")


def resolve_base_url(override):
    if override:
        return override
    region = os.environ.get("DASHSCOPE_REGION", "cn").strip().lower()
    return DASHSCOPE_COMPAT_BASE_URLS.get(region, DASHSCOPE_COMPAT_BASE_URLS["cn"])


def probe_video(path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    if not video_streams:
        raise RuntimeError(f"No video stream found in {path}")

    duration = None
    candidates = [payload.get("format", {}).get("duration")]
    candidates.extend(stream.get("duration") for stream in video_streams)
    for candidate in candidates:
        try:
            duration = float(candidate)
            break
        except (TypeError, ValueError):
            continue

    primary_video = video_streams[0]
    return {
        "duration_seconds": duration,
        "width": primary_video.get("width"),
        "height": primary_video.get("height"),
    }


def extract_frames(video_path, frames_dir, sample_interval):
    if sample_interval <= 0:
        raise ValueError("--sample-interval must be greater than 0")
    frame_pattern = frames_dir / "frame_%06d.jpg"
    fps = 1.0 / sample_interval
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps:.6f}",
        "-q:v",
        "3",
        "-start_number",
        "0",
        str(frame_pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg frame extraction failed")

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise RuntimeError("No frames were extracted for OCR")
    return frames


def encode_image(path):
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def extract_json_value(text):
    decoder = json.JSONDecoder()
    for start_index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start_index:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("Model response did not contain valid JSON")


def get_content_text(message):
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text") and item.text:
                parts.append(item.text)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)


def normalize_text(text):
    normalized = " ".join(str(text or "").split())
    if normalized.lower() in {"", "none", "null", "n/a", "empty"}:
        return ""
    if normalized in {"无", "没有"}:
        return ""
    return normalized


def parse_ocr_text(content):
    try:
        payload = extract_json_value(content)
    except ValueError:
        return normalize_text(content)

    if isinstance(payload, dict):
        for key in ("text", "subtitle", "content", "result"):
            if key in payload:
                return normalize_text(payload.get(key, ""))
        return normalize_text("")
    if isinstance(payload, list):
        parts = []
        for item in payload:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return normalize_text(" ".join(parts))
    return normalize_text(payload)


def build_messages(data_url, args):
    return [
        {
            "role": "system",
            "content": (
                "You extract only subtitle-style dialogue text from sampled video frames. "
                "Return JSON only in the form {\"text\":\"...\"}. "
                "Ignore logos, watermarks, timers, app chrome, and decorative scene text. "
                "Preserve the original language. "
                "If no subtitle-like dialogue text is visible, return {\"text\":\"\"}."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": data_url},
                    "min_pixels": args.min_pixels,
                    "max_pixels": args.max_pixels,
                },
                {
                    "type": "text",
                    "text": (
                        "Extract only the subtitle or dialogue text visible in this frame. "
                        "If there are two subtitle lines, join them with a single space. "
                        "Do not describe the image. Return JSON only."
                    ),
                },
            ],
        },
    ]


def ocr_frame(client, model, frame_path, args):
    data_url = f"data:image/jpeg;base64,{encode_image(frame_path)}"
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(data_url, args),
    )
    content = get_content_text(response.choices[0].message)
    return parse_ocr_text(content)


def frame_timestamp(frame_path, sample_interval):
    stem = frame_path.stem
    index = int(stem.split("_")[-1])
    return index * sample_interval


def comparison_key(text):
    return "".join(char for char in normalize_text(text) if not char.isspace())


def text_similarity(left, right):
    left_key = comparison_key(left)
    right_key = comparison_key(right)
    if not left_key or not right_key:
        return 0.0
    if left_key == right_key:
        return 1.0
    return difflib.SequenceMatcher(None, left_key, right_key).ratio()


def text_score(text):
    collapsed = comparison_key(text)
    known_chars = sum(1 for char in collapsed if char != "?")
    placeholders = collapsed.count("?")
    return (known_chars, -placeholders, len(collapsed))


def choose_better_text(current, candidate):
    if text_score(candidate) > text_score(current):
        return candidate
    return current


def build_segments(samples, sample_interval, duration_seconds, similarity_threshold):
    segments = []
    current = None

    for sample in samples:
        text = normalize_text(sample["text"])
        if not text:
            if current:
                segments.append(current)
                current = None
            continue

        sample_start = sample["timestamp"]
        sample_end = sample_start + sample_interval
        if duration_seconds is not None:
            sample_end = min(sample_end, duration_seconds)

        if current and text_similarity(current["text"], text) >= similarity_threshold:
            current["text"] = choose_better_text(current["text"], text)
            current["end"] = max(current["end"], sample_end)
            current["sample_count"] += 1
            continue

        if current:
            segments.append(current)
        current = {
            "start": sample_start,
            "end": sample_end,
            "text": text,
            "sample_count": 1,
        }

    if current:
        segments.append(current)

    normalized_segments = []
    for index, segment in enumerate(segments, start=1):
        end = max(segment["start"], segment["end"])
        normalized_segments.append(
            {
                "id": index,
                "start": round(segment["start"], 3),
                "end": round(end, 3),
                "text": segment["text"],
                "source_text": segment["text"],
                "ocr_sample_count": segment["sample_count"],
            }
        )
    return normalized_segments


def main():
    args = parse_args()
    input_path = Path(args.input_video).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()

    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    try:
        api_key = resolve_api_key()
        base_url = resolve_base_url(args.base_url)
        video_info = probe_video(input_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        from openai import OpenAI
    except ImportError:
        print(
            "openai is not installed. Install it with `uv pip install openai` or "
            "run the script via `uv run --with openai python ...`.",
            file=sys.stderr,
        )
        return 1

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        with tempfile.TemporaryDirectory(prefix="ocr-video-frames-") as temp_dir_name:
            frames_dir = Path(temp_dir_name)
            frames = extract_frames(input_path, frames_dir, args.sample_interval)
            samples = []
            frames_with_text = 0
            for frame in frames:
                text = ocr_frame(client, args.model, frame, args)
                if text:
                    frames_with_text += 1
                samples.append(
                    {
                        "timestamp": frame_timestamp(frame, args.sample_interval),
                        "text": text,
                    }
                )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    segments = build_segments(
        samples=samples,
        sample_interval=args.sample_interval,
        duration_seconds=video_info["duration_seconds"],
        similarity_threshold=args.similarity_threshold,
    )
    if not segments:
        print("OCR fallback did not find subtitle-like text in sampled frames", file=sys.stderr)
        return 1

    payload = {
        "provider": "dashscope-qwen-ocr",
        "mode": "ocr-fallback",
        "input": str(input_path),
        "model": args.model,
        "base_url": base_url,
        "sample_interval": args.sample_interval,
        "similarity_threshold": args.similarity_threshold,
        "duration_seconds": video_info["duration_seconds"],
        "frame_size": {
            "width": video_info["width"],
            "height": video_info["height"],
        },
        "frames_examined": len(samples),
        "frames_with_text": frames_with_text,
        "segments": segments,
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
