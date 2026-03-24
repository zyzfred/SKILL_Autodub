# Batch Processing

[English](batch-processing.md) | [简体中文](batch-processing.zh-CN.md)

`video-target-subtitles` supports a folder input when the folder contains only target videos for the same subtitle run.

## Accepted Batch Input

- a single directory
- only local video files inside that directory
- supported extensions: `.mp4`, `.mov`, `.mkv`, `.webm`

This batch entry does not recurse into nested directories.

## Batch Contract

For each source video `<stem>.<ext>` the skill should produce:

- `output/<stem>.work/<stem>.source.segments.json`
- `output/<stem>.work/<stem>.source.rebalanced.segments.json`
- `output/<stem>.work/<stem>.source.semantic.segments.json`
- `output/<stem>.work/<stem>.<target>.translated.segments.json`
- `output/<stem>.work/<stem>.<target>.segments.json`
- `output/<stem>.<target>.srt`
- `output/<stem>.<target>.vtt`
- `output/<stem>.run-summary.json`

For the full batch it should also produce:

- `output/batch.<target>.summary.json`
- `output/batch.<target>.summary.md` when `scripts/summarize_batch_results.py` is run

## Failure Semantics

- one video failure must not erase completed outputs for earlier videos
- each video keeps its own `run-summary.json`
- batch failure should still leave a usable partial batch summary
- reruns should be able to start from a later stage with `--start-at`

## Recommended Commands

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en
```

Resume from a later stage:

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

Summarize existing results:

```bash
python scripts/summarize_batch_results.py \
  --output-dir output \
  --target-code en
```
