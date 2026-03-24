#!/usr/bin/env python3

import json
import math
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
SYSTEM_FONT_DIRS = [
    Path.home() / "Library/Fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
]
NOTO_SANS_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/"
    "NotoSans/NotoSans-Regular.ttf"
)
STYLE_PRESETS = {
    "default-english-burnin": {
        "font_candidates": [
            "Arial",
            "Helvetica",
            "Verdana",
            "Trebuchet MS",
            "Noto Sans",
            "Liberation Sans",
            "Source Sans 3",
            "Inter",
        ],
        "font_size_ratio": 0.05,
        "min_font_size": 36,
        "outline_ratio": 0.004,
        "min_outline": 3.0,
        "margin_v_ratio": 0.06,
        "spacing": 3,
        "shadow_distance": 5,
        "shadow_angle": -45,
    },
    "vertical-short-drama": {
        "font_candidates": [
            "Arial",
            "Helvetica",
            "Verdana",
            "Trebuchet MS",
            "Noto Sans",
        ],
        "font_size_ratio": 0.055,
        "min_font_size": 38,
        "outline_ratio": 0.0045,
        "min_outline": 3.2,
        "margin_v_ratio": 0.08,
        "spacing": 2,
        "shadow_distance": 5,
        "shadow_angle": -45,
    },
    "cinematic-wide": {
        "font_candidates": [
            "Arial",
            "Helvetica",
            "Source Sans 3",
            "Noto Sans",
            "Inter",
        ],
        "font_size_ratio": 0.045,
        "min_font_size": 34,
        "outline_ratio": 0.0035,
        "min_outline": 2.8,
        "margin_v_ratio": 0.055,
        "spacing": 2,
        "shadow_distance": 4,
        "shadow_angle": -45,
    },
}


@dataclass
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def run(command):
    subprocess.run(command, check=True)


def run_output(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_token(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def available_font_files(directory):
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
    )


def detect_system_font(candidates):
    if shutil.which("fc-match"):
        for candidate in candidates:
            result = subprocess.run(
                ["fc-match", candidate],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {
                    "font_name": candidate,
                    "font_source": "system",
                    "font_path": None,
                    "fonts_dir": None,
                }

    normalized_candidates = [(candidate, normalize_token(candidate)) for candidate in candidates]
    for candidate, normalized in normalized_candidates:
        for root in SYSTEM_FONT_DIRS:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() not in FONT_EXTENSIONS:
                    continue
                if normalized in normalize_token(path.stem):
                    return {
                        "font_name": candidate,
                        "font_source": "system",
                        "font_path": str(path),
                        "fonts_dir": str(path.parent),
                    }
    return None


def copy_font_into_package(font_info, fonts_dir):
    font_path = font_info.get("font_path")
    if not font_path:
        return font_info
    source_path = Path(font_path)
    if not source_path.exists():
        return font_info
    ensure_dir(fonts_dir)
    copied_path = fonts_dir / source_path.name
    if source_path.resolve() == copied_path.resolve():
        updated = dict(font_info)
        updated["fonts_dir"] = str(copied_path.parent)
        return updated
    shutil.copy2(source_path, copied_path)
    updated = dict(font_info)
    updated["font_path"] = str(copied_path)
    updated["fonts_dir"] = str(copied_path.parent)
    return updated


def resolve_font_choice(assets_fonts_dir, preset_name, allow_download_fallback=False, download_dir=None):
    preset = STYLE_PRESETS[preset_name]
    asset_font_files = available_font_files(Path(assets_fonts_dir))
    if asset_font_files:
        chosen = asset_font_files[0]
        return {
            "font_name": chosen.stem.replace("_", " ").replace("-", " "),
            "font_source": "asset",
            "font_path": str(chosen),
            "fonts_dir": str(chosen.parent),
            "downloaded": False,
        }

    system_font = detect_system_font(preset["font_candidates"])
    if system_font:
        system_font["downloaded"] = False
        return system_font

    if allow_download_fallback:
        if not download_dir:
            raise RuntimeError("download_dir is required when online fallback fonts are allowed")
        ensure_dir(download_dir)
        target = Path(download_dir) / "NotoSans-Regular.ttf"
        urllib.request.urlretrieve(NOTO_SANS_URL, target)
        return {
            "font_name": "Noto Sans",
            "font_source": "downloaded",
            "font_path": str(target),
            "fonts_dir": str(target.parent),
            "downloaded": True,
        }

    raise RuntimeError(
        "No font resolved from bundled assets or system fonts. Add a bundled font or allow an online fallback download."
    )


def collect_videos(input_dir, include_stems=""):
    allowed = {item.strip() for item in include_stems.split(",") if item.strip()}
    videos = []
    for path in sorted(Path(input_dir).iterdir()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if allowed and path.stem not in allowed:
            continue
        videos.append(path)
    return videos


def probe_resolution(video_path):
    output = run_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(video_path),
        ]
    )
    width, height = output.split("x")
    return int(width), int(height)


def parse_srt_timestamp(raw):
    hours, minutes, rest = raw.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000.0
    )


def format_ass_timestamp(seconds):
    total_cs = round(seconds * 100)
    hours, rem = divmod(total_cs, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def escape_ass_text(text):
    value = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    return value.replace("\n", r"\N")


def parse_srt(path):
    raw = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", raw.strip(), flags=re.MULTILINE)
    cues = []
    for block in blocks:
        lines = [line.rstrip("\r") for line in block.splitlines()]
        if len(lines) < 3:
            continue
        index = int(lines[0].strip())
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->")]
        text = "\n".join(lines[2:])
        cues.append(
            SubtitleCue(
                index=index,
                start=parse_srt_timestamp(start_raw),
                end=parse_srt_timestamp(end_raw),
                text=text,
            )
        )
    return cues


def parse_segments_json(path):
    payload = read_json(path)
    cues = []
    for index, segment in enumerate(payload.get("segments") or [], start=1):
        cues.append(
            SubtitleCue(
                index=index,
                start=float(segment["start"]),
                end=float(segment["end"]),
                text=str(segment["text"]),
            )
        )
    return cues


def load_cues(path):
    path = Path(path)
    if path.suffix.lower() == ".srt":
        return parse_srt(path)
    if path.suffix.lower() == ".json":
        return parse_segments_json(path)
    raise ValueError(f"Unsupported subtitle input for ASS generation: {path}")


def style_values(width, height, preset_name):
    preset = STYLE_PRESETS[preset_name]
    outline = round(max(preset["min_outline"], height * preset["outline_ratio"]), 1)
    shadow_distance = preset["shadow_distance"]
    shadow_angle = preset["shadow_angle"]
    shadow_x = round(math.cos(math.radians(shadow_angle)) * shadow_distance, 2)
    shadow_y = round(math.sin(math.radians(shadow_angle)) * shadow_distance, 2)
    return {
        "preset": preset_name,
        "font_size": max(preset["min_font_size"], round(height * preset["font_size_ratio"])),
        "outline": outline,
        "spacing": preset["spacing"],
        "margin_v": round(height * preset["margin_v_ratio"]),
        "shadow_distance": shadow_distance,
        "shadow_angle": shadow_angle,
        "shadow_x": shadow_x,
        "shadow_y": shadow_y,
        "text_opacity": 1.0,
        "outline_opacity": 1.0,
        "shadow_opacity": 0.9,
    }


def ass_header(width, height, font_name, style):
    primary = "&H00FFFFFF"
    outline_color = "&H00000000"
    shadow_color = "&H19000000"
    return "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            (
                "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
                "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,"
                "ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,"
                "MarginL,MarginR,MarginV,Encoding"
            ),
            (
                f"Style: Default,{font_name},{style['font_size']},{primary},{primary},"
                f"{outline_color},{shadow_color},0,0,0,0,100,100,{style['spacing']},0,1,"
                f"{style['outline']},0,2,60,60,{style['margin_v']},1"
            ),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
    )


def write_ass(ass_path, cues, width, height, font_name, preset_name):
    style = style_values(width, height, preset_name)
    lines = [ass_header(width, height, font_name, style)]
    for cue in cues:
        text = escape_ass_text(cue.text)
        tags = rf"{{\xshad{style['shadow_x']}\yshad{style['shadow_y']}}}"
        lines.append(
            "Dialogue: 0,"
            f"{format_ass_timestamp(cue.start)},{format_ass_timestamp(cue.end)},"
            f"Default,,0,0,0,,{tags}{text}"
        )

    Path(ass_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return style


def build_ass_filter(ass_path, fonts_dir=None):
    escaped = Path(ass_path).as_posix().replace("\\", "/").replace(":", r"\:")
    escaped = escaped.replace(",", r"\,").replace("[", r"\[").replace("]", r"\]")
    parts = [f"filename={escaped}"]
    if fonts_dir:
        font_escaped = Path(fonts_dir).as_posix().replace("\\", "/").replace(":", r"\:")
        font_escaped = font_escaped.replace(",", r"\,").replace("[", r"\[").replace("]", r"\]")
        parts.append(f"fontsdir={font_escaped}")
    return "ass=" + ":".join(parts)


def create_readme_text(manifest):
    lines = [
        "# Subtitle Delivery Package",
        "",
        "- `original_videos/`: copied source videos",
        "- `subtitles/`: reviewed subtitle files used for delivery",
        "- `styled_ass/`: deterministic ASS files used for burn-in",
        "- `burned_videos/`: hard-subtitled MP4 outputs",
        "- `manifest.json`: file mapping, font resolution, and style metadata",
        "",
        "## Style",
        "",
        f"- Preset: `{manifest['style_preset']}`",
        f"- Font: `{manifest['font']['font_name']}` from `{manifest['font']['font_source']}`",
        f"- Font size ratio: `{manifest['style']['font_size']}` pixels on the recorded reference resolution",
        f"- Character spacing: `{manifest['style']['spacing']}`",
        f"- Outline: `{manifest['style']['outline']}`",
        f"- MarginV: `{manifest['style']['margin_v']}`",
        f"- Shadow distance: `{manifest['style']['shadow_distance']}`",
        "",
        "## Notes",
        "",
        "- libass/ffmpeg line spacing is not independently controllable",
        "- shadow blur is approximated through ASS shadow offsets rather than a dedicated blur knob",
    ]
    return "\n".join(lines) + "\n"


def validate_delivery_root(delivery_root):
    delivery_root = Path(delivery_root)
    required_paths = [
        delivery_root / "original_videos",
        delivery_root / "subtitles",
        delivery_root / "styled_ass",
        delivery_root / "burned_videos",
        delivery_root / "manifest.json",
        delivery_root / "README.md",
    ]
    errors = []
    warnings = []
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing required path: {path}")

    manifest_path = delivery_root / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "errors": errors, "warnings": warnings}

    manifest = read_json(manifest_path)
    for item in manifest.get("files") or []:
        for key in ["copied_video", "srt", "vtt", "ass", "burned_video"]:
            file_path = item.get(key)
            if not file_path or not Path(file_path).exists():
                errors.append(f"Manifest path missing for {item.get('stem')}: {key}")
        resolution = item.get("resolution") or {}
        if not resolution.get("width") or not resolution.get("height"):
            warnings.append(f"Resolution missing for {item.get('stem')}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
