# SKILL Autodub

`video-target-subtitles` 与 `video-subtitle-delivery` 两个 Codex skill 的仓库。

[English](README.md) | [简体中文](README.zh-CN.md)

许可证：[MIT](LICENSE)

## 仓库范围

这个仓库现在维护一条两段式工作流，覆盖多语种字幕生产与字幕交付：

- `video-target-subtitles` 负责从本地视频或已有时间轴字幕生成多语种字幕资产。
- `video-subtitle-delivery` 负责把审核通过的字幕打包成最终交付目录、样式化 `ASS`、压制视频、清单以及可选 zip 包。

当前仓库还没有内置独立的语音合成配音 skill。更准确地说，这个仓库负责把多语种配音上游所需的资产做稳定化：审核后的字幕、可复用时间轴 JSON、batch summary、delivery manifest，都可以直接交给下游配音系统继续做 TTS、配音混流或母版生成，而不用重跑 ASR 和翻译。

## 当前版本线

仓库级发布标签：`v1.1.1`

| Skill | 版本 | 作用 |
| --- | --- | --- |
| `video-target-subtitles` | `v1.1.1` | 字幕生成、本地化、时间轴修复、OCR 兜底、批量字幕处理 |
| `video-subtitle-delivery` | `v0.1.0` | 审核后字幕打包、样式化 `ASS`、硬字幕输出、交付封装 |

发布说明：

- [`docs/releases/v1.1.1.md`](docs/releases/v1.1.1.md)
- [`docs/releases/video-target-subtitles-v1.1.1.md`](docs/releases/video-target-subtitles-v1.1.1.md)
- [`docs/releases/video-subtitle-delivery-v0.1.0.md`](docs/releases/video-subtitle-delivery-v0.1.0.md)
- 上一个仓库发布：[`docs/releases/v1.1.0.md`](docs/releases/v1.1.0.md)
- 历史基线：[`docs/releases/v1.0.0.md`](docs/releases/v1.0.0.md)

贡献说明：

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`CONTRIBUTING.zh-CN.md`](CONTRIBUTING.zh-CN.md)

版本策略：

- [`docs/versioning-strategy.md`](docs/versioning-strategy.md)
- [`docs/versioning-strategy.zh-CN.md`](docs/versioning-strategy.zh-CN.md)

工作流总览：

- [`docs/workflow-overview.md`](docs/workflow-overview.md)
- [`docs/workflow-overview.zh-CN.md`](docs/workflow-overview.zh-CN.md)

后续计划：

- [`docs/plans/v1.2.0.md`](docs/plans/v1.2.0.md)
- [`docs/plans/v1.2.0.zh-CN.md`](docs/plans/v1.2.0.zh-CN.md)

## 工作流

```mermaid
flowchart LR
  A["输入视频或已有时间轴字幕"] --> B["video-target-subtitles"]
  B --> C["审核后的多语种字幕"]
  C --> D["video-subtitle-delivery"]
  C -. "可选下游交接" .-> E["多语种配音系统"]
  D --> F["ASS + 压制视频 + manifest + 交付包"]
  E --> G["合成语音与配音母版"]
```

## Skill 边界

### `video-target-subtitles`

当任务仍然属于字幕生产时，使用这个 skill：

- 提取适合识别的音频
- 先用 DashScope FunASR 转写，失败时回退到 Qwen OCR
- 在保留时间轴的前提下做翻译
- 导出 `srt` / `vtt`
- 进行批量字幕生成、失败重试和结果汇总

这个 skill 有意停在以下边界之前：

- 样式化 `ASS`
- 压制字幕视频
- delivery 目录封装
- zip 交付包
- 语音合成或配音音频生成

### `video-subtitle-delivery`

只有在字幕 QA 已完成后才使用这个 skill：

- 将审核后的字幕转换成样式化 `ASS`
- 用 `ffmpeg` / `libass` 压制到视频中
- 构建可复现的交付目录
- 导出 `manifest.json`、交付 `README.md` 和可选 zip 包

这个 skill 明确不负责：

- ASR
- 翻译
- 字幕文本重写
- 未审核字幕的时间轴修复
- 语音合成或换声配音

## 仓库结构

```text
SKILL_Autodub/
├── README.md
├── README.zh-CN.md
├── CONTRIBUTING.md
├── CONTRIBUTING.zh-CN.md
├── docs/
│   ├── releases/
│   └── plans/
├── video-target-subtitles/
│   ├── SKILL.md
│   ├── SKILL.zh-CN.md
│   ├── VERSION
│   ├── agents/
│   ├── references/
│   └── scripts/
└── video-subtitle-delivery/
    ├── SKILL.md
    ├── SKILL.zh-CN.md
    ├── VERSION
    ├── agents/
    ├── assets/
    ├── references/
    └── scripts/
```

`video-target-subtitles/` 和 `video-subtitle-delivery/` 都是可以直接部署的 skill 目录。

## 部署方式

### 方式 1：把两个 skill 都复制到 Codex skills 目录

```bash
git clone https://github.com/zyzfred/SKILL_Autodub.git
mkdir -p "$CODEX_HOME/skills"
cp -R SKILL_Autodub/video-target-subtitles "$CODEX_HOME/skills/video-target-subtitles"
cp -R SKILL_Autodub/video-subtitle-delivery "$CODEX_HOME/skills/video-subtitle-delivery"
```

### 方式 2：开发时使用软链接

```bash
git clone https://github.com/zyzfred/SKILL_Autodub.git
mkdir -p "$CODEX_HOME/skills"
ln -s "$(pwd)/SKILL_Autodub/video-target-subtitles" "$CODEX_HOME/skills/video-target-subtitles"
ln -s "$(pwd)/SKILL_Autodub/video-subtitle-delivery" "$CODEX_HOME/skills/video-subtitle-delivery"
```

部署后的期望路径：

```text
$CODEX_HOME/skills/video-target-subtitles
$CODEX_HOME/skills/video-subtitle-delivery
```

## 运行依赖

通用依赖：

- `ffmpeg`
- `ffprobe`
- Python 3
- 推荐使用 `uv`

Delivery 额外依赖：

- `ffmpeg` 需要启用 `libass`

字幕生成所需 Python 依赖：

```bash
uv pip install dashscope openai
```

也可以按脚本临时运行字幕生成流程：

```bash
uv run --with dashscope --with openai python ...
```

delivery skill 默认不需要联网。

## 推荐阅读

- [`video-target-subtitles/SKILL.md`](video-target-subtitles/SKILL.md)
- [`video-target-subtitles/SKILL.zh-CN.md`](video-target-subtitles/SKILL.zh-CN.md)
- [`video-subtitle-delivery/SKILL.md`](video-subtitle-delivery/SKILL.md)
- [`video-subtitle-delivery/SKILL.zh-CN.md`](video-subtitle-delivery/SKILL.zh-CN.md)

## 快速校验

检查两个 skill 是否部署到位：

```bash
ls "$CODEX_HOME/skills/video-target-subtitles"
ls "$CODEX_HOME/skills/video-subtitle-delivery"
```

检查 Python 脚本是否可编译：

```bash
python -m py_compile video-target-subtitles/scripts/*.py video-subtitle-delivery/scripts/*.py
```

## 使用示例

```text
Use $video-target-subtitles to generate English subtitles for /absolute/path/input.mp4.
Use $video-target-subtitles to generate Japanese subtitles for every video in /absolute/path/data.
Use $video-subtitle-delivery to package reviewed English subtitles in /absolute/path/output against the videos in /absolute/path/data.
```
