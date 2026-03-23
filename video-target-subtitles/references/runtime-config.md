# Runtime Configuration

## Overview

This skill uses two runtime backends:

- FunASR via the DashScope Python SDK for speech recognition
- An OpenAI-compatible chat completion endpoint for cue-by-cue translation

## Install Dependencies

Persistent install:

```bash
uv pip install dashscope openai
```

Ad hoc execution without modifying the environment:

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py ...
```

## ASR Environment Variables

- `DASHSCOPE_API_KEY`: required for FunASR
- `DASHSCOPE_REGION`: optional, `cn` or `intl`, default `cn`
- `DASHSCOPE_BASE_WEBSOCKET_API_URL`: optional websocket endpoint override
- `FUNASR_MODEL`: optional, default `fun-asr-realtime`
- `FUNASR_LANGUAGE_HINT`: optional, for example `zh`, `en`, or `ja`
- `FUNASR_VOCABULARY_ID`: optional DashScope hotword vocabulary ID

Endpoint defaults:

- China mainland: `wss://dashscope.aliyuncs.com/api-ws/v1/inference`
- International: `wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference`

## Translation Environment Variables

Preferred variables:

- `SUBTITLE_TRANSLATION_API_KEY`
- `SUBTITLE_TRANSLATION_BASE_URL`
- `SUBTITLE_TRANSLATION_MODEL`

Fallback variables:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

DashScope-compatible fallback:

- If no translation-specific key and no `OPENAI_API_KEY` are set, `translate_segments.py` falls back to `DASHSCOPE_API_KEY`
- In that case the default base URL is `https://dashscope.aliyuncs.com/compatible-mode/v1`
- In that case the default translation model is `qwen-plus`

## Recommended Execution Pattern

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py data/example.mp4 \
  --target-language English \
  --target-code en
```

Add `--target-locale en-US` or `--source-language zh` when the task needs tighter translation control.
