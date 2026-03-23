#!/usr/bin/env python3

import argparse
import json
import os
import sys
from http import HTTPStatus
from pathlib import Path

from env_loader import load_dotenv
from segment_utils import write_json

load_dotenv()


DEFAULT_WS_URLS = {
    "cn": "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
    "intl": "wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference",
}

FORMAT_BY_SUFFIX = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".opus": "opus",
    ".ogg": "opus",
    ".spx": "speex",
    ".speex": "speex",
    ".aac": "aac",
    ".amr": "amr",
    ".pcm": "pcm",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Transcribe local audio with DashScope FunASR and emit normalized segments JSON.",
    )
    parser.add_argument("input_audio", help="Input audio file")
    parser.add_argument("output_json", help="Output segments JSON")
    parser.add_argument(
        "--model",
        default=os.environ.get("FUNASR_MODEL", "fun-asr-realtime"),
        help="FunASR model name (default: FUNASR_MODEL or fun-asr-realtime)",
    )
    parser.add_argument(
        "--format",
        default="",
        help="Audio format override (wav, mp3, opus, speex, aac, amr, pcm)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Audio sample rate in Hz (default: 16000)",
    )
    parser.add_argument(
        "--region",
        choices=("cn", "intl"),
        default=os.environ.get("DASHSCOPE_REGION", "cn"),
        help="DashScope region for the websocket endpoint (default: cn)",
    )
    parser.add_argument(
        "--websocket-url",
        default=os.environ.get("DASHSCOPE_BASE_WEBSOCKET_API_URL", ""),
        help="Override websocket endpoint URL",
    )
    parser.add_argument(
        "--language-hint",
        default=os.environ.get("FUNASR_LANGUAGE_HINT", ""),
        help="Optional language hint such as zh, en, or ja",
    )
    parser.add_argument(
        "--vocabulary-id",
        default=os.environ.get("FUNASR_VOCABULARY_ID", ""),
        help="Optional DashScope hotword vocabulary ID",
    )
    parser.add_argument(
        "--semantic-punctuation-enabled",
        dest="semantic_punctuation_enabled",
        action="store_true",
        help="Enable semantic sentence segmentation",
    )
    parser.add_argument(
        "--disable-semantic-punctuation",
        dest="semantic_punctuation_enabled",
        action="store_false",
        help="Use VAD sentence segmentation instead of semantic segmentation",
    )
    parser.set_defaults(semantic_punctuation_enabled=True)
    parser.add_argument(
        "--max-sentence-silence",
        type=int,
        default=1300,
        help="VAD silence threshold in ms when semantic punctuation is disabled",
    )
    parser.add_argument(
        "--multi-threshold-mode-enabled",
        action="store_true",
        help="Enable the FunASR multi-threshold mode",
    )
    parser.add_argument(
        "--speech-noise-threshold",
        type=float,
        help="Optional VAD sensitivity override in [-1.0, 1.0]",
    )
    return parser.parse_args()


def resolve_format(path, override):
    if override:
        return override
    suffix = path.suffix.lower()
    if suffix in FORMAT_BY_SUFFIX:
        return FORMAT_BY_SUFFIX[suffix]
    raise ValueError(
        f"Could not infer the audio format from {path.name}. Pass --format explicitly."
    )


def resolve_api_key():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        return api_key
    raise RuntimeError("DASHSCOPE_API_KEY is not set")


def resolve_websocket_url(args):
    if args.websocket_url:
        return args.websocket_url
    return DEFAULT_WS_URLS[args.region]


def normalize_sentences(sentences):
    if isinstance(sentences, dict):
        sentences = [sentences]
    if not isinstance(sentences, list):
        raise ValueError("Recognition result did not return a sentence list")

    normalized = []
    for index, sentence in enumerate(sentences, start=1):
        if not isinstance(sentence, dict):
            continue
        text = str(sentence.get("text", "")).strip()
        if not text:
            continue
        begin_ms = int(sentence.get("begin_time", 0))
        end_ms = int(sentence.get("end_time", begin_ms))
        words = []
        for word in sentence.get("words") or []:
            if not isinstance(word, dict):
                continue
            words.append(
                {
                    "text": str(word.get("text", "")),
                    "punctuation": str(word.get("punctuation", "")),
                    "start": int(word.get("begin_time", 0)) / 1000.0,
                    "end": int(word.get("end_time", word.get("begin_time", 0))) / 1000.0,
                }
            )
        normalized.append(
            {
                "id": index,
                "start": begin_ms / 1000.0,
                "end": end_ms / 1000.0,
                "text": text,
                "source_text": text,
                "words": words,
            }
        )
    return normalized


def main():
    args = parse_args()
    input_path = Path(args.input_audio).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()

    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    try:
        audio_format = resolve_format(input_path, args.format)
        api_key = resolve_api_key()
        websocket_url = resolve_websocket_url(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        import dashscope
        from dashscope.audio.asr import Recognition
    except ImportError:
        print(
            "dashscope is not installed. Install it with `uv pip install dashscope` or "
            "run the script via `uv run --with dashscope python ...`.",
            file=sys.stderr,
        )
        return 1

    dashscope.api_key = api_key
    dashscope.base_websocket_api_url = websocket_url

    kwargs = {
        "model": args.model,
        "format": audio_format,
        "sample_rate": args.sample_rate,
        "semantic_punctuation_enabled": args.semantic_punctuation_enabled,
        "callback": None,
    }
    if args.language_hint:
        kwargs["language_hints"] = [args.language_hint]
    if args.vocabulary_id:
        kwargs["vocabulary_id"] = args.vocabulary_id
    if not args.semantic_punctuation_enabled:
        kwargs["max_sentence_silence"] = args.max_sentence_silence
        if args.multi_threshold_mode_enabled:
            kwargs["multi_threshold_mode_enabled"] = True
    if args.speech_noise_threshold is not None:
        kwargs["speech_noise_threshold"] = args.speech_noise_threshold

    recognition = Recognition(**kwargs)
    result = recognition.call(str(input_path))
    if result.status_code != HTTPStatus.OK:
        print(result.message, file=sys.stderr)
        return 1

    segments = normalize_sentences(result.get_sentence())
    payload = {
        "provider": "dashscope-funasr",
        "input": str(input_path),
        "model": args.model,
        "format": audio_format,
        "sample_rate": args.sample_rate,
        "region": args.region,
        "websocket_url": websocket_url,
        "request_id": recognition.get_last_request_id(),
        "language_hint": args.language_hint or None,
        "segmentation": {
            "semantic_punctuation_enabled": args.semantic_punctuation_enabled,
            "max_sentence_silence": (
                args.max_sentence_silence if not args.semantic_punctuation_enabled else None
            ),
            "multi_threshold_mode_enabled": (
                args.multi_threshold_mode_enabled if not args.semantic_punctuation_enabled else None
            ),
            "speech_noise_threshold": args.speech_noise_threshold,
        },
        "segments": segments,
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
