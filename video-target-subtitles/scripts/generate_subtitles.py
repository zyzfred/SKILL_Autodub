#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path

from env_loader import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent

load_dotenv(extra_roots=[Path.cwd(), SCRIPT_DIR])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate target-language subtitles with FunASR transcription and timestamp-preserving translation.",
    )
    parser.add_argument("input_path", help="Input video or audio file")
    parser.add_argument(
        "--target-language",
        required=True,
        help="Target subtitle language, for example English or Japanese",
    )
    parser.add_argument(
        "--target-locale",
        default="",
        help="Optional locale hint, for example en-US",
    )
    parser.add_argument(
        "--target-code",
        default="",
        help="Short code used in filenames, for example en or ja",
    )
    parser.add_argument(
        "--source-language",
        default="",
        help="Optional source language hint for translation",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--output-stem",
        default="",
        help="Optional base filename for outputs",
    )
    parser.add_argument(
        "--formats",
        default="srt,vtt",
        help="Comma-separated output formats (default: srt,vtt)",
    )
    parser.add_argument(
        "--audio-stream",
        type=int,
        default=0,
        help="Audio stream index for ffmpeg extraction (default: 0)",
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
        "--translation-model",
        default="",
        help="Translation model override",
    )
    parser.add_argument(
        "--enable-target-reflow",
        dest="enable_target_reflow",
        action="store_true",
        help="Opt into post-translation cue splitting when wrapping alone is not enough",
    )
    parser.add_argument(
        "--disable-target-reflow",
        dest="enable_target_reflow",
        action="store_false",
        help="Disable post-translation cue splitting (default behavior)",
    )
    parser.set_defaults(enable_target_reflow=False)
    parser.add_argument(
        "--target-max-line-chars",
        type=int,
        default=42,
        help="Preferred single-line character limit for space-delimited target cues (default: 42)",
    )
    parser.add_argument(
        "--target-max-cjk-line-chars",
        type=int,
        default=22,
        help="Preferred single-line character limit for CJK-heavy target cues (default: 22)",
    )
    parser.add_argument(
        "--target-max-cps",
        type=float,
        default=20.0,
        help="Target maximum reading speed for post-translation reflow (default: 20.0)",
    )
    parser.add_argument(
        "--target-min-duration",
        type=float,
        default=0.8,
        help="Minimum duration per reflowed cue when possible (default: 0.8)",
    )
    parser.add_argument(
        "--disable-timing-polish",
        action="store_true",
        help="Skip the timing polish pass after target-language reflow",
    )
    parser.add_argument(
        "--subtitle-min-gap",
        type=float,
        default=0.08,
        help="Preferred minimum gap between final subtitle cues (default: 0.08)",
    )
    parser.add_argument(
        "--disable-rebalance",
        action="store_true",
        help="Skip source-segment rebalancing before translation",
    )
    parser.add_argument(
        "--rebalance-min-duration",
        type=float,
        default=0.9,
        help="Preferred minimum subtitle cue duration for rebalancing (default: 0.9)",
    )
    parser.add_argument(
        "--rebalance-max-duration",
        type=float,
        default=5.2,
        help="Preferred maximum subtitle cue duration for rebalancing (default: 5.2)",
    )
    parser.add_argument(
        "--rebalance-max-chars",
        type=int,
        default=24,
        help="Preferred maximum source cue character count for rebalancing (default: 24)",
    )
    parser.add_argument(
        "--rebalance-min-chars",
        type=int,
        default=4,
        help="Treat shorter source cues as merge candidates during rebalancing (default: 4)",
    )
    parser.add_argument(
        "--rebalance-hard-gap",
        type=float,
        default=0.8,
        help="Force a source cue boundary when a word gap exceeds this value (default: 0.8)",
    )
    parser.add_argument(
        "--rebalance-merge-gap",
        type=float,
        default=0.35,
        help="Allow merging adjacent source cues only when the inter-cue gap is at or below this value (default: 0.35)",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip subtitle linting",
    )
    parser.add_argument(
        "--subtitle-max-line-length",
        type=int,
        default=42,
        help="Soft-wrap exported subtitle lines at this length (default: 42)",
    )
    parser.add_argument(
        "--subtitle-max-lines",
        type=int,
        default=0,
        help="Soft target for exported wrapped lines. Export keeps all wrapped lines. 0 means unlimited.",
    )
    parser.add_argument(
        "--subtitle-punctuation-mode",
        choices=("preserve", "minimal"),
        default="minimal",
        help="How aggressively to simplify exported subtitle punctuation (default: minimal)",
    )
    parser.add_argument(
        "--disable-semantic-repair",
        action="store_true",
        help="Skip the semantic repair pass before translation",
    )
    parser.add_argument(
        "--semantic-repair-model",
        default="",
        help="Model override for the semantic repair pass",
    )
    parser.add_argument(
        "--semantic-repair-merge-gap",
        type=float,
        default=0.45,
        help="Allow semantic merge when the inter-cue gap is at or below this value (default: 0.45)",
    )
    parser.add_argument(
        "--semantic-repair-max-merge-duration",
        type=float,
        default=6.0,
        help="Do not merge semantic repair cues past this combined duration (default: 6.0)",
    )
    parser.add_argument(
        "--semantic-repair-enable-model-rewrite",
        action="store_true",
        help="Enable the slower model-based semantic repair rewrite on top of rule-based repair",
    )
    return parser.parse_args()


def slugify(text):
    value = "".join(char.lower() if char.isalnum() else "-" for char in text.strip())
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-") or "target"


def run_json_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")
    return json.loads(result.stdout)


def main():
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = args.output_stem or input_path.stem
    target_code = args.target_code or slugify(args.target_language)
    work_dir = output_dir / f"{output_stem}.work"
    work_dir.mkdir(parents=True, exist_ok=True)

    extracted_audio = work_dir / f"{output_stem}.funasr.wav"
    source_segments = work_dir / f"{output_stem}.source.segments.json"
    working_source_segments = source_segments
    raw_translated_segments = work_dir / f"{output_stem}.{target_code}.translated.segments.json"
    reflowed_target_segments = work_dir / f"{output_stem}.{target_code}.reflow.segments.json"
    translated_segments = work_dir / f"{output_stem}.{target_code}.segments.json"

    extract_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "extract_audio.py"),
        str(input_path),
        str(extracted_audio),
        "--audio-stream",
        str(args.audio_stream),
    ]
    extract_info = run_json_command(extract_cmd)

    transcribe_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "funasr_transcribe.py"),
        str(extracted_audio),
        str(source_segments),
    ]
    if args.asr_model:
        transcribe_cmd.extend(["--model", args.asr_model])
    if args.asr_language_hint:
        transcribe_cmd.extend(["--language-hint", args.asr_language_hint])
    if args.semantic_punctuation_enabled is True:
        transcribe_cmd.append("--semantic-punctuation-enabled")
    elif args.semantic_punctuation_enabled is False:
        transcribe_cmd.append("--disable-semantic-punctuation")
    if args.max_sentence_silence is not None:
        transcribe_cmd.extend(["--max-sentence-silence", str(args.max_sentence_silence)])
    if args.multi_threshold_mode_enabled:
        transcribe_cmd.append("--multi-threshold-mode-enabled")
    if args.speech_noise_threshold is not None:
        transcribe_cmd.extend(["--speech-noise-threshold", str(args.speech_noise_threshold)])
    asr_info = run_json_command(transcribe_cmd)

    rebalance_info = None
    if not args.disable_rebalance:
        rebalanced_source_segments = work_dir / f"{output_stem}.source.rebalanced.segments.json"
        rebalance_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "rebalance_segments.py"),
            str(source_segments),
            str(rebalanced_source_segments),
            "--min-duration",
            str(args.rebalance_min_duration),
            "--max-duration",
            str(args.rebalance_max_duration),
            "--max-chars",
            str(args.rebalance_max_chars),
            "--min-chars",
            str(args.rebalance_min_chars),
            "--hard-gap",
            str(args.rebalance_hard_gap),
            "--merge-gap",
            str(args.rebalance_merge_gap),
        ]
        rebalance_info = run_json_command(rebalance_cmd)
        working_source_segments = rebalanced_source_segments

    semantic_repair_info = None
    if not args.disable_semantic_repair:
        semantic_source_segments = work_dir / f"{output_stem}.source.semantic.segments.json"
        semantic_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "semantic_repair_segments.py"),
            str(working_source_segments),
            str(semantic_source_segments),
            "--merge-gap",
            str(args.semantic_repair_merge_gap),
            "--max-merge-duration",
            str(args.semantic_repair_max_merge_duration),
        ]
        if args.source_language:
            semantic_cmd.extend(["--source-language", args.source_language])
        if args.semantic_repair_model:
            semantic_cmd.extend(["--model", args.semantic_repair_model])
        if not args.semantic_repair_enable_model_rewrite:
            semantic_cmd.append("--disable-model-rewrite")
        semantic_repair_info = run_json_command(semantic_cmd)
        working_source_segments = semantic_source_segments

    translate_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "translate_segments.py"),
        str(working_source_segments),
        str(raw_translated_segments),
        "--target-language",
        args.target_language,
    ]
    if args.target_locale:
        translate_cmd.extend(["--target-locale", args.target_locale])
    if args.source_language:
        translate_cmd.extend(["--source-language", args.source_language])
    if args.translation_model:
        translate_cmd.extend(["--model", args.translation_model])
    translation_info = run_json_command(translate_cmd)

    reflow_info = None
    final_target_segments = raw_translated_segments
    if args.enable_target_reflow:
        reflow_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "reflow_translated_segments.py"),
            str(raw_translated_segments),
            str(reflowed_target_segments),
            "--max-chars",
            str(args.target_max_line_chars),
            "--max-cjk-chars",
            str(args.target_max_cjk_line_chars),
            "--max-cps",
            str(args.target_max_cps),
            "--min-duration",
            str(args.target_min_duration),
            "--min-gap",
            str(args.subtitle_min_gap),
        ]
        reflow_info = run_json_command(reflow_cmd)
        final_target_segments = reflowed_target_segments

    timing_polish_info = None
    if not args.disable_timing_polish:
        polished_target_segments = translated_segments
        timing_polish_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "polish_segment_timing.py"),
            str(final_target_segments),
            str(polished_target_segments),
            "--min-duration",
            str(args.target_min_duration),
            "--min-gap",
            str(args.subtitle_min_gap),
        ]
        timing_polish_info = run_json_command(timing_polish_cmd)
        final_target_segments = polished_target_segments

    outputs = {}
    lint_results = {}
    for subtitle_format in [item.strip() for item in args.formats.split(",") if item.strip()]:
        if subtitle_format not in {"srt", "vtt"}:
            raise RuntimeError(f"Unsupported format: {subtitle_format}")
        subtitle_path = output_dir / f"{output_stem}.{target_code}.{subtitle_format}"
        export_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "segments_to_subtitles.py"),
            str(final_target_segments),
            str(subtitle_path),
            "--format",
            subtitle_format,
            "--max-line-length",
            str(args.subtitle_max_line_length),
            "--max-lines",
            str(args.subtitle_max_lines),
            "--punctuation-mode",
            args.subtitle_punctuation_mode,
        ]
        run_json_command(export_cmd)
        outputs[subtitle_format] = str(subtitle_path)

        if not args.skip_lint:
            lint_cmd = [
                sys.executable,
                str(SCRIPT_DIR / "lint_subtitles.py"),
                str(subtitle_path),
                "--json",
            ]
            lint_results[subtitle_format] = run_json_command(lint_cmd)

    summary = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "work_dir": str(work_dir),
        "target_language": args.target_language,
        "target_locale": args.target_locale or None,
        "audio": extract_info,
        "asr": {
            "model": asr_info.get("model"),
            "request_id": asr_info.get("request_id"),
            "segments": len(asr_info.get("segments") or []),
            "segmentation": asr_info.get("segmentation"),
            "source_segments_json": str(source_segments),
        },
        "rebalance": {
            "enabled": not args.disable_rebalance,
            "input_segments": rebalance_info.get("rebalanced", {}).get("input_segments")
            if rebalance_info
            else None,
            "output_segments": rebalance_info.get("rebalanced", {}).get("output_segments")
            if rebalance_info
            else None,
            "source_segments_json": str(working_source_segments),
            "settings": rebalance_info.get("rebalanced") if rebalance_info else None,
        },
        "semantic_repair": {
            "enabled": not args.disable_semantic_repair,
            "input_segments": semantic_repair_info.get("semantic_repair", {}).get("input_segments")
            if semantic_repair_info
            else None,
            "output_segments": semantic_repair_info.get("semantic_repair", {}).get("output_segments")
            if semantic_repair_info
            else None,
            "source_segments_json": str(working_source_segments),
            "settings": semantic_repair_info.get("semantic_repair") if semantic_repair_info else None,
            "model_rewrite_enabled": args.semantic_repair_enable_model_rewrite,
        },
        "translation": {
            "model": translation_info.get("translation", {}).get("model"),
            "raw_translated_segments_json": str(raw_translated_segments),
            "translated_segments_json": str(final_target_segments),
        },
        "export": {
            "subtitle_max_line_length": args.subtitle_max_line_length,
            "subtitle_max_lines": args.subtitle_max_lines,
            "subtitle_punctuation_mode": args.subtitle_punctuation_mode,
        },
        "reflow": {
            "enabled": args.enable_target_reflow,
            "input_segments": reflow_info.get("reflow", {}).get("input_segments")
            if reflow_info
            else None,
            "output_segments": reflow_info.get("reflow", {}).get("output_segments")
            if reflow_info
            else None,
            "settings": reflow_info.get("reflow") if reflow_info else None,
        },
        "timing_polish": {
            "enabled": not args.disable_timing_polish,
            "input_segments": timing_polish_info.get("timing_polish", {}).get("input_segments")
            if timing_polish_info
            else None,
            "output_segments": timing_polish_info.get("timing_polish", {}).get("output_segments")
            if timing_polish_info
            else None,
            "settings": timing_polish_info.get("timing_polish") if timing_polish_info else None,
        },
        "outputs": outputs,
        "lint": lint_results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
