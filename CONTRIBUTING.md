# Contributing

Thanks for contributing to `SKILL_Autodub`.

This repository is intentionally simple:

- the deployable skill lives in `video-target-subtitles/`
- repository-level files such as `README.md`, `LICENSE`, and `docs/` support discovery and release management

## Contribution Rules

- Keep `video-target-subtitles/` deployable as a standalone Codex skill folder.
- Do not introduce repository-only dependencies into the skill runtime.
- Prefer updating the bundled scripts over moving logic into the README.
- Keep weak punctuation minimal by default unless a change explicitly revises that policy.
- Preserve the current baseline that short emphasis cues are not merged just because they are short.

## Local Validation

Before opening a PR or pushing a change, run:

```bash
python -m py_compile video-target-subtitles/scripts/*.py
```

If you changed runtime behavior, also validate against a real sample video or a timed subtitle asset and record:

- sample input used
- output files produced
- lint summary
- accepted residual warnings, if any

## Docs to Update With Behavior Changes

When default behavior changes, update the relevant files together:

- `video-target-subtitles/SKILL.md`
- `video-target-subtitles/references/subtitle-localization.md`
- `video-target-subtitles/agents/openai.yaml`
- `video-target-subtitles/VERSION` when sealing a new version
- `docs/releases/` when writing or updating a public release summary

## Branching

- `main` holds released or release-ready repository documentation
- use topic branches for active iteration work
- planned next branch: `codex/v1.0.1`

## Pull Request Checklist

- The skill folder still deploys cleanly to `$CODEX_HOME/skills/video-target-subtitles`
- Python scripts compile successfully
- README links still work
- If behavior changed, docs and release notes were updated together
- If release behavior changed, the validation summary is explicit about what is now accepted or rejected

