#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from delivery_common import validate_delivery_root


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate the delivery folder structure and manifest paths.",
    )
    parser.add_argument("delivery_root", help="Delivery folder to validate")
    return parser.parse_args()


def main():
    args = parse_args()
    delivery_root = Path(args.delivery_root).expanduser().resolve()
    if not delivery_root.exists():
        raise SystemExit(f"Delivery root not found: {delivery_root}")

    result = validate_delivery_root(delivery_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
