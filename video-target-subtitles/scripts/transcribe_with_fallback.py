#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from env_loader import load_dotenv
from segment_utils import write_json

SCRIPT_DIR = Path(__file__).resolve().parent

load_dotenv(extra_roots=[Path.cwd(), SCRIPT_DIR])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Transcribe source segments with FunASR and fall back to OCR when speech recognition fails.",
    )
    parser.add_argument("input_audio", help="Input audio file")
    parser.add_argument("output_json", help="Output segments JSON")
    parser.add_argument(
        "--video-path",
        default="",
        help="Original video path used for OCR fallback",
    )
    parser.add_argument(
        "--asr-model",
        default="",
        help="FunASR model override",
    )
    parser.add_argument(
        "--asr-language-hint",
        default="",
        help="Optional FunASR language hint such as zh, en, or ja",
    )
    parser.add_argument(
        "--semantic-punctuation-enabled",
        dest="semantic_punctuation_enabled",
        action="store_true",
        help="Enable semantic sentence segmentation in FunASR",
    )
    parser.add_argument(
        "--disable-semantic-punctuation",
        dest="semantic_punctuation_enabled",
        action="store_false",
        help="Use VAD segmentation instead of semantic sentence segmentation",
    )
    parser.set_defaults(semantic_punctuation_enabled=None)
    parser.add_argument(
        "--max-sentence-silence",
        type=int,
        help="FunASR VAD silence threshold in ms",
    )
    parser.add_argument(
        "--multi-threshold-mode-enabled",
        action="store_true",
        help="Enable FunASR multi-threshold VAD mode",
    )
    parser.add_argument(
        "--speech-noise-threshold",
        type=float,
        help="Optional FunASR VAD sensitivity override in [-1.0, 1.0]",
    )
    parser.add_argument(
        "--disable-ocr-fallback",
        action="store_true",
        help="Fail instead of falling back to OCR when FunASR fails",
    )
    parser.add_argument(
        "--ocr-model",
        default="",
        help="Qwen OCR model override",
    )
    parser.add_argument(
        "--ocr-sample-interval",
        type=float,
        default=0.5,
        help="Seconds between OCR frame samples (default: 0.5)",
    )
    parser.add_argument(
        "--ocr-similarity-threshold",
        type=float,
        default=0.88,
        help="Merge neighboring OCR samples when normalized text similarity reaches this threshold (default: 0.88)",
    )
    return parser.parse_args()


def load_json_document(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_json_command(command, output_path):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        raise RuntimeError(message)
    if Path(output_path).exists():
        return load_json_document(output_path)
    return json.loads(result.stdout)


def annotate_payload(payload, transcription):
    document = dict(payload)
    existing = dict(document.get("transcription") or {})
    existing.update(transcription)
    document["transcription"] = existing
    return document


def segments_count(payload):
    return len(payload.get("segments") or [])


def build_asr_command(args, output_path):
    command = [
        sys.executable,
        str(SCRIPT_DIR / "funasr_transcribe.py"),
        str(Path(args.input_audio).expanduser().resolve()),
        str(output_path),
    ]
    if args.asr_model:
        command.extend(["--model", args.asr_model])
    if args.asr_language_hint:
        command.extend(["--language-hint", args.asr_language_hint])
    if args.semantic_punctuation_enabled is True:
        command.append("--semantic-punctuation-enabled")
    elif args.semantic_punctuation_enabled is False:
        command.append("--disable-semantic-punctuation")
    if args.max_sentence_silence is not None:
        command.extend(["--max-sentence-silence", str(args.max_sentence_silence)])
    if args.multi_threshold_mode_enabled:
        command.append("--multi-threshold-mode-enabled")
    if args.speech_noise_threshold is not None:
        command.extend(["--speech-noise-threshold", str(args.speech_noise_threshold)])
    return command


def build_ocr_command(args, video_path, output_path):
    command = [
        sys.executable,
        str(SCRIPT_DIR / "ocr_video_transcribe.py"),
        str(video_path),
        str(output_path),
        "--sample-interval",
        str(args.ocr_sample_interval),
        "--similarity-threshold",
        str(args.ocr_similarity_threshold),
    ]
    if args.ocr_model:
        command.extend(["--model", args.ocr_model])
    return command


def main():
    args = parse_args()
    output_path = Path(args.output_json).expanduser().resolve()
    video_path = Path(args.video_path).expanduser().resolve() if args.video_path else None

    with tempfile.TemporaryDirectory(prefix="subtitle-transcribe-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        asr_output = temp_dir / "asr.segments.json"
        asr_payload = None
        asr_error = None

        try:
            asr_payload = run_json_command(build_asr_command(args, asr_output), asr_output)
            if segments_count(asr_payload) <= 0:
                asr_error = "FunASR returned no usable segments"
        except Exception as exc:
            asr_error = str(exc)

        if asr_payload is not None and not asr_error:
            final_payload = annotate_payload(
                asr_payload,
                {
                    "mode": "speech",
                    "fallback_used": False,
                    "fallback_reason": None,
                    "primary_provider": asr_payload.get("provider"),
                    "primary_model": asr_payload.get("model"),
                    "primary_error": None,
                    "video_path": str(video_path) if video_path else None,
                },
            )
            write_json(output_path, final_payload)
            print(json.dumps(final_payload, ensure_ascii=False, indent=2))
            return 0

        if args.disable_ocr_fallback or not video_path:
            print(asr_error or "FunASR transcription failed", file=sys.stderr)
            return 1

        ocr_output = temp_dir / "ocr.segments.json"
        try:
            ocr_payload = run_json_command(
                build_ocr_command(args, video_path, ocr_output),
                ocr_output,
            )
            if segments_count(ocr_payload) <= 0:
                raise RuntimeError("OCR fallback returned no usable segments")
        except Exception as exc:
            combined_error = (
                f"FunASR failed: {asr_error or 'unknown error'}. "
                f"OCR fallback failed: {exc}"
            )
            print(combined_error, file=sys.stderr)
            return 1

        final_payload = annotate_payload(
            ocr_payload,
            {
                "mode": "ocr-fallback",
                "fallback_used": True,
                "fallback_reason": asr_error,
                "primary_provider": "dashscope-funasr",
                "primary_model": (asr_payload or {}).get("model") or args.asr_model or None,
                "primary_error": asr_error,
                "primary_segments": segments_count(asr_payload or {}),
                "video_path": str(video_path),
            },
        )
        write_json(output_path, final_payload)
        print(json.dumps(final_payload, ensure_ascii=False, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
