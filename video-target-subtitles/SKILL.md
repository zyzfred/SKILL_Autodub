---
name: video-target-subtitles
description: Generate target-language subtitles for local video files by extracting speech-ready audio, transcribing it with DashScope FunASR, falling back to Qwen OCR over sampled video frames when speech recognition fails, translating the resulting sentence-aligned segments with an OpenAI-compatible text model while preserving timestamps, and exporting clean SRT or VTT deliverables. Supports batch subtitle generation from a folder of local videos. Use when Codex needs to subtitle or localize MP4, MOV, MKV, or WebM assets, translate existing captions, repair subtitle timing, or prepare subtitle files for review, dubbing, or publishing.
---

# Video Target Subtitles

[English](SKILL.md) | [简体中文](SKILL.zh-CN.md)

Create localized subtitle deliverables from local video files or existing timed-text assets. This skill is intentionally limited to subtitle production and subtitle QA. It now binds a concrete speech backend, OCR fallback, and translation path:

- Speech ASR: DashScope FunASR via `dashscope.audio.asr.Recognition`
- OCR fallback: Qwen OCR via the DashScope OpenAI-compatible endpoint when FunASR fails or returns no usable segments
- Translation: OpenAI-compatible chat completion API

Prefer stable intermediate artifacts so transcription, translation, QA, and re-export can be repeated without rerunning the entire pipeline.

This skill supports:

- a single local video file
- a single existing timed-text file
- a folder that contains only target videos for batch subtitle production

This skill does not handle:

- delivery directory packaging
- styled `ASS` generation
- final zip archives

Use a separate delivery skill after subtitle QA when the user wants burn-in or packaged export.
Use a separate dubbing workflow after subtitle QA when the user wants speech synthesis, voice replacement, or multilingual dubbed masters.

## Runtime Setup

Read `references/runtime-config.md` before first use.

- Set `DASHSCOPE_API_KEY` in the environment for FunASR.
- Set `SUBTITLE_OCR_MODEL` in the environment when you want to override the OCR fallback model. The default is `qwen-vl-ocr-latest`. `QWEN_OCR_MODEL` is also accepted as an alias.
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
- whether the user provided a single file or a folder of videos

2. Keep trigger boundaries clean:
- If the user asks to "generate subtitles", stay inside subtitle production.
- Do not start `ASS` styling, burn-in, or packaging unless they explicitly ask for a delivery step.
- Folder input means "run the same subtitle production chain for each video in that folder", not "create a delivery package".

3. Reuse timing before generating new timing:
- If a reliable `srt`, `vtt`, or `ass` file exists, translate cue text and preserve cue boundaries unless timing is clearly broken.
- If a timed transcript JSON already exists, translate that JSON and export.
- Only run fresh source extraction when no trustworthy timed text exists.

4. Inspect the media streams:

```bash
python scripts/probe_media.py input.mp4 --pretty
```

Use the result to confirm duration, stream layout, and whether the file contains multiple audio tracks or embedded subtitle streams.

5. Extract ASR-friendly audio:

```bash
python scripts/extract_audio.py input.mp4 work/input.wav
```

This defaults to mono 16 kHz PCM WAV, which matches the documented FunASR realtime model requirements for `fun-asr-realtime`.

6. Transcribe into normalized timed segments with automatic OCR fallback:

```bash
uv run --with dashscope --with openai python scripts/transcribe_with_fallback.py \
  work/input.wav \
  work/video.source.segments.json \
  --video-path input.mp4
```

Defaults:

- speech model: `fun-asr-realtime`
- OCR fallback model: `qwen-vl-ocr-latest`
- speech websocket endpoint: Beijing region unless overridden by env
- OCR fallback reuses `DASHSCOPE_API_KEY` and the DashScope compatible-mode endpoint for the active region
- segmentation: semantic punctuation enabled for FunASR
- OCR timing is sampled from frame intervals, so review hard-burned subtitle videos more carefully than speech-aligned ASR output

7. Rebalance source segments before translation when raw ASR cuts are too coarse or too twitchy:

```bash
python scripts/rebalance_segments.py \
  work/video.source.segments.json \
  work/video.source.rebalanced.segments.json
```

Use this pass to:

- split long source cues with word timestamps and punctuation
- preserve short source cues by default, including short emphasis beats
- keep the time axis stable before translation and export

8. Run semantic repair on source cues when ASR content is locally coherent but still contains dangling fragments:

```bash
python scripts/semantic_repair_segments.py \
  work/video.source.rebalanced.segments.json \
  work/video.source.semantic.segments.json
```

Use this pass to:

- merge neighboring source cues only when the cue is semantically incomplete on its own
- preserve timestamps while reducing obvious fragmentary text
- hand cleaner source cues to the translation step

9. Translate while preserving timestamps:

```bash
uv run --with openai python scripts/translate_segments.py \
  work/video.source.semantic.segments.json \
  work/video.en.translated.segments.json \
  --target-language English
```

The translation step keeps `start` and `end` unchanged and only rewrites cue text. Ask for compact subtitle phrasing, minimal punctuation, and no hard line breaks.

10. Polish final cue timing:

```bash
python scripts/polish_segment_timing.py \
  work/video.en.translated.segments.json \
  work/video.en.segments.json
```

Use this pass to:

- stretch very short cues into nearby gaps when space allows
- normalize cue gaps to the configured minimum without causing overlaps
- keep the final export JSON machine-readable and reusable

11. Export subtitle deliverables with minimal punctuation and semantic wrapping:

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

12. Reflow translated cues into extra target-side cues only when the user explicitly wants cue splitting instead of wrapped lines:

```bash
python scripts/reflow_translated_segments.py \
  work/video.en.translated.segments.json \
  work/video.en.reflow.segments.json
```

This is now an opt-in path for cases where wrapped lines are not acceptable and target-side cue splitting is worth the extra timing churn.

13. Normalize timed segments into JSON:
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

14. Translate for subtitle readability:
- Preserve source timing when it is usable.
- Translate for on-screen readability, not literal word order.
- Prefer minimal punctuation.
- Use spaces in place of weak punctuation pauses when possible.
- Preserve semantic completeness when wrapping long lines.
- Preserve speaker labels, forced-caption cues, and non-speech tags only when they help comprehension.
- Do not let translated cues become empty or overlap in time.
- When a cue needs wrapping, keep each line within the standard line length when possible.
- If a semantically clean wrap still exceeds the preferred number of lines, keep it and accept the resulting warning.

15. Lint the result before calling it done:

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
- tries FunASR first and falls back to Qwen OCR over sampled video frames when ASR fails or returns no usable speech segments
- rebalances source cues by splitting long source cues while preserving short emphasis cues
- repairs only semantically broken source cues before translation
- translates each subtitle cue while preserving timestamps
- polishes final timing for minimum gap and short-cue duration
- exports `srt` and `vtt` with minimal punctuation and semantic line wrapping
- lints the exported subtitle files

## Batch Folder Input

Use the batch entrypoint when the input is a folder containing only target videos:

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en
```

Folder semantics:

- scan all supported video extensions under the folder
- run the same subtitle production chain for each video independently
- keep one `<stem>.run-summary.json` per video even when later videos fail
- write one `batch.<target>.summary.json` batch summary
- allow restart from a specific stage with `--start-at`
- allow retrying failed items with `scripts/retry_failed_translations.py`

Batch mode still stops at subtitle outputs and linting. It does not create delivery folders, `ASS`, burn-in, or zip archives.

## Decision Rules

- Prefer existing subtitle files over fresh transcription whenever possible.
- Keep a machine-readable intermediate JSON file even if the final deliverable is only `srt`.
- Ask for clarification before translating songs, background chatter, or on-screen signs unless the deliverable clearly requires them.
- Deliver subtitle files first for open-caption requests; burn-in belongs after subtitle QA.
- When speech ASR fails or the dialogue is only available as hard-burned on-screen text, let the pipeline fall back to OCR and review the sampled timings more carefully.
- When the user provides a folder, assume every supported video inside that folder belongs to the batch unless they narrow it with stems or filenames.
- Delivery packaging is a downstream concern. Hand off only the source videos, final `srt`/`vtt`, and run summaries.

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
- `<stem>.run-summary.json` for batch runs
- `batch.<target>.summary.json` for the batch aggregate
- `batch.<target>.summary.md` when using `scripts/summarize_batch_results.py`

## Resources

- `scripts/probe_media.py`: summarize streams and duration with `ffprobe`
- `scripts/extract_audio.py`: extract ASR-friendly WAV audio with `ffmpeg`
- `scripts/transcribe_with_fallback.py`: try FunASR first and fall back to Qwen OCR when speech recognition fails
- `scripts/funasr_transcribe.py`: run DashScope FunASR and emit normalized `segments.json`
- `scripts/ocr_video_transcribe.py`: sample video frames, run Qwen OCR, and emit normalized `segments.json`
- `scripts/rebalance_segments.py`: split long source cues with word-level timing while preserving short emphasis cues
- `scripts/semantic_repair_segments.py`: merge and lightly repair only fragmentary source cues before translation
- `scripts/translate_segments.py`: translate timed segments with an OpenAI-compatible model while preserving timestamps
- `scripts/polish_segment_timing.py`: normalize minimum gaps and stretch very short cues when space allows
- `scripts/reflow_translated_segments.py`: optional target-side cue splitting when wrapped lines are not acceptable
- `scripts/generate_subtitles.py`: end-to-end extraction, ASR, translation, export, and lint pipeline
- `scripts/batch_generate_subtitles.py`: folder-scoped batch orchestration for video subtitle production
- `scripts/retry_failed_translations.py`: rerun only failed items from the translation stage or a user-selected stage
- `scripts/summarize_batch_results.py`: collapse per-video run summaries into machine-readable and human-readable batch summaries
- `scripts/segments_to_subtitles.py`: export normalized segment JSON into `srt` or `vtt` with punctuation simplification and semantic wrapping
- `scripts/lint_subtitles.py`: lint subtitle timing and readability constraints
- `references/subtitle-localization.md`: JSON schema, translation heuristics, and QA checklist
- `references/runtime-config.md`: required environment variables, endpoints, and install patterns
- `references/batch-processing.md`: folder input semantics, output contracts, and batch invocation patterns
- `references/failure-recovery.md`: restart, retry, and per-file summary expectations

## Example Requests

- `Use $video-target-subtitles to generate English subtitles for data/真人.mp4.`
- `Use $video-target-subtitles to generate English subtitles for every video in data/.`
- `Use $video-target-subtitles to translate an existing Chinese SRT into Japanese while keeping timestamps.`
- `Use $video-target-subtitles to repair subtitle timing after re-cutting a short MP4 and export both SRT and VTT.`
