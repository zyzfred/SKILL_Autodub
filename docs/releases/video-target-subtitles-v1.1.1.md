# Release Notes: video-target-subtitles v1.1.1

## English

`video-target-subtitles v1.1.1` extends the source-text stage with OCR fallback while keeping the existing segment JSON contract stable for translation, timing polish, and subtitle export.

### What Changed

- adds `scripts/transcribe_with_fallback.py` as the unified source-text entrypoint
- adds `scripts/ocr_video_transcribe.py` for sampled-frame OCR extraction with Qwen OCR
- updates single-file and batch orchestration to use the new fallback entrypoint
- records fallback mode, fallback reason, and provider details in generated summaries
- documents `SUBTITLE_OCR_MODEL` with default `qwen-vl-ocr-latest`

### Current Behavior

- prefers DashScope FunASR for speech-aligned source extraction
- falls back to OCR when speech ASR fails or returns no usable segments
- keeps downstream rebalance, semantic repair, translation, timing polish, and export stages unchanged
- requires closer human review for OCR-derived timings because they are sampled from frame intervals

### New Repository Artifacts

- `video-target-subtitles/scripts/transcribe_with_fallback.py`
- `video-target-subtitles/scripts/ocr_video_transcribe.py`
- `docs/releases/v1.1.1.md`

## 简体中文

`video-target-subtitles v1.1.1` 在保持既有 segment JSON 契约不变的前提下，为 source-text 阶段增加了 OCR 兜底，因此翻译、时间轴微调和字幕导出链路都不需要改协议。

### 本次变化

- 新增 `scripts/transcribe_with_fallback.py`，作为统一的 source-text 入口
- 新增 `scripts/ocr_video_transcribe.py`，使用 Qwen OCR 做抽帧文字提取
- 单文件和 batch 编排都改为调用新的 fallback 入口
- 在生成的 summary 中记录 fallback mode、fallback reason 和 provider 细节
- 增补 `SUBTITLE_OCR_MODEL` 文档，默认值为 `qwen-vl-ocr-latest`

### 当前行为

- 优先使用 DashScope FunASR 做语音对齐的 source extraction
- 当语音 ASR 失败或没有可用片段时自动回退到 OCR
- 下游的 rebalance、semantic repair、translation、timing polish 和 export 行为保持不变
- 由于 OCR 时间轴来自抽帧采样，人工复核时应比普通语音 ASR 更谨慎

### 新增仓库产物

- `video-target-subtitles/scripts/transcribe_with_fallback.py`
- `video-target-subtitles/scripts/ocr_video_transcribe.py`
- `docs/releases/v1.1.1.md`
