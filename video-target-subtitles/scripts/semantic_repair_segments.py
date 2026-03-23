#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
from pathlib import Path

from env_loader import load_dotenv
from segment_utils import load_segments_document, write_json

load_dotenv()


DASHSCOPE_COMPAT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CONTINUATION_PREFIXES = (
    "而",
    "并",
    "但",
    "但是",
    "不过",
    "可是",
    "所以",
    "因为",
    "如果",
    "然后",
    "还有",
    "要不",
    "并且",
    "以及",
    "又",
    "也",
    "那",
    "这",
    "昨天",
)
FRAGMENT_PATTERNS = (
    "而是",
    "别",
    "昨天",
    "是呀",
    "还有",
    "以及",
    "有",
)
WEAK_ENDINGS = ("，", "、", ",", "：", ":", "…", "——")
TERMINAL_PUNCTUATION = ("。", "！", "？", "!", "?", ".", ";", "；")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Repair source-language subtitle cues with heuristic merging and optional model-based polishing.",
    )
    parser.add_argument("input_json", help="Input segments JSON")
    parser.add_argument("output_json", help="Output repaired segments JSON")
    parser.add_argument(
        "--source-language",
        default="Chinese",
        help="Language of the source transcript (default: Chinese)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get(
            "SUBTITLE_SEMANTIC_REPAIR_MODEL",
            os.environ.get("SUBTITLE_TRANSLATION_MODEL", os.environ.get("OPENAI_MODEL", "")),
        ),
        help="OpenAI-compatible model used for semantic repair",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "SUBTITLE_SEMANTIC_REPAIR_BASE_URL",
            os.environ.get(
                "SUBTITLE_TRANSLATION_BASE_URL",
                os.environ.get("OPENAI_BASE_URL", ""),
            ),
        ),
        help="OpenAI-compatible base URL override",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=18,
        help="Number of cues per semantic repair batch (default: 18)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Model temperature (default: 0.2)",
    )
    parser.add_argument(
        "--merge-gap",
        type=float,
        default=0.45,
        help="Allow semantic merge when the cue gap is at or below this value (default: 0.45)",
    )
    parser.add_argument(
        "--max-merge-duration",
        type=float,
        default=6.0,
        help="Do not merge cues past this combined duration (default: 6.0)",
    )
    parser.add_argument(
        "--disable-model-rewrite",
        action="store_true",
        help="Only apply heuristic merging and skip the model rewrite pass",
    )
    parser.add_argument(
        "--context-radius",
        type=int,
        default=1,
        help="Include this many neighboring cues on each side of a problematic cue during model rewrite (default: 1)",
    )
    return parser.parse_args()


def visual_length(text):
    return sum(1 for char in text if not char.isspace())


def strip_closing_punctuation(text):
    return text.strip().rstrip("。！？!?,，、；;：:…—\"'”’)]）")


def has_terminal_punctuation(text):
    stripped = text.strip()
    return stripped.endswith(TERMINAL_PUNCTUATION)


def matches_fragment_pattern(text):
    stripped = strip_closing_punctuation(text)
    return any(
        stripped == pattern or stripped.endswith(pattern)
        for pattern in FRAGMENT_PATTERNS
    )


def is_weak_ending(text):
    stripped = text.strip()
    return stripped.endswith(WEAK_ENDINGS) or matches_fragment_pattern(stripped)


def starts_with_continuation(text):
    stripped = text.strip().lstrip("“\"'(")
    return any(stripped.startswith(prefix) for prefix in CONTINUATION_PREFIXES)


def is_semantically_incomplete(text):
    stripped = str(text).strip()
    if not stripped:
        return False
    if matches_fragment_pattern(stripped):
        return True
    if stripped.endswith(WEAK_ENDINGS):
        return True
    if starts_with_continuation(stripped) and not has_terminal_punctuation(stripped):
        return True
    return False


def should_merge(left, right, merge_gap, max_merge_duration):
    gap = float(right["start"]) - float(left["end"])
    if gap > merge_gap:
        return False

    left_text = str(left.get("text", "")).strip()
    right_text = str(right.get("text", "")).strip()
    combined_duration = float(right["end"]) - float(left["start"])
    if combined_duration > max_merge_duration:
        return False

    if is_semantically_incomplete(left_text):
        return True
    if starts_with_continuation(right_text):
        return True
    if is_weak_ending(left_text):
        return True
    return False


def merge_pair(left, right):
    merged_words = []
    merged_words.extend(left.get("words") or [])
    merged_words.extend(right.get("words") or [])
    merged_text = f"{left['text']}{right['text']}".strip()
    return {
        "id": left["id"],
        "start": left["start"],
        "end": right["end"],
        "text": merged_text,
        "source_text": merged_text,
        "asr_text": f"{left.get('asr_text', left['text'])}{right.get('asr_text', right['text'])}",
        "words": merged_words,
    }


def heuristic_merge(document, merge_gap, max_merge_duration):
    merged = []
    for segment in document["segments"]:
        current = dict(segment)
        current.setdefault("asr_text", current.get("text", ""))
        current.setdefault("source_text", current.get("text", ""))
        if not merged:
            merged.append(current)
            continue

        previous = merged[-1]
        if should_merge(previous, current, merge_gap=merge_gap, max_merge_duration=max_merge_duration):
            merged[-1] = merge_pair(previous, current)
        else:
            merged.append(current)

    for index, segment in enumerate(merged, start=1):
        segment["id"] = index
    return merged


def resolve_api_key_and_base_url(base_url):
    if os.environ.get("SUBTITLE_SEMANTIC_REPAIR_API_KEY"):
        return os.environ["SUBTITLE_SEMANTIC_REPAIR_API_KEY"], base_url or None, "semantic"
    if os.environ.get("SUBTITLE_TRANSLATION_API_KEY"):
        return os.environ["SUBTITLE_TRANSLATION_API_KEY"], base_url or None, "translation"
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], base_url or None, "openai"
    if os.environ.get("DASHSCOPE_API_KEY"):
        return os.environ["DASHSCOPE_API_KEY"], base_url or DASHSCOPE_COMPAT_BASE_URL, "dashscope"
    raise RuntimeError(
        "No semantic repair API key found. Set SUBTITLE_SEMANTIC_REPAIR_API_KEY, "
        "SUBTITLE_TRANSLATION_API_KEY, OPENAI_API_KEY, or DASHSCOPE_API_KEY."
    )


def resolve_model(model, source):
    if model:
        return model
    if source == "dashscope":
        return "qwen3.5-flash-2026-02-23"
    raise RuntimeError(
        "No semantic repair model configured. Set SUBTITLE_SEMANTIC_REPAIR_MODEL, "
        "SUBTITLE_TRANSLATION_MODEL, or OPENAI_MODEL."
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


def build_messages(batch, source_language):
    prompt_payload = {
        "source_language": source_language,
        "segments": [
            {
                "id": segment["id"],
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            for segment in batch
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "Repair ASR-derived subtitle source cues before translation. "
                "Return JSON only. Keep the same cue IDs and order. "
                "Lightly repair broken phrasing, dangling fragments, and obvious "
                "omissions that are strongly implied by adjacent cues. "
                "Keep the wording concise, natural, and faithful to the audio. "
                "Do not add plot details or names not supported by context. "
                "Do not return empty strings."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(prompt_payload, ensure_ascii=False),
        },
    ]


def model_rewrite(client, model, segments, source_language, batch_size, temperature):
    repaired = {segment["id"]: segment["text"] for segment in segments}
    for start_index in range(0, len(segments), batch_size):
        batch = segments[start_index : start_index + batch_size]
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=build_messages(batch, source_language),
        )
        content = get_content_text(response.choices[0].message)
        payload = extract_json_value(content)
        items = payload.get("segments") or payload.get("repairs")
        if not isinstance(items, list):
            raise ValueError("Semantic repair response must include a segments list")
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            repaired[int(item["id"])] = str(item.get("text", "")).strip() or repaired[int(item["id"])]
    return repaired


def is_problematic_segment(segment):
    text = str(segment.get("text", "")).strip()
    if not text:
        return False
    if is_semantically_incomplete(text):
        return True
    if starts_with_continuation(text):
        return True
    return False


def build_rewrite_windows(segments, context_radius):
    problem_indexes = {
        index
        for index, segment in enumerate(segments)
        if is_problematic_segment(segment)
    }
    if not problem_indexes:
        return []

    expanded = set()
    for index in problem_indexes:
        start = max(0, index - context_radius)
        end = min(len(segments), index + context_radius + 1)
        expanded.update(range(start, end))

    windows = []
    sorted_indexes = sorted(expanded)
    window = [sorted_indexes[0]]
    for index in sorted_indexes[1:]:
        if index == window[-1] + 1:
            window.append(index)
        else:
            windows.append(window)
            window = [index]
    windows.append(window)
    return [[segments[index] for index in window] for window in windows]


def cleanup_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("。。", "。")
    text = text.replace("，，", "，")
    return text.strip()


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()
    document = load_segments_document(input_path)

    merged_segments = heuristic_merge(
        document,
        merge_gap=args.merge_gap,
        max_merge_duration=args.max_merge_duration,
    )

    model_name = None
    resolved_base_url = None
    if not args.disable_model_rewrite:
        try:
            api_key, resolved_base_url, source = resolve_api_key_and_base_url(args.base_url)
            model_name = resolve_model(args.model, source)
            from openai import OpenAI
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

        client_kwargs = {"api_key": api_key}
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        client = OpenAI(**client_kwargs)
        windows = build_rewrite_windows(merged_segments, context_radius=args.context_radius)
        repaired_lookup = {segment["id"]: segment["text"] for segment in merged_segments}
        for window in windows:
            repaired_lookup.update(
                model_rewrite(
                    client,
                    model=model_name,
                    segments=window,
                    source_language=args.source_language,
                    batch_size=args.batch_size,
                    temperature=args.temperature,
                )
            )
        for segment in merged_segments:
            segment["source_text"] = segment["text"]
            segment["text"] = cleanup_text(repaired_lookup.get(segment["id"], segment["text"]))
    else:
        for segment in merged_segments:
            segment["source_text"] = segment["text"]
            segment["text"] = cleanup_text(segment["text"])

    output = dict(document)
    output["segments"] = merged_segments
    output["semantic_repair"] = {
        "merge_gap": args.merge_gap,
        "max_merge_duration": args.max_merge_duration,
        "input_segments": len(document["segments"]),
        "output_segments": len(merged_segments),
        "model_enabled": not args.disable_model_rewrite,
        "model": model_name,
        "base_url": resolved_base_url,
        "source_language": args.source_language,
        "context_radius": args.context_radius,
    }
    write_json(output_path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
