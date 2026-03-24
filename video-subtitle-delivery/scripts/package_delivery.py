#!/usr/bin/env python3

import argparse
import json
import shutil
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a zip archive for a completed delivery folder.",
    )
    parser.add_argument("delivery_root", help="Delivery folder to package")
    parser.add_argument(
        "--archive-path",
        default="",
        help="Optional explicit archive path. Defaults to <delivery_root>.zip",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    delivery_root = Path(args.delivery_root).expanduser().resolve()
    if not delivery_root.exists():
        raise SystemExit(f"Delivery root not found: {delivery_root}")

    archive_path = (
        Path(args.archive_path).expanduser().resolve()
        if args.archive_path
        else delivery_root.with_suffix(".zip")
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    base_name = str(archive_path.with_suffix(""))
    generated = shutil.make_archive(base_name, "zip", root_dir=str(delivery_root))
    print(
        json.dumps(
            {
                "delivery_root": str(delivery_root),
                "archive_path": str(Path(generated).resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
