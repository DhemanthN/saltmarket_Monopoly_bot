"""Zip the engine, board data and model weights for the browser runtime (Pyodide).

Writes ``web/public/runtime/app.<hash>.zip`` and ``web/public/runtime/manifest.json``. The zip
unpacks to ``/app`` inside Pyodide as ``src/saltmarket/...``, ``data/*.json`` and
``models/*.npz``, so ``paths.MODELS`` and the board loader find their files with no code
change. The hash in the file name changes whenever any input changes, so browsers never keep a
stale engine. Standard library only, so it runs wherever Python does.

Usage: ``python scripts/build_web_runtime.py`` (``--check`` exits 1 if the output is stale).
"""

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "runtime"
MODELS = ("two_player.npz", "main.npz", "dqn_two_player.npz")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def inputs() -> list[tuple[str, Path]]:
    """Return (name inside the zip, source path) for every bundled file, in a stable order."""
    files = [
        (p.relative_to(ROOT).as_posix(), p)
        for p in sorted((ROOT / "src" / "saltmarket").rglob("*.py"))
    ]
    files += [(p.relative_to(ROOT).as_posix(), p) for p in sorted((ROOT / "data").glob("*.json"))]
    files += [(f"models/{name}", ROOT / "models" / name) for name in MODELS]
    return files


def build_zip() -> bytes:
    """Return the zip bytes. Fixed timestamps make the output identical for identical inputs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in inputs():
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def main() -> int:
    """Build the bundle, or with ``--check`` report whether the built one is current."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the output is stale")
    args = parser.parse_args()

    data = build_zip()
    digest = hashlib.sha256(data).hexdigest()
    name = f"app.{digest[:12]}.zip"
    manifest = {"bundle": name, "sha256": digest, "bytes": len(data)}
    manifest_path = OUT / "manifest.json"

    if args.check:
        current = manifest_path.exists() and json.loads(manifest_path.read_text()) == manifest
        if not current or not (OUT / name).exists():
            print("web runtime bundle is stale: run python scripts/build_web_runtime.py")
            return 1
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("app.*.zip"):
        if old.name != name:
            old.unlink()
    (OUT / name).write_bytes(data)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {name} ({len(data) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
