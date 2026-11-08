"""Write or check exact fingerprints of seeded games.

Usage:
    python scripts/fingerprint_games.py --check    # compare against tests/data
    python scripts/fingerprint_games.py --write    # record the current engine's output

Only use --write when a rule change is intended to alter games. Performance work must
pass --check unchanged.
"""

import argparse
import json
import sys
from pathlib import Path

from saltmarket.bots.catalog import BOTS
from saltmarket.sim.fingerprint import fingerprint_schedule, game_fingerprint

GOLDEN = Path(__file__).resolve().parents[1] / "tests" / "data" / "golden_games.json"
TABLES = {2: 60, 4: 40}


def current_fingerprints() -> dict[str, list[dict]]:
    """Fingerprint the fixed schedule for every table size."""
    return {
        str(size): [game_fingerprint(m) for m in fingerprint_schedule(sorted(BOTS), games, size)]
        for size, games in TABLES.items()
    }


def main() -> None:
    """Write the golden file, or exit with an error if the engine no longer matches it."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    fingerprints = current_fingerprints()
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(fingerprints, indent=1) + "\n", encoding="utf-8")
        print(f"Wrote {sum(map(len, fingerprints.values()))} fingerprints to {GOLDEN}")
        return
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if fingerprints != expected:
        sys.exit("Fingerprints differ from tests/data/golden_games.json")
    print("All fingerprints match.")


if __name__ == "__main__":
    main()
