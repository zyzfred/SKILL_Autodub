# Release Notes: video-target-subtitles v1.1.0

## English

`video-target-subtitles v1.1.0` updates the repository baseline from the original `v1.0.0` sealed release to the current locally deployed subtitle-generation skill.

### What Changed

- adds folder-scoped batch subtitle generation
- adds batch summary and per-file run summary artifacts
- adds restart and retry documentation for failed runs
- makes the subtitle-vs-delivery boundary explicit
- keeps subtitle generation usable as an upstream input for multilingual dubbing workflows

### Current Behavior

- preserves short emphasis cues by default
- uses fragment-only semantic repair
- exports subtitles with minimal punctuation by default
- prefers semantic line wrapping over target-side cue splitting
- supports single-file and folder-based subtitle production

### New Repository Artifacts

- `video-target-subtitles/scripts/batch_generate_subtitles.py`
- `video-target-subtitles/scripts/retry_failed_translations.py`
- `video-target-subtitles/scripts/summarize_batch_results.py`
- `video-target-subtitles/references/batch-processing.md`
- `video-target-subtitles/references/failure-recovery.md`

### Boundary Clarification

This release still does not package delivery folders, generate styled `ASS`, burn subtitles into video, or synthesize dubbed audio. Those concerns stay outside subtitle production.

## 简体中文

`video-target-subtitles v1.1.0` 将仓库基线从最初封版的 `v1.0.0` 提升到了当前本机已部署的字幕生成 skill。

### 本次变化

- 新增按文件夹批量生成字幕
- 新增 batch summary 和单文件 run summary
- 新增失败重启与重试的文档说明
- 明确了“字幕生产”和“字幕交付”的边界
- 继续把字幕生成阶段定位为多语种配音工作流的稳定上游输入

### 当前行为

- 默认保留短重点句
- 只做 fragment-only semantic repair
- 默认以最小标点导出字幕
- 优先采用语义换行，而不是 target 侧拆 cue
- 同时支持单文件与文件夹批量字幕生产

### 新增仓库产物

- `video-target-subtitles/scripts/batch_generate_subtitles.py`
- `video-target-subtitles/scripts/retry_failed_translations.py`
- `video-target-subtitles/scripts/summarize_batch_results.py`
- `video-target-subtitles/references/batch-processing.md`
- `video-target-subtitles/references/failure-recovery.md`

### 边界澄清

这个版本依然不负责 delivery 目录打包、样式化 `ASS`、字幕压制视频，或语音合成配音。这些问题继续留在字幕生产阶段之外处理。
