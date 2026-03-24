# Font Licensing

[English](font-licensing.md) | [简体中文](font-licensing.zh-CN.md)

Font selection must be deterministic and license-aware.

## Priority Order

1. bundled fonts under `assets/fonts/`
2. system fonts
3. online fallback only when explicitly allowed

## Recommended Practice

- keep freely distributable fonts inside `assets/fonts/`
- prefer filenames that closely match the font family name
- avoid assuming proprietary system fonts can be redistributed
- if a system font is used, record that in the manifest instead of copying it into the package

## Current State

This skill ships with an empty `assets/fonts/` placeholder directory. If a project needs a guaranteed font, add a redistributable font there and keep its license note alongside it.
