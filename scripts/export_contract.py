"""Write web/src/contract/types.ts from the Python contract, or check that it is current."""

import argparse
import sys
from pathlib import Path

from saltmarket.web.export_ts import render_types

TARGET = Path(__file__).resolve().parents[1] / "web" / "src" / "contract" / "types.ts"


def main() -> int:
    """Write the file, or with --check exit 1 if it differs from what would be written."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the file is out of date")
    args = parser.parse_args()
    text = render_types()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current.replace("\r\n", "\n") != text:
            print(f"{TARGET} is out of date. Run: python scripts/export_contract.py")
            return 1
        print("types.ts is up to date")
        return 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
