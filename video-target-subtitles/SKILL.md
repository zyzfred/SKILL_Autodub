---
name: video-target-subtitles
description: Generate target-language subtitles for local video files by extracting speech-ready audio, transcribing it with DashScope FunASR, translating the resulting sentence-aligned segments with an OpenAI-compatible text model while preserving timestamps, and exporting clean SRT or VTT deliverables. Use when Codex needs to subtitle or localize MP4, MOV, MKV, or WebM assets, translate existing captions, repair subtitle timing, or prepare subtitle files for review, dubbing, or publishing.
---

# Video Target Subtitles

Create localized subtitle deliverables from local video files or existing timed-text assets. This skill now binds a concrete ASR backend and translation path:

- ASR: DashScope FunASR via `dashscope.audio.asr.Recognition`
- Translation: OpenAI-compatible chat completion API

Prefer stable intermediate artifacts so transcription, translation, QA, and re-export can be repeated without rerunning the entire pipeline.

## Runtime Setup

Read `references/runtime-config.md` before first use.

- Set `DASHSCOPE_API_KEY` in the environment for FunASR.
- Set translation environment variables with either:
  - `SUBTITLE_TRANSLATION_API_KEY`, `SUBTITLE_TRANSLATION_MODEL`, and optional `SUBTITLE_TRANSLATION_BASE_URL`
  - or `OPENAI_API_KEY` and `OPENAI_MODEL`
  - or reuse `DASHSCOPE_API_KEY` for translation through the DashScope OpenAI-compatible endpoint
- Install dependencies with `uv pip install dashscope openai`, or run scripts ad hoc with `uv run --with dashscope --with openai python ...`

## Workflow

1. Confirm the inputs before touching the media:
- video or subtitle path
- target language and locale
- requested deliverables: `srt`, `vtt`, or both
- whether timed subtitles already exist

2. Reuse timing before generating new timing:
- If a reliable `srt`, `vtt`, or `ass` file exists, translate cue text and preserve cue boundaries unless timing is clearly broken.
- If a timed transcript JSON already exists, translate that JSON and export.
- Only run fresh ASR when no trustworthy timed text exists.

3. Inspect the media streams:

```bash
python scripts/probe_media.py input.mp4 --pretty
```

Use the result to confirm duration, stream layout, and whether the file contains multiple audio tracks or embedded subtitle streams.

4. Extract ASR-friendly audio:

```bash
python scripts/extract_audio.py input.mp4 work/input.wav
```

This defaults to mono 16 kHz PCM WAV, which matches the documented FunASR realtime model requirements for `fun-asr-realtime`.

5. Transcribe with FunASR into normalized timed segments:

```bash
uv run --with dashscope python scripts/funasr_transcribe.py work/input.wav work/video.source.segments.json
```

Defaults:

- model: `fun-asr-realtime`
- websocket endpoint: Beijing region unless overridden by env
- segmentation: semantic punctuation enabled

6. Rebalance source segments before translation when raw ASR cuts are too coarse or too twitchy:

```bash
python scripts/rebalance_segments.py \
  work/video.source.segments.json \
  work/video.source.rebalanced.segments.json
```

Use this pass to:

- split long source cues with word timestamps and punctuation
- preserve short source cues by default, including short emphasis beats
- keep the time axis stable before translation and export

7. Run semantic repair on source cues when ASR content is locally coherent but still contains dangling fragments:

```bash
python scripts/semantic_repair_segments.py \
  work/video.source.rebalanced.segments.json \
  work/video.source.semantic.segments.json
```

Use this pass to:

- merge neighboring source cues only when the cue is semantically incomplete on its own
- preserve timestamps while reducing obvious fragmentary text
- hand cleaner source cues to the translation step

8. Translate while preserving timestamps:

```bash
uv run --with openai python scripts/translate_segments.py \
  work/video.source.semantic.segments.json \
  work/video.en.translated.segments.json \
  --target-language English
```

The translation step keeps `start` and `end` unchanged and only rewrites cue text. Ask for compact subtitle phrasing, minimal punctuation, and no hard line breaks.

9. Polish final cue timing:

```bash
python scripts/polish_segment_timing.py \
  work/video.en.translated.segments.json \
  work/video.en.segments.json
```

Use this pass to:

- stretch very short cues into nearby gaps when space allows
- normalize cue gaps to the configured minimum without causing overlaps
- keep the final export JSON machine-readable and reusable

10. Export subtitle deliverables with minimal punctuation and semantic wrapping:

```bash
python scripts/segments_to_subtitles.py \
  work/video.en.segments.json \
  output/video.en.srt \
  --format srt \
  --max-line-length 42 \
  --punctuation-mode minimal
python scripts/segments_to_subtitles.py \
  work/video.en.segments.json \
  output/video.en.vtt \
  --format vtt \
  --max-line-length 42 \
  --punctuation-mode minimal
```

Use this pass to:

- omit weak punctuation such as periods and commas by default
- preserve strong punctuation such as `?` or `!` only when it carries real tone
- wrap long cues across semantic lines instead of forcing extra target-side cue splits
- treat `max-lines` as a warning-only review rule, not an export-time hard limit

11. Reflow translated cues into extra target-side cues only when the user explicitly wants cue splitting instead of wrapped lines:

```bash
python scripts/reflow_translated_segments.py \
  work/video.en.translated.segments.json \
  work/video.en.reflow.segments.json
```

This is now an opt-in path for cases where wrapped lines are not acceptable and target-side cue splitting is worth the extra timing churn.

12. Normalize timed segments into JSON:
- Keep `start` and `end` in seconds as floats.
- Keep source-language segments separate from translated segments.
- Prefer one JSON file per stage:
  - `<stem>.source.segments.json`
  - `<stem>.source.rebalanced.segments.json`
  - `<stem>.source.semantic.segments.json`
  - `<stem>.<target>.translated.segments.json`
  - `<stem>.<target>.segments.json`
  - `<stem>.<target>.reflow.segments.json` when target-side cue splitting is explicitly enabled
- Read `references/subtitle-localization.md` for the supported JSON shape and subtitle heuristics.

13. Translate for subtitle readability:
- Preserve source timing when it is usable.
- Translate for on-screen readability, not literal word order.
- Prefer minimal punctuation.
- Use spaces in place of weak punctuation pauses when possible.
- Preserve semantic completeness when wrapping long lines.
- Preserve speaker labels, forced-caption cues, and non-speech tags only when they help comprehension.
- Do not let translated cues become empty or overlap in time.
- When a cue needs wrapping, keep each line within the standard line length when possible.
- If a semantically clean wrap still exceeds the preferred number of lines, keep it and accept the resulting warning.

14. Lint the result before calling it done:

```bash
python scripts/lint_subtitles.py output/video.en.srt
```

Treat non-monotonic timing, overlaps, and empty cues as errors. Treat reading-speed, line-length, and `max-lines` violations as warnings that still usually need review. A clean semantic wrap that still exceeds the preferred line count is an acceptable final state.

## One-Step Pipeline

Use the orchestration script when the task is a straight video-to-subtitles workflow:

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py input.mp4 \
  --target-language English \
  --target-code en
```

This script:

- extracts mono 16 kHz WAV audio
- transcribes with FunASR
- rebalances source cues by splitting long source cues while preserving short emphasis cues
- repairs only semantically broken source cues before translation
- translates each subtitle cue while preserving timestamps
- polishes final timing for minimum gap and short-cue duration
- exports `srt` and `vtt` with minimal punctuation and semantic line wrapping
- lints the exported subtitle files

## Decision Rules

- Prefer existing subtitle files over fresh transcription whenever possible.
- Keep a machine-readable intermediate JSON file even if the final deliverable is only `srt`.
- Ask for clarification before translating songs, background chatter, or on-screen signs unless the deliverable clearly requires them.
- Deliver subtitle files first for open-caption requests; burn-in belongs after subtitle QA.
- Switch to an OCR workflow when the only available text is hard-burned into video frames. This skill does not automate OCR extraction.

## Output Conventions

When the user does not provide names, write outputs under a predictable folder such as `output/`:

- `<stem>.source.segments.json`
- `<stem>.source.rebalanced.segments.json`
- `<stem>.source.semantic.segments.json`
- `<stem>.<target>.translated.segments.json`
- `<stem>.<target>.segments.json`
- `<stem>.<target>.reflow.segments.json` when target-side cue splitting is enabled
- `<stem>.<target>.srt`
- `<stem>.<target>.vtt`

## Resources

- `scripts/probe_media.py`: summarize streams and duration with `ffprobe`
- `scripts/extract_audio.py`: extract ASR-friendly WAV audio with `ffmpeg`
- `scripts/funasr_transcribe.py`: run DashScope FunASR and emit normalized `segments.json`
- `scripts/rebalance_segments.py`: split long source cues with word-level timing while preserving short emphasis cues
- `scripts/semantic_repair_segments.py`: merge and lightly repair only fragmentary source cues before translation
- `scripts/translate_segments.py`: translate timed segments with an OpenAI-compatible model while preserving timestamps
- `scripts/polish_segment_timing.py`: normalize minimum gaps and stretch very short cues when space allows
- `scripts/reflow_translated_segments.py`: optional target-side cue splitting when wrapped lines are not acceptable
- `scripts/generate_subtitles.py`: end-to-end extraction, ASR, translation, export, and lint pipeline
- `scripts/segments_to_subtitles.py`: export normalized segment JSON into `srt` or `vtt` with punctuation simplification and semantic wrapping
- `scripts/lint_subtitles.py`: lint subtitle timing and readability constraints
- `references/subtitle-localization.md`: JSON schema, translation heuristics, and QA checklist
- `references/runtime-config.md`: required environment variables, endpoints, and install patterns

## Example Requests

- `Use $video-target-subtitles to generate English subtitles for data/真人.mp4.`
- `Use $video-target-subtitles to translate an existing Chinese SRT into Japanese while keeping timestamps.`
- `Use $video-target-subtitles to repair subtitle timing after re-cutting a short MP4 and export both SRT and VTT.`
