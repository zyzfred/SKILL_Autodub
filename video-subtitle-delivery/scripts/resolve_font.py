#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from delivery_common import resolve_font_choice


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resolve the font used for subtitle delivery.",
    )
    parser.add_argument(
        "--assets-fonts-dir",
        default=str((Path(__file__).resolve().parent.parent / "assets/fonts").resolve()),
        help="Directory containing bundled fonts (default: skill assets/fonts)",
    )
    parser.add_argument(
        "--style-preset",
        default="default-english-burnin",
        help="Style preset name (default: default-english-burnin)",
    )
    parser.add_argument(
        "--allow-download-fallback",
        action="store_true",
        help="Allow downloading a fallback font when no asset or system font is found",
    )
    parser.add_argument(
        "--download-dir",
        default="",
        help="Directory used for downloaded fallback fonts",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    download_dir = Path(args.download_dir).expanduser().resolve() if args.download_dir else None
    font_info = resolve_font_choice(
        assets_fonts_dir=Path(args.assets_fonts_dir).expanduser().resolve(),
        preset_name=args.style_preset,
        allow_download_fallback=args.allow_download_fallback,
        download_dir=download_dir,
    )
    print(json.dumps(font_info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
