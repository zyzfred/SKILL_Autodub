#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path

from segment_utils import load_segments_document, write_json


HARD_BOUNDARY_RE = re.compile(r"(?:\.\.\.|[.!?。！？；;]+[\"'”’)\]]*)$")
SOFT_BOUNDARY_RE = re.compile(r"(?:[,，、:：]+[\"'”’)\]]*)$")
CJK_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reflow translated subtitle cues into single-line subtitle segments.",
    )
    parser.add_argument("input_json", help="Input translated segments JSON")
    parser.add_argument("output_json", help="Output reflowed segments JSON")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=42,
        help="Preferred single-line character limit for space-delimited languages (default: 42)",
    )
    parser.add_argument(
        "--max-cjk-chars",
        type=int,
        default=22,
        help="Preferred single-line character limit for CJK-heavy cues (default: 22)",
    )
    parser.add_argument(
        "--max-cps",
        type=float,
        default=20.0,
        help="Target maximum reading speed used when deciding whether to split (default: 20.0)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.8,
        help="Minimum duration to keep per reflowed cue when possible (default: 0.8)",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=0.08,
        help="Minimum gap to insert between reflowed cues when duration allows (default: 0.08)",
    )
    return parser.parse_args()


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).strip())


def is_cjk_dominant(text):
    cjk_chars = len(CJK_CHAR_RE.findall(text))
    non_space_chars = sum(1 for char in text if not char.isspace())
    return cjk_chars * 2 >= max(1, non_space_chars)


def visual_length(text):
    return sum(1 for char in text if not char.isspace())


def choose_char_limit(text, args):
    return args.max_cjk_chars if is_cjk_dominant(text) else args.max_chars


def tokenize(text):
    if is_cjk_dominant(text):
        return [char for char in text if not char.isspace()]
    return re.findall(r"\S+\s*", text)


def join_tokens(tokens):
    return "".join(tokens).strip()


def split_long_token(token, limit):
    text = token.strip()
    return [text[index : index + limit] for index in range(0, len(text), limit)]


def choose_split_index(tokens, limit):
    current_length = 0
    last_fit = 0
    best_hard = 0
    best_soft = 0

    for index, token in enumerate(tokens, start=1):
        current_length += len(token)
        if current_length > limit:
            break
        last_fit = index
        stripped = token.rstrip()
        if HARD_BOUNDARY_RE.search(stripped):
            best_hard = index
        elif SOFT_BOUNDARY_RE.search(stripped):
            best_soft = index

    return best_hard or best_soft or last_fit


def split_text_single_line(text, limit):
    normalized = normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= limit:
        return [normalized]

    tokens = tokenize(normalized)
    chunks = []
    while tokens:
        remainder = join_tokens(tokens)
        if len(remainder) <= limit:
            chunks.append(remainder)
            break

        split_at = choose_split_index(tokens, limit)
        if split_at <= 0:
            long_token = tokens.pop(0)
            chunks.extend(split_long_token(long_token, limit))
            continue

        chunk = join_tokens(tokens[:split_at])
        if not chunk:
            long_token = tokens.pop(0)
            chunks.extend(split_long_token(long_token, limit))
            continue

        chunks.append(chunk)
        tokens = tokens[split_at:]

    return [chunk for chunk in chunks if chunk]


def merge_chunks(chunks):
    if len(chunks) <= 1:
        return chunks

    shortest_index = min(range(len(chunks)), key=lambda index: visual_length(chunks[index]))
    if shortest_index == 0:
        merge_index = 1
    elif shortest_index == len(chunks) - 1:
        merge_index = shortest_index - 1
    else:
        left_length = visual_length(chunks[shortest_index - 1] + chunks[shortest_index])
        right_length = visual_length(chunks[shortest_index] + chunks[shortest_index + 1])
        merge_index = shortest_index - 1 if left_length <= right_length else shortest_index

    if merge_index < shortest_index:
        merged = normalize_text(f"{chunks[merge_index]} {chunks[shortest_index]}")
        return chunks[:merge_index] + [merged] + chunks[shortest_index + 1 :]

    merged = normalize_text(f"{chunks[shortest_index]} {chunks[merge_index]}")
    return chunks[:shortest_index] + [merged] + chunks[merge_index + 1 :]


def fit_chunks_to_duration(chunks, duration, min_duration, min_gap):
    fitted = list(chunks)
    while len(fitted) > 1 and duration + 1e-9 < (
        len(fitted) * min_duration + (len(fitted) - 1) * min_gap
    ):
        fitted = merge_chunks(fitted)
    return fitted


def allocate_durations(start, end, texts, min_duration, min_gap):
    if len(texts) == 1:
        return [(start, end)]

    total_duration = end - start
    total_gap = min_gap * (len(texts) - 1)
    weights = [max(1, visual_length(text)) for text in texts]
    base_duration = min_duration * len(texts)
    available_duration = max(0.0, total_duration - total_gap)
    extra_duration = max(0.0, available_duration - base_duration)
    total_weight = sum(weights) or len(texts)

    chunk_durations = [
        min_duration + extra_duration * (weight / total_weight)
        for weight in weights
    ]

    cursor = start
    ranges = []
    for index, duration in enumerate(chunk_durations, start=1):
        chunk_start = cursor
        chunk_end = end if index == len(chunk_durations) else chunk_start + duration
        ranges.append((chunk_start, chunk_end))
        cursor = chunk_end + min_gap

    return ranges


def needs_reflow(segment, args):
    text = normalize_text(segment.get("text", ""))
    if not text:
        return False

    return "\n" in str(segment.get("text", "")) or len(text) > choose_char_limit(text, args)


def reflow_segment(segment, args):
    text = normalize_text(segment.get("text", ""))
    if not text:
        return [dict(segment, text="")]

    limit = choose_char_limit(text, args)
    chunks = split_text_single_line(text, limit)
    duration = float(segment["end"]) - float(segment["start"])
    chunks = fit_chunks_to_duration(
        chunks,
        duration=duration,
        min_duration=args.min_duration,
        min_gap=args.min_gap,
    )
    if len(chunks) <= 1:
        cleaned = dict(segment)
        cleaned["text"] = text
        return [cleaned]

    timing = allocate_durations(
        float(segment["start"]),
        float(segment["end"]),
        chunks,
        min_duration=args.min_duration,
        min_gap=args.min_gap,
    )

    reflowed = []
    for index, (chunk_text, (start, end)) in enumerate(zip(chunks, timing), start=1):
        item = dict(segment)
        item.pop("words", None)
        item["start"] = start
        item["end"] = end
        item["text"] = chunk_text
        item["parent_id"] = segment.get("id")
        item["chunk_index"] = index
        item["chunk_count"] = len(chunks)
        item["timing_source"] = "reflow-proportional"
        reflowed.append(item)
    return reflowed


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()
    document = load_segments_document(input_path)

    reflowed_segments = []
    split_segments = 0
    extra_cues = 0
    for segment in document["segments"]:
        if needs_reflow(segment, args):
            rewritten = reflow_segment(segment, args)
            if len(rewritten) > 1:
                split_segments += 1
                extra_cues += len(rewritten) - 1
            reflowed_segments.extend(rewritten)
        else:
            cleaned = dict(segment)
            cleaned["text"] = normalize_text(cleaned.get("text", ""))
            reflowed_segments.append(cleaned)

    for index, segment in enumerate(reflowed_segments, start=1):
        segment["id"] = index
        segment["start"] = float(segment["start"])
        segment["end"] = float(segment["end"])

    output = dict(document)
    output["segments"] = reflowed_segments
    output["reflow"] = {
        "max_chars": args.max_chars,
        "max_cjk_chars": args.max_cjk_chars,
        "max_cps": args.max_cps,
        "min_duration": args.min_duration,
        "min_gap": args.min_gap,
        "input_segments": len(document["segments"]),
        "output_segments": len(reflowed_segments),
        "split_segments": split_segments,
        "extra_cues": extra_cues,
        "single_line_only": True,
    }
    write_json(output_path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
