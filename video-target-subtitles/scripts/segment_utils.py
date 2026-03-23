#!/usr/bin/env python3

import json
from pathlib import Path


def load_segments_document(path):
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, list):
        payload = {"segments": payload}

    if not isinstance(payload, dict):
        raise ValueError("Segment document must be a JSON object or list")

    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise ValueError("Segment document must contain a segments list")

    normalized_segments = []
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            raise ValueError(f"Segment {index} must be an object")
        if "start" not in segment or "end" not in segment:
            raise ValueError(f"Segment {index} must contain start and end")
        normalized = dict(segment)
        normalized["start"] = float(segment["start"])
        normalized["end"] = float(segment["end"])
        normalized["text"] = str(segment.get("text", ""))
        normalized.setdefault("id", index)
        normalized_segments.append(normalized)

    payload["segments"] = normalized_segments
    return payload


def write_json(path, payload):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

