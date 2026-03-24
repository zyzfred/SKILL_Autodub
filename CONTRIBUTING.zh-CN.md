# Contributing

感谢你为 `SKILL_Autodub` 做贡献。

这个仓库现在包含两个可部署的 skill：

- `video-target-subtitles/`
- `video-subtitle-delivery/`

仓库级文件，例如 `README.md`、`LICENSE` 和 `docs/`，用于发现、发布说明和工作流文档。

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

## 贡献规则

- 保持两个 skill 目录都能作为独立 Codex skill 直接部署。
- 不要向任何一个 skill runtime 引入“只有仓库里才有意义”的依赖。
- 优先更新脚本和参考文档，而不是把行为规则塞进 README。
- 仓库文档新增或改动时，必须同步维护中英文两份说明。
- 保持工作流边界清晰：
  - 字幕生产属于 `video-target-subtitles/`
  - 字幕交付属于 `video-subtitle-delivery/`
  - 可以在仓库里说明下游配音交接边界，但不要在未实现语音合成时暗示仓库已经内置配音能力
- 除非显式修改策略，否则默认保持最小弱标点。
- 继续保持“短重点句不会仅因为短就被合并”的基线。

## 本地校验

在提交 PR 或推送变更前，先运行：

```bash
python -m py_compile video-target-subtitles/scripts/*.py video-subtitle-delivery/scripts/*.py
```

如果你修改了运行时行为，还应当基于真实样例视频或已有时间轴字幕资产做验证，并记录：

- 使用了什么输入样例
- 产出了哪些输出文件
- lint 汇总结果
- 若存在已接受残留 warning，具体是什么

## 行为变化时必须同步更新的文档

当默认行为发生变化时，以下文件应一起更新：

- `video-target-subtitles/SKILL.md`
- `video-target-subtitles/SKILL.zh-CN.md`
- `video-subtitle-delivery/SKILL.md`，如果 delivery 合约有变化
- `video-subtitle-delivery/SKILL.zh-CN.md`，如果 delivery 合约有变化
- 对应的双语 `references/` 文档
- `agents/openai.yaml`，如果 skill 元数据有变化
- `VERSION`，如果要封新版本
- `docs/releases/`，如果需要公开发布说明
- `README.md` 和 `README.zh-CN.md`，如果仓库级能力定位发生变化

## 分支约定

- `main` 用于存放已发布或可发布的仓库文档
- 正在进行的迭代请使用 topic branch
- 分支名优先使用 `codex/` 前缀

## Pull Request 清单

- 两个 skill 目录都仍然可以部署到 `$CODEX_HOME/skills`
- Python 脚本编译通过
- 中英文文档链接都正常
- 如果行为变了，文档和 release notes 一起更新了
- 如果 release 行为变了，验证总结里明确写清楚了现在接受和拒绝的结果
