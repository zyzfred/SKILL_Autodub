# Failure Recovery

[English](failure-recovery.md) | [简体中文](failure-recovery.zh-CN.md)

The subtitle production skill should treat batch recovery as a first-class path.

## Required Behavior

- keep one `<stem>.run-summary.json` per video
- keep batch summaries separate from heavy intermediate segment JSON
- preserve the `failed_stage` and error message when a run stops
- support restarting from a later stage instead of rerunning ASR by default
- record whether the source-text stage succeeded through speech ASR or OCR fallback

## Restart Patterns

Rerun a batch from a known stage:

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

Retry only failed items:

```bash
python scripts/retry_failed_translations.py \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

## Summary Expectations

Each run summary should make it easy to answer:

- which input file this summary belongs to
- which stage last succeeded
- which stage failed
- whether source segments came from speech ASR or OCR fallback
- which final subtitle files exist
- how many lint errors and warnings remain

The recovery flow should not depend on delivery-specific files or on early source-stage JSON that belongs outside the final subtitle contract.
