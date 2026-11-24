"""Package the engine, board data and model weights for the browser runtime (Pyodide).

Writes ``web/public/runtime/app.<hash>.zip``, one ``model.<name>.<hash>.npz`` per weights file and
``web/public/runtime/manifest.json``. The zip unpacks to ``/app`` inside Pyodide as
``src/saltmarket/...`` and ``data/*.json``. The worker puts each model it needs at
``/app/models/<name>.npz``, so ``paths.MODELS`` finds it with no code change. Models sit outside
the zip because float weights do not compress and a game uses only one or two of them; a visitor
downloads just the opponent they pick. Each hash changes whenever its input changes, so browsers
never keep a stale engine. Standard library only, so it runs wherever Python does.

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
    """Return (name inside the zip, source path) for every code and data file, in a stable order."""
    files = [
        (p.relative_to(ROOT).as_posix(), p)
        for p in sorted((ROOT / "src" / "saltmarket").rglob("*.py"))
    ]
    files += [(p.relative_to(ROOT).as_posix(), p) for p in sorted((ROOT / "data").glob("*.json"))]
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


def model_files() -> dict[str, tuple[str, bytes]]:
    """Return ``{model name: (hashed file name, bytes)}`` for every weights file."""
    out = {}
    for filename in MODELS:
        data = (ROOT / "models" / filename).read_bytes()
        stem = filename.removesuffix(".npz")
        out[stem] = (f"model.{stem}.{hashlib.sha256(data).hexdigest()[:12]}.npz", data)
    return out


def main() -> int:
    """Build the bundle, or with ``--check`` report whether the built one is current."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the output is stale")
    args = parser.parse_args()

    data = build_zip()
    digest = hashlib.sha256(data).hexdigest()
    name = f"app.{digest[:12]}.zip"
    models = model_files()
    manifest = {
        "bundle": name,
        "sha256": digest,
        "bytes": len(data),
        "models": {stem: {"file": file, "bytes": len(blob)} for stem, (file, blob) in models.items()},
    }
    manifest_path = OUT / "manifest.json"

    if args.check:
        current = manifest_path.exists() and json.loads(manifest_path.read_text()) == manifest
        built = [name] + [file for file, _ in models.values()]
        if not current or not all((OUT / f).exists() for f in built):
            print("web runtime bundle is stale: run python scripts/build_web_runtime.py")
            return 1
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    keep = {name} | {file for file, _ in models.values()}
    for old in [*OUT.glob("app.*.zip"), *OUT.glob("model.*.npz")]:
        if old.name not in keep:
            old.unlink()
    (OUT / name).write_bytes(data)
    for file, blob in models.values():
        (OUT / file).write_bytes(blob)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {name} ({len(data) / 1e6:.1f} MB) and {len(models)} model files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
