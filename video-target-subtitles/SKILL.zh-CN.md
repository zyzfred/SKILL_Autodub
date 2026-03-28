---
name: video-target-subtitles
description: Generate target-language subtitles for local video files by extracting speech-ready audio, transcribing it with DashScope FunASR, falling back to Qwen OCR over sampled video frames when speech recognition fails, translating the resulting sentence-aligned segments with an OpenAI-compatible text model while preserving timestamps, and exporting clean SRT or VTT deliverables. Supports batch subtitle generation from a folder of local videos. Use when Codex needs to subtitle or localize MP4, MOV, MKV, or WebM assets, translate existing captions, repair subtitle timing, or prepare subtitle files for review, dubbing, or publishing.
---

# Video Target Subtitles

[English](SKILL.md) | [简体中文](SKILL.zh-CN.md)

从本地视频文件或已有时间轴字幕资产生成目标语言字幕。这个 skill 有意只覆盖字幕生产与字幕 QA，不把 delivery 和配音混在一起。当前绑定的后端路径如下：

- 语音 ASR：DashScope FunASR，经由 `dashscope.audio.asr.Recognition`
- OCR 兜底：当 FunASR 失败或没有产出可用片段时，经由 DashScope OpenAI-compatible endpoint 调用 Qwen OCR 抽取画面文字
- 翻译：OpenAI-compatible chat completion API

优先保留稳定的中间产物，这样转写、翻译、QA、重导出都可以重复执行，而不必每次重跑整条链。

这个 skill 支持：

- 单个本地视频文件
- 单个已有时间轴字幕文件
- 只包含目标视频的文件夹批量字幕生产

这个 skill 不负责：

- delivery 目录打包
- 样式化 `ASS` 生成
- 最终 zip 交付包

当用户要压制、打包时，切换到单独的 delivery skill。
当用户要做语音合成、换声或多语种配音母版时，切换到独立的配音工作流。

## 运行准备

首次使用前先阅读 `references/runtime-config.md` 与 `references/runtime-config.zh-CN.md`。

- 为 FunASR 设置环境变量 `DASHSCOPE_API_KEY`
- 如果要覆盖 OCR 兜底模型，在环境变量里设置 `SUBTITLE_OCR_MODEL`。默认是 `qwen-vl-ocr-latest`。同时兼容 `QWEN_OCR_MODEL` 这个别名。
- 为翻译设置以下任一组环境变量：
  - `SUBTITLE_TRANSLATION_API_KEY`、`SUBTITLE_TRANSLATION_MODEL`，以及可选的 `SUBTITLE_TRANSLATION_BASE_URL`
  - 或 `OPENAI_API_KEY` 与 `OPENAI_MODEL`
  - 或直接复用 `DASHSCOPE_API_KEY` 走 DashScope 的 OpenAI-compatible endpoint
- 依赖安装方式：
  - `uv pip install dashscope openai`
  - 或按需运行 `uv run --with dashscope --with openai python ...`

## 工作流

1. 在碰媒体前先确认输入：
- 视频或字幕路径
- 目标语言与 locale
- 需要的导出格式：`srt`、`vtt` 或两者都要
- 是否已经存在时间轴字幕
- 用户给的是单文件还是视频文件夹

2. 保持触发边界干净：
- 如果用户说的是“生成字幕”，就停留在字幕生产阶段
- 不要在没有明确要求时顺带做 `ASS`、压制或打包
- 文件夹输入表示“对每个视频跑同一套字幕链路”，不表示“生成 delivery 包”

3. 能复用已有时间轴时，不重造时间轴：
- 如果已有可靠的 `srt`、`vtt` 或 `ass`，直接翻译 cue 文本并尽量保留 cue 边界
- 如果已有时间轴 transcript JSON，直接翻译 JSON 并导出
- 只有在没有可信时间轴文本时才跑新的 source extraction

4. 探测媒体流：

```bash
python scripts/probe_media.py input.mp4 --pretty
```

用结果确认时长、流布局，以及是否存在多音轨或内嵌字幕轨。

5. 提取适合 ASR 的音频：

```bash
python scripts/extract_audio.py input.mp4 work/input.wav
```

默认提取为单声道 16 kHz PCM WAV，这与 `fun-asr-realtime` 的要求一致。

6. 先做语音转写，必要时自动回退到 OCR，生成标准化时间轴片段：

```bash
uv run --with dashscope --with openai python scripts/transcribe_with_fallback.py \
  work/input.wav \
  work/video.source.segments.json \
  --video-path input.mp4
```

默认值：

- 语音模型：`fun-asr-realtime`
- OCR 兜底模型：`qwen-vl-ocr-latest`
- 语音 websocket endpoint：默认中国区，可由环境变量覆盖
- OCR 兜底会复用 `DASHSCOPE_API_KEY`，并按当前地域使用 DashScope compatible-mode endpoint
- FunASR 默认开启 semantic punctuation
- OCR 时间轴来自抽帧采样，不是逐词对齐；对硬字幕视频应比普通 ASR 结果更谨慎地复核

7. 当原始 ASR 切分过粗或过碎时，先做 source 重分句：

```bash
python scripts/rebalance_segments.py \
  work/video.source.segments.json \
  work/video.source.rebalanced.segments.json
```

这一阶段用于：

- 结合词级时间戳和标点拆长句
- 默认保留短 source cue，包括短重点句
- 在翻译前尽量保持时间轴稳定

8. 当 source cue 内容基本正确但存在残缺片段时，做 semantic repair：

```bash
python scripts/semantic_repair_segments.py \
  work/video.source.rebalanced.segments.json \
  work/video.source.semantic.segments.json
```

这一阶段用于：

- 只在 cue 单独看语义不完整时合并相邻 cue
- 在减少碎片文本的同时保留时间轴
- 给翻译阶段提供更干净的 source cue

9. 在保留时间轴的前提下翻译：

```bash
uv run --with openai python scripts/translate_segments.py \
  work/video.source.semantic.segments.json \
  work/video.en.translated.segments.json \
  --target-language English
```

翻译阶段保持 `start` 与 `end` 不变，只重写文本。提示词目标应是：字幕式表达、最小标点、不要硬插换行。

10. 微调最终 cue 时间轴：

```bash
python scripts/polish_segment_timing.py \
  work/video.en.translated.segments.json \
  work/video.en.segments.json
```

这一阶段用于：

- 在空间允许时拉长过短 cue
- 统一最小 gap，避免重叠
- 输出机器可读、可复用的最终 JSON

11. 以最小标点和语义换行导出字幕：

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

这一阶段用于：

- 默认省略句号、逗号等弱标点
- 仅在语气确实强时保留 `?` 或 `!`
- 优先按语义换行，而不是默认拆成更多 target cue
- 将 `max-lines` 视为 review warning，而不是导出硬失败

12. 只有在用户明确要求“拆 cue 而不是换行”时，才启用 target 侧 reflow：

```bash
python scripts/reflow_translated_segments.py \
  work/video.en.translated.segments.json \
  work/video.en.reflow.segments.json
```

这是 opt-in 路径，只适用于 wrapped lines 完全不可接受、且值得承受额外 timing churn 的情况。

13. 时间轴 JSON 规范：
- `start` 和 `end` 使用秒级 float
- source segments 与 translated segments 分开保存
- 推荐每个阶段一个 JSON 文件：
  - `<stem>.source.segments.json`
  - `<stem>.source.rebalanced.segments.json`
  - `<stem>.source.semantic.segments.json`
  - `<stem>.<target>.translated.segments.json`
  - `<stem>.<target>.segments.json`
  - 当显式启用 target-side cue splitting 时，额外生成 `<stem>.<target>.reflow.segments.json`
- 详细形状与规则见 `references/subtitle-localization.md`

14. 字幕翻译原则：
- 只要原始时间轴可用，就尽量保持不变
- 优先为屏幕可读性翻译，而不是逐词直译
- 弱标点尽量省略
- 可能的话，用空格替代弱标点停顿
- 长句换行时保证语义完整
- 只有确实有助理解时才保留 speaker label、forced-caption cue、非语音标签
- 不要让翻译后的 cue 变空或发生时间重叠
- 如果 semantically clean 的换行仍超过理想行数，可以保留并接受 warning

15. 交付前先 lint：

```bash
python scripts/lint_subtitles.py output/video.en.srt
```

非单调时间轴、重叠、空 cue 视为错误。阅读速度、行长和 `max-lines` 超限通常视为 warning，需要复核。若语义换行已经干净，超出理想行数也可以接受。

## 一步式流程

当任务就是标准的视频到字幕链路时，优先使用 orchestration script：

```bash
uv run --with dashscope --with openai python scripts/generate_subtitles.py input.mp4 \
  --target-language English \
  --target-code en
```

这个脚本会：

- 提取单声道 16 kHz WAV 音频
- 先尝试 FunASR，若失败或没有可用语音片段则回退到按视频抽帧的 Qwen OCR
- 在保留短重点句的前提下重分 source cue
- 只修复语义残缺 source 片段
- 保持时间轴不变地翻译每个字幕 cue
- 微调短 cue 与最小 gap
- 导出带最小标点与语义换行的 `srt` / `vtt`
- 对导出的字幕做 lint

## Batch 文件夹输入

当输入是只包含目标视频的文件夹时，使用 batch 入口：

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en
```

文件夹语义：

- 扫描该目录下所有支持的视频扩展名
- 对每个视频独立运行同一套字幕生产链
- 即使后续视频失败，也保留每个视频自己的 `<stem>.run-summary.json`
- 生成统一的 `batch.<target>.summary.json`
- 支持通过 `--start-at` 从指定阶段重启
- 支持配合 `scripts/retry_failed_translations.py` 只重试失败项

Batch 模式仍然停在字幕输出和 lint，不会生成 delivery 目录、`ASS`、硬字幕或 zip。

## 决策规则

- 能复用已有字幕时，优先复用，不要重新转写
- 即便最终只交 `srt`，也保留中间 JSON
- 歌曲、背景对白、屏幕文字是否翻译，若不明确就先澄清
- 对开放字幕请求，先交付字幕文件；burn-in 属于 QA 之后的事
- 如果语音 ASR 失败，或对白只存在于硬烧录画面文字中，让流水线自动回退到 OCR，并更仔细地复核采样时间轴
- 当用户给的是文件夹时，默认其中所有支持的视频都属于这次 batch，除非用户用文件名或 stem 缩小范围
- delivery 打包是下游问题；这里最多交付 source 视频、最终 `srt`/`vtt` 和 run summaries
- 多语种配音属于更下游的语音系统；这个 skill 负责给配音阶段准备稳定的已审核字幕和时间轴资产

## 输出约定

若用户没有指定目录，默认写到类似 `output/` 的目录：

- `<stem>.source.segments.json`
- `<stem>.source.rebalanced.segments.json`
- `<stem>.source.semantic.segments.json`
- `<stem>.<target>.translated.segments.json`
- `<stem>.<target>.segments.json`
- 启用 target-side cue splitting 时生成 `<stem>.<target>.reflow.segments.json`
- `<stem>.<target>.srt`
- `<stem>.<target>.vtt`
- batch 运行时为每个视频生成 `<stem>.run-summary.json`
- 整个 batch 生成 `batch.<target>.summary.json`
- 使用 `scripts/summarize_batch_results.py` 时还会输出 `batch.<target>.summary.md`

## 资源

- `scripts/probe_media.py`：用 `ffprobe` 汇总媒体流和时长
- `scripts/extract_audio.py`：用 `ffmpeg` 提取适合 ASR 的 WAV 音频
- `scripts/transcribe_with_fallback.py`：先尝试 FunASR，失败时自动回退到 Qwen OCR
- `scripts/funasr_transcribe.py`：运行 DashScope FunASR 并输出标准化 `segments.json`
- `scripts/ocr_video_transcribe.py`：按时间间隔抽取视频帧，运行 Qwen OCR，并输出标准化 `segments.json`
- `scripts/rebalance_segments.py`：在保留短重点句的同时拆长 source cue
- `scripts/semantic_repair_segments.py`：只对残缺 source cue 做轻量合并与修复
- `scripts/translate_segments.py`：使用 OpenAI-compatible 模型翻译时间轴片段并保留时间轴
- `scripts/polish_segment_timing.py`：规范最小 gap，并在可能时拉长过短 cue
- `scripts/reflow_translated_segments.py`：当 wrapped lines 不可接受时，进行可选的 target-side cue splitting
- `scripts/generate_subtitles.py`：提取、ASR、翻译、导出、lint 的端到端流程
- `scripts/batch_generate_subtitles.py`：以文件夹为范围的 batch 编排器
- `scripts/retry_failed_translations.py`：从翻译阶段或用户指定阶段只重跑失败项
- `scripts/summarize_batch_results.py`：把单视频 run summaries 汇总成 machine-readable 与 human-readable batch summary
- `scripts/segments_to_subtitles.py`：把标准化 segment JSON 导出为 `srt` / `vtt`
- `scripts/lint_subtitles.py`：检查字幕时间轴与可读性约束
- `references/subtitle-localization.md`：JSON 结构、翻译原则、QA 清单
- `references/runtime-config.md`：环境变量、endpoint 与安装方式
- `references/batch-processing.md`：文件夹输入语义、输出契约与 batch 调用方式
- `references/failure-recovery.md`：重启、重试与单文件 summary 约定

## 示例请求

- `Use $video-target-subtitles to generate English subtitles for data/真人.mp4.`
- `Use $video-target-subtitles to generate English subtitles for every video in data/.`
- `Use $video-target-subtitles to translate an existing Chinese SRT into Japanese while keeping timestamps.`
- `Use $video-target-subtitles to repair subtitle timing after re-cutting a short MP4 and export both SRT and VTT.`
