# Subtitle Localization Reference

[English](subtitle-localization.md) | [简体中文](subtitle-localization.zh-CN.md)

## Contents

- JSON shape
- Translation heuristics
- Timing heuristics
- Review checklist

## JSON Shape

Use a plain list or an object with a top-level `segments` array. Each segment should contain at least:

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.48,
      "text": "原始文本或目标语言文本"
    }
  ]
}
```

Optional fields such as `id`, `speaker`, `source_text`, `target_text`, or `notes` are fine, but `scripts/segments_to_subtitles.py` reads only `start`, `end`, and `text`.

Recommended intermediate files:

- Source transcript: `<stem>.source.segments.json`
- Target-language subtitle segments: `<stem>.<target>.segments.json`

## Translation Heuristics

- Keep timestamps unchanged unless the user explicitly asks for re-timing.
- Prefer natural subtitle phrasing over word-for-word translation.
- Preserve intent, speaker attitude, and register.
- Preserve proper nouns and terminology consistently.
- Prefer minimal punctuation. Omit periods and commas unless they materially help comprehension.
- Preserve question marks or exclamation marks only when they reflect strong tone.
- Use spaces in place of weak punctuation pauses when possible.
- When a cue runs long, prefer semantic line wrapping over creating extra cues by default.
- Keep filler words only when they matter to tone, hesitation, or plot.
- Preserve bracketed sound cues only when they help comprehension or accessibility.

Useful prompt shape for segment translation:

```text
Return JSON only.
Keep every segment in the same order.
Keep `start` and `end` unchanged.
Translate `text` into <target language>.
Optimize for subtitle readability rather than literal translation.
Prefer concise subtitle phrasing with minimal punctuation.
Do not insert hard line breaks.
Do not drop meaningful speaker labels or forced-caption cues.
```

## Timing Heuristics

Use these as defaults, not absolutes:

- Keep subtitle duration between 0.8 s and 7.0 s when possible.
- Avoid overlaps.
- Keep gaps above about 0.08 s when editing timings manually.
- Prefer one or two wrapped lines per cue in normal cases.
- Aim for no more than about 42 Latin characters per cue line.
- Aim for no more than about 18 to 22 CJK characters per cue line.
- Aim for reading speed below about 20 characters per second for most content.
- If a semantically clean wrap still exceeds the preferred line count, keep it and treat it as a warning-only review case.

Platform, audience, and script system can justify overrides. Document the override if you relax these thresholds.

## Review Checklist

- Confirm the target language, locale, and tone.
- Confirm whether songs, signs, and background voices should be translated.
- Spot-check terminology consistency across recurring names or phrases.
- Confirm weak punctuation has been removed unless it genuinely improves clarity.
- Confirm wrapped lines stay semantically intact even when a cue exceeds the preferred line count.
- Spot-check the first, middle, and last minute for timing drift.
- Run `scripts/lint_subtitles.py` on the exported subtitle file.
- Open the subtitle file beside the video before handing it off.
