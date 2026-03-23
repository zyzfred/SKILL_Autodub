#!/usr/bin/env python3

import argparse
import json
import string
from pathlib import Path

from segment_utils import load_segments_document, write_json


STRONG_PUNCTUATION = set("。！？!?；;")
SOFT_PUNCTUATION = set("，、,:：")
ASCII_WORD_CHARS = set(string.ascii_letters + string.digits)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rebalance subtitle segments by splitting long cues using word timestamps.",
    )
    parser.add_argument("input_json", help="Input segments JSON")
    parser.add_argument("output_json", help="Output segments JSON")
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.9,
        help="Prefer cues at or above this duration in seconds (default: 0.9)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=5.2,
        help="Try to keep cues at or below this duration in seconds (default: 5.2)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=24,
        help="Try to keep source cue text at or below this character count (default: 24)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=4,
        help="Legacy setting retained for compatibility. Short cues are preserved by default.",
    )
    parser.add_argument(
        "--hard-gap",
        type=float,
        default=0.8,
        help="Force a sentence break when the gap between adjacent words exceeds this value (default: 0.8)",
    )
    parser.add_argument(
        "--merge-gap",
        type=float,
        default=0.35,
        help="Legacy setting retained for compatibility. Source rebalance no longer merges short cues by default.",
    )
    return parser.parse_args()


def visual_length(text):
    return sum(1 for char in text if not char.isspace())


def normalize_word(word):
    return {
        "text": str(word.get("text", "")),
        "punctuation": str(word.get("punctuation", "")),
        "start": float(word.get("start", 0.0)),
        "end": float(word.get("end", word.get("start", 0.0))),
    }


def needs_space(previous_char, current_text):
    if not previous_char or not current_text:
        return False
    return previous_char in ASCII_WORD_CHARS and current_text[0] in ASCII_WORD_CHARS


def tokens_to_text(tokens):
    parts = []
    previous_char = ""
    for token in tokens:
        token_text = token["text"]
        if token_text and needs_space(previous_char, token_text):
            parts.append(" ")
        parts.append(token_text)
        if token["punctuation"]:
            parts.append(token["punctuation"])
            previous_char = token["punctuation"][-1]
        elif token_text:
            previous_char = token_text[-1]
    return "".join(parts).strip()


def make_segment(tokens):
    words = [normalize_word(token) for token in tokens]
    text = tokens_to_text(tokens)
    return {
        "start": tokens[0]["start"],
        "end": tokens[-1]["end"],
        "text": text,
        "source_text": text,
        "words": words,
    }


def split_on_sentence_boundaries(tokens, hard_gap):
    segments = []
    buffer = []
    for index, token in enumerate(tokens):
        buffer.append(token)
        next_token = tokens[index + 1] if index + 1 < len(tokens) else None
        gap_to_next = (
            next_token["start"] - token["end"] if next_token is not None else None
        )
        should_flush = (
            token["punctuation"] in STRONG_PUNCTUATION
            or next_token is None
            or (gap_to_next is not None and gap_to_next >= hard_gap)
        )
        if should_flush:
            segments.append(make_segment(buffer))
            buffer = []
    if buffer:
        segments.append(make_segment(buffer))
    return segments


def recompute_boundary_indexes(tokens):
    strong = None
    soft = None
    for index, token in enumerate(tokens, start=1):
        punctuation = token["punctuation"]
        if punctuation in STRONG_PUNCTUATION:
            strong = index
        elif punctuation in SOFT_PUNCTUATION:
            soft = index
    return strong, soft


def split_long_segment(segment, min_duration, max_duration, max_chars):
    tokens = [normalize_word(word) for word in segment.get("words") or []]
    if not tokens:
        return [segment]

    pieces = []
    buffer = []
    while tokens:
        token = tokens.pop(0)
        buffer.append(token)
        duration = buffer[-1]["end"] - buffer[0]["start"]
        char_count = visual_length(tokens_to_text(buffer))
        over_duration = duration > max_duration
        over_chars = char_count > max_chars
        if not over_duration and not over_chars:
            continue

        strong_boundary, soft_boundary = recompute_boundary_indexes(buffer[:-1])
        split_at = strong_boundary or soft_boundary or max(1, len(buffer) - 1)
        left = buffer[:split_at]
        right = buffer[split_at:]

        if left and (left[-1]["end"] - left[0]["start"]) >= min_duration * 0.6:
            pieces.append(make_segment(left))
            buffer = right
        else:
            pieces.append(make_segment(buffer[:-1]))
            buffer = [buffer[-1]]

    if buffer:
        pieces.append(make_segment(buffer))

    return pieces


def collect_tokens(document):
    tokens = []
    for segment in document["segments"]:
        words = segment.get("words") or []
        if words:
            tokens.extend(normalize_word(word) for word in words if str(word.get("text", "")).strip())
            continue

        text = str(segment.get("source_text", segment.get("text", ""))).strip()
        if not text:
            continue
        tokens.append(
            {
                "text": text,
                "punctuation": "",
                "start": float(segment["start"]),
                "end": float(segment["end"]),
            }
        )
    return tokens


def rebalance(document, min_duration, max_duration, max_chars, min_chars, hard_gap, merge_gap):
    tokens = collect_tokens(document)
    initial_segments = split_on_sentence_boundaries(tokens, hard_gap=hard_gap)

    split_segments = []
    for segment in initial_segments:
        split_segments.extend(
            split_long_segment(
                segment,
                min_duration=min_duration,
                max_duration=max_duration,
                max_chars=max_chars,
            )
        )

    final_segments = []
    for index, segment in enumerate(split_segments, start=1):
        normalized = dict(segment)
        normalized["id"] = index
        normalized["start"] = float(segment["start"])
        normalized["end"] = float(segment["end"])
        normalized["text"] = str(segment["text"]).strip()
        normalized["source_text"] = str(segment.get("source_text", normalized["text"])).strip()
        normalized["words"] = [normalize_word(word) for word in segment.get("words") or []]
        final_segments.append(normalized)

    output = dict(document)
    output["segments"] = final_segments
    output["rebalanced"] = {
        "min_duration": min_duration,
        "max_duration": max_duration,
        "max_chars": max_chars,
        "min_chars": min_chars,
        "hard_gap": hard_gap,
        "merge_gap": merge_gap,
        "merge_short_cues": False,
        "input_segments": len(document["segments"]),
        "output_segments": len(final_segments),
    }
    return output


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()
    document = load_segments_document(input_path)
    output = rebalance(
        document,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        max_chars=args.max_chars,
        min_chars=args.min_chars,
        hard_gap=args.hard_gap,
        merge_gap=args.merge_gap,
    )
    write_json(output_path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
