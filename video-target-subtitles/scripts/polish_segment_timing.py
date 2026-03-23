#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from segment_utils import load_segments_document, write_json


EPSILON = 1e-6


def parse_args():
    parser = argparse.ArgumentParser(
        description="Polish subtitle timings by normalizing gaps and stretching very short cues when space allows.",
    )
    parser.add_argument("input_json", help="Input segments JSON")
    parser.add_argument("output_json", help="Output polished segments JSON")
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.8,
        help="Preferred minimum cue duration in seconds (default: 0.8)",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=0.08,
        help="Preferred minimum gap between adjacent cues in seconds (default: 0.08)",
    )
    return parser.parse_args()


def normalize_segment(segment):
    normalized = dict(segment)
    normalized["start"] = float(segment["start"])
    normalized["end"] = float(segment["end"])
    return normalized


def duration(segment):
    return float(segment["end"]) - float(segment["start"])


def available_left_gap(segments, index, min_gap):
    if index == 0:
        return max(0.0, float(segments[index]["start"]))
    return max(0.0, float(segments[index]["start"]) - float(segments[index - 1]["end"]) - min_gap)


def available_right_gap(segments, index, min_gap):
    if index >= len(segments) - 1:
        return 0.0
    return max(0.0, float(segments[index + 1]["start"]) - float(segments[index]["end"]) - min_gap)


def normalize_gaps(segments, min_duration, min_gap):
    adjusted = 0
    for index in range(len(segments) - 1):
        current = segments[index]
        following = segments[index + 1]
        gap = float(following["start"]) - float(current["end"])
        if gap + EPSILON >= min_gap:
            continue

        needed = min_gap - gap
        shrink_current = max(0.0, duration(current) - min_duration)
        shrink_following = max(0.0, duration(following) - min_duration)

        move_from_current = min(needed / 2.0, shrink_current)
        if move_from_current > EPSILON:
            current["end"] -= move_from_current
            needed -= move_from_current
            adjusted += 1

        move_from_following = min(needed, shrink_following)
        if move_from_following > EPSILON:
            following["start"] += move_from_following
            needed -= move_from_following
            adjusted += 1

        if needed > EPSILON:
            move_from_current = min(needed, max(0.0, duration(current) - min_duration))
            if move_from_current > EPSILON:
                current["end"] -= move_from_current
                adjusted += 1

    return adjusted


def stretch_short_cues(segments, min_duration, min_gap):
    adjusted = 0
    for index, segment in enumerate(segments):
        shortfall = min_duration - duration(segment)
        if shortfall <= EPSILON:
            continue

        right_gap = available_right_gap(segments, index, min_gap)
        left_gap = available_left_gap(segments, index, min_gap)

        take_right = min(shortfall, right_gap)
        if take_right > EPSILON:
            segment["end"] += take_right
            shortfall -= take_right
            adjusted += 1

        take_left = min(shortfall, left_gap)
        if take_left > EPSILON:
            segment["start"] -= take_left
            shortfall -= take_left
            adjusted += 1

        if shortfall > EPSILON and index < len(segments) - 1:
            extra_right = available_right_gap(segments, index, min_gap)
            take_more_right = min(shortfall, extra_right)
            if take_more_right > EPSILON:
                segment["end"] += take_more_right
                adjusted += 1

    return adjusted


def main():
    args = parse_args()
    input_path = Path(args.input_json).expanduser().resolve()
    output_path = Path(args.output_json).expanduser().resolve()
    document = load_segments_document(input_path)

    polished_segments = [normalize_segment(segment) for segment in document["segments"]]
    gap_adjustments = normalize_gaps(polished_segments, args.min_duration, args.min_gap)
    stretch_adjustments = stretch_short_cues(polished_segments, args.min_duration, args.min_gap)
    gap_adjustments += normalize_gaps(polished_segments, args.min_duration, args.min_gap)

    for index, segment in enumerate(polished_segments, start=1):
        segment["id"] = index
        segment["start"] = float(segment["start"])
        segment["end"] = float(segment["end"])

    output = dict(document)
    output["segments"] = polished_segments
    output["timing_polish"] = {
        "min_duration": args.min_duration,
        "min_gap": args.min_gap,
        "input_segments": len(document["segments"]),
        "output_segments": len(polished_segments),
        "gap_adjustments": gap_adjustments,
        "stretch_adjustments": stretch_adjustments,
    }
    write_json(output_path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
