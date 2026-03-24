# Runtime Configuration

[English](runtime-config.md) | [简体中文](runtime-config.zh-CN.md)

## 概览

这个 skill 依赖两个运行时后端：

- 使用 DashScope Python SDK 调用 FunASR 做语音识别
- 使用 OpenAI-compatible chat completion endpoint 做逐 cue 翻译

## 安装依赖

常驻安装：

```bash
uv pip install dashscope openai
```

不改环境、按需执行：

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py ...
```

## ASR 环境变量

- `DASHSCOPE_API_KEY`：FunASR 必需
- `DASHSCOPE_REGION`：可选，`cn` 或 `intl`，默认 `cn`
- `DASHSCOPE_BASE_WEBSOCKET_API_URL`：可选，自定义 websocket endpoint
- `FUNASR_MODEL`：可选，默认 `fun-asr-realtime`
- `FUNASR_LANGUAGE_HINT`：可选，例如 `zh`、`en`、`ja`
- `FUNASR_VOCABULARY_ID`：可选，DashScope 热词词表 ID

默认 endpoint：

- 中国大陆：`wss://dashscope.aliyuncs.com/api-ws/v1/inference`
- 国际站：`wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference`

## 翻译环境变量

优先使用：

- `SUBTITLE_TRANSLATION_API_KEY`
- `SUBTITLE_TRANSLATION_BASE_URL`
- `SUBTITLE_TRANSLATION_MODEL`

回退变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

DashScope 兼容回退：

- 如果没有设置翻译专用 key，也没有设置 `OPENAI_API_KEY`，`translate_segments.py` 会回退到 `DASHSCOPE_API_KEY`
- 此时默认 base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 此时默认翻译模型为 `qwen-plus`

## 推荐执行方式

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py data/example.mp4 \
  --target-language English \
  --target-code en
```

当任务需要更严格的翻译控制时，加上 `--target-locale en-US` 或 `--source-language zh`。
