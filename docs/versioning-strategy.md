# Versioning Strategy

[English](versioning-strategy.md) | [简体中文](versioning-strategy.zh-CN.md)

## Why This Exists

This repository is now a multi-skill monorepo. A single version number is no longer enough to describe both the repository baseline and each skill's implementation state.

## Two Version Layers

### 1. Repository Release Version

Use a repository-wide Git tag in the format `vX.Y.Z`.

This version means:

- the published baseline on `main`
- the set of skills and docs that belong together as one release
- the entry point for release notes under `docs/releases/`

### 2. Skill Release Version

Each deployable skill keeps its own `VERSION` file.

This version means:

- the contract and runtime state of that specific skill
- the point at which its `SKILL.md`, `references/`, scripts, and metadata are considered aligned
- the version users should reference when discussing one skill in isolation

## Mapping Rule

Repository version and skill version do not need to match.

They should be read together like this:

- repository tag answers: "What is the published state of the repo?"
- skill version answers: "What is the published state of this skill?"

Current example:

- repository release tag: `v1.1.0`
- `video-target-subtitles`: `v1.1.0`
- `video-subtitle-delivery`: `v0.1.0`

## When To Bump Which Version

Bump the repository release tag when:

- `main` reaches a coherent release baseline
- repository-level docs, workflow boundaries, or skill inventory change materially
- multiple skill updates need to be published together

Bump a skill `VERSION` when:

- that skill's runtime behavior changes
- its input or output contract changes
- its scripts, metadata, or reference docs change in a release-relevant way

In most public releases, both may move. They still should not be conflated.

## Release Checklist

For a repository release:

1. update or add `docs/releases/vX.Y.Z.md`
2. confirm README and contribution docs still describe the current repo baseline
3. confirm each touched skill has the correct `VERSION`
4. commit on `main`
5. create and push the Git tag

For a skill release inside the repo:

1. update that skill's `VERSION`
2. update its `SKILL.md`, matching bilingual docs, and relevant `references/`
3. update or add skill-specific release notes when needed
4. include the change in the next repository release if it is meant for publication

## Non-Goals

- forcing all skills to share one synchronized version number
- using repository tags as a substitute for skill `VERSION` files
- hiding breaking skill changes inside repo-level doc-only releases
