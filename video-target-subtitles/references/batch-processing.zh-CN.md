# Batch Processing

[English](batch-processing.md) | [简体中文](batch-processing.zh-CN.md)

`video-target-subtitles` 支持文件夹输入，但前提是该文件夹只包含同一批次要处理的视频。

## 可接受的 Batch 输入

- 单个目录
- 目录内只放本地视频文件
- 支持扩展名：`.mp4`、`.mov`、`.mkv`、`.webm`

这个 batch 入口默认不递归子目录。

## Batch 契约

对于每个源视频 `<stem>.<ext>`，skill 应产出：

- `output/<stem>.work/<stem>.source.segments.json`
- `output/<stem>.work/<stem>.source.rebalanced.segments.json`
- `output/<stem>.work/<stem>.source.semantic.segments.json`
- `output/<stem>.work/<stem>.<target>.translated.segments.json`
- `output/<stem>.work/<stem>.<target>.segments.json`
- `output/<stem>.<target>.srt`
- `output/<stem>.<target>.vtt`
- `output/<stem>.run-summary.json`

对于整个 batch，还应产出：

- `output/batch.<target>.summary.json`
- 当运行 `scripts/summarize_batch_results.py` 时，额外生成 `output/batch.<target>.summary.md`

## 失败语义

- 单个视频失败不能抹掉前面视频已经完成的输出
- 每个视频都保留自己的 `run-summary.json`
- batch 失败时也应尽量留下可用的部分汇总
- rerun 时应支持通过 `--start-at` 从更后面的阶段重启

## 推荐命令

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en
```

从后续阶段继续：

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

汇总已有结果：

```bash
python scripts/summarize_batch_results.py \
  --output-dir output \
  --target-code en
```
