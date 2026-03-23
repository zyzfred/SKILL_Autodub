#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

from env_loader import load_dotenv
from segment_utils import load_segments_document, write_json

load_dotenv()


DASHSCOPE_COMPAT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Translate normalized segments while preserving timestamps.",
    )
    parser.add_argument("input_json", help="Input segments JSON")
    parser.add_argument("output_json", help="Output translated segments JSON")
    parser.add_argument(
        "--target-language",
        required=True,
        help="Target language, for example English or Japanese",
    )
    parser.add_argument(
        "--target-locale",
        default="",
        help="Optional locale hint, for example en-US or ja-JP",
    )
    parser.add_argument(
        "--source-language",
        default="",
        help="Optional source language hint",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("SUBTITLE_TRANSLATION_MODEL", os.environ.get("OPENAI_MODEL", "")),
        help="Translation model name",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "SUBTITLE_TRANSLATION_BASE_URL",
            os.environ.get("OPENAI_BASE_URL", ""),
        ),
        help="OpenAI-compatible base URL override",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=40,
        help="Number of subtitle cues to translate per request (default: 40)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Model temperature (default: 0.2)",
    )
    return parser.parse_args()


def resolve_api_key_and_base_url(base_url):
    if os.environ.get("SUBTITLE_TRANSLATION_API_KEY"):
        return os.environ["SUBTITLE_TRANSLATION_API_KEY"], base_url or None
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], base_url or None
    if os.environ.get("DASHSCOPE_API_KEY"):
        return os.environ["DASHSCOPE_API_KEY"], base_url or DASHSCOPE_COMPAT_BASE_URL
    raise RuntimeError(
        "No translation API key found. Set SUBTITLE_TRANSLATION_API_KEY, OPENAI_API_KEY, or DASHSCOPE_API_KEY."
    )


def resolve_model(model, api_key_source):
    if model:
        return model
    if api_key_source == "dashscope":
        return "qwen-plus"
    raise RuntimeError(
        "No translation model configured. Set SUBTITLE_TRANSLATION_MODEL or OPENAI_MODEL."
    )


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


def build_messages(batch, args):
    prompt_payload = {
        "target_language": args.target_language,
        "target_locale": args.target_locale or None,
        "source_language": args.source_language or None,
        "segments": [
            {
                "id": segment["id"],
                "text": segment["text"],
            }
            for segment in batch
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "Translate subtitle cues into the requested target language. "
                "Return JSON only. Preserve the order and IDs. "
                "Do not include timestamps in the response. "
                "Optimize for subtitle readability rather than literal translation. "
                "Keep phrasing compact and screen-readable. "
                "Prefer minimal punctuation: omit periods and commas unless they are necessary. "
                "Preserve question marks or exclamation marks only when they reflect strong tone. "
                "Do not insert hard line breaks."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(prompt_payload, ensure_ascii=False),
        },
    ]


def translate_batch(client, model, batch, args):
    response = client.chat.completions.create(
        model=model,
        temperature=args.temperature,
        messages=build_messages(batch, args),
    )
    content = get_content_text(response.choices[0].message)
    payload = extract_json_value(content)
    if isinstance(payload, list):
        translations = payload
    elif isinstance(payload, dict):
        translations = payload.get("translations") or payload.get("segments")
    else:
        translations = None
    if not isinstance(translations, list):
        raise ValueError("Model response must include a translations or segments list")

    translated_by_id = {}
    for item in translations:
        if not isinstance(item, dict) or "id" not in item:
            continue
        translated_by_id[int(item["id"])] = str(item.get("text", "")).strip()

    missing_ids = [segment["id"] for segment in batch if segment["id"] not in translated_by_id]
    if missing_ids:
        raise ValueError(f"Model response is missing IDs: {missing_ids}")

    return translated_by_id


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    try:
        document = load_segments_document(input_path)
        base_url = args.base_url
        api_key_source = (
            "subtitle"
            if os.environ.get("SUBTITLE_TRANSLATION_API_KEY")
            else "openai"
            if os.environ.get("OPENAI_API_KEY")
            else "dashscope"
            if os.environ.get("DASHSCOPE_API_KEY")
            else ""
        )
        api_key, resolved_base_url = resolve_api_key_and_base_url(base_url)
        model = resolve_model(args.model, api_key_source)
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

    client_kwargs = {"api_key": api_key}
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url
    client = OpenAI(**client_kwargs)

    translated_segments = []
    non_empty_segments = [segment for segment in document["segments"] if segment["text"].strip()]
    translated_lookup = {}
    for start_index in range(0, len(non_empty_segments), args.batch_size):
        batch = non_empty_segments[start_index : start_index + args.batch_size]
        translated_lookup.update(translate_batch(client, model, batch, args))

    for segment in document["segments"]:
        translated = dict(segment)
        source_text = str(segment.get("source_text", segment["text"]))
        translated["source_text"] = source_text
        translated["text"] = translated_lookup.get(segment["id"], segment["text"])
        translated_segments.append(translated)

    output_payload = dict(document)
    output_payload["translation"] = {
        "provider": "openai-compatible",
        "model": model,
        "base_url": resolved_base_url,
        "target_language": args.target_language,
        "target_locale": args.target_locale or None,
        "source_language": args.source_language or None,
    }
    output_payload["segments"] = translated_segments
    write_json(output_path, output_payload)
    print(json.dumps(output_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
