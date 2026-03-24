# Contributing

Thanks for contributing to `SKILL_Autodub`.

This repository now contains two deployable skills:

- `video-target-subtitles/`
- `video-subtitle-delivery/`

Repository-level files such as `README.md`, `LICENSE`, and `docs/` support discovery, release notes, and workflow documentation.

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

## Contribution Rules

- Keep both skill folders deployable as standalone Codex skills.
- Do not introduce repository-only dependencies into either skill runtime.
- Prefer updating bundled scripts and references over moving behavioral logic into the README.
- Keep repository documentation bilingual when you add or revise docs.
- Preserve clean workflow boundaries:
  - subtitle production belongs in `video-target-subtitles/`
  - subtitle delivery belongs in `video-subtitle-delivery/`
  - downstream dubbing handoff may be documented here, but speech synthesis should not be implied unless implemented
- Keep weak punctuation minimal by default unless a change explicitly revises that policy.
- Preserve the baseline that short emphasis cues are not merged just because they are short.

## Local Validation

Before opening a PR or pushing a change, run:

```bash
python -m py_compile video-target-subtitles/scripts/*.py video-subtitle-delivery/scripts/*.py
```

If you changed runtime behavior, also validate against a real sample video or a timed subtitle asset and record:

- sample input used
- output files produced
- lint summary
- accepted residual warnings, if any

## Docs to Update With Behavior Changes

When default behavior changes, update the relevant files together:

- `video-target-subtitles/SKILL.md`
- `video-target-subtitles/SKILL.zh-CN.md`
- `video-subtitle-delivery/SKILL.md` when the delivery contract changes
- `video-subtitle-delivery/SKILL.zh-CN.md` when the delivery contract changes
- the matching `references/` docs in both languages
- `agents/openai.yaml` when skill metadata changes
- `VERSION` when sealing a new version
- `docs/releases/` when writing or updating a public release summary
- `README.md` and `README.zh-CN.md` when repository-level capability positioning changes

## Branching

- `main` holds released or release-ready repository documentation
- use topic branches for active iteration work
- prefer branch names prefixed with `codex/`

## Pull Request Checklist

- Both skill folders still deploy cleanly to `$CODEX_HOME/skills`
- Python scripts compile successfully
- English and Chinese doc links still work
- If behavior changed, docs and release notes were updated together
- If release behavior changed, the validation summary is explicit about what is now accepted or rejected
