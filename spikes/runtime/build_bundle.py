"""Zip the engine package and data files for Pyodide, and copy the models next to them."""

import py_compile
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "bundle"
MODELS = ("two_player.npz", "dqn_two_player.npz")


def add_py(archive: zipfile.ZipFile, path: Path, name: str, compiled: bool) -> None:
    """Add a source file, plus an unchecked-hash .pyc next to it so Pyodide skips compiling."""
    archive.write(path, name)
    if compiled:
        tag = sys.implementation.cache_tag
        pyc = Path(name).parent / "__pycache__" / f"{Path(name).stem}.{tag}.pyc"
        temp = OUT / "_tmp.pyc"
        py_compile.compile(
            path, cfile=temp, doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
        )
        archive.write(temp, pyc.as_posix())
        temp.unlink()


def main() -> None:
    """Write ``bundle/app.zip`` laid out as ``src/saltmarket/...``, ``data/*.json``, ``spike/``."""
    OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT / "app.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        compiled = "--pyc" in sys.argv
        for path in sorted((ROOT / "src" / "saltmarket").rglob("*.py")):
            add_py(archive, path, path.relative_to(ROOT).as_posix(), compiled)
        for path in sorted((ROOT / "data").glob("*.json")):
            archive.write(path, path.relative_to(ROOT).as_posix())
        for path in sorted((HERE / "spike_py").glob("*.py")):
            add_py(archive, path, f"src/spike/{path.name}", compiled)
        archive.writestr("src/spike/__init__.py", "")
    for name in MODELS:
        shutil.copy(ROOT / "models" / name, OUT / name)
    shutil.copy(HERE / "fixtures" / "observations.npz", OUT / "observations.npz")
    print({p.name: p.stat().st_size for p in OUT.iterdir()})


if __name__ == "__main__":
    main()
