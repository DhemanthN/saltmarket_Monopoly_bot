"""The browser runtime cannot import torch, tqdm or multiprocessing. Check statically."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
FORBIDDEN = {"torch", "tqdm", "multiprocessing", "pandas", "matplotlib", "gymnasium", "scipy"}


def _module_file(name: str) -> Path | None:
    base = SRC.joinpath(*name.split("."))
    for candidate in (base / "__init__.py", base.with_suffix(".py")):
        if candidate.exists():
            return candidate
    return None


def _import_closure(entry_dir: Path) -> tuple[set[str], set[str]]:
    """Return (saltmarket modules, external top-level packages) reachable from ``entry_dir``."""
    pending = [f"saltmarket.web.{p.stem}" for p in entry_dir.glob("*.py") if p.stem != "__init__"]
    seen: set[str] = set()
    external: set[str] = set()
    while pending:
        name = pending.pop()
        path = _module_file(name)
        if path is None or name in seen:
            continue
        seen.add(name)
        parent = name.rpartition(".")[0]
        if parent:
            pending.append(parent)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
            else:
                continue
            for item in names:
                if item.startswith("saltmarket"):
                    pending.append(item)
                else:
                    external.add(item.split(".")[0])
    return seen, external


def test_web_layer_imports_no_heavy_packages() -> None:
    modules, external = _import_closure(SRC / "saltmarket" / "web")
    assert external & FORBIDDEN == set()
    heavy = {"saltmarket.rl.ppo", "saltmarket.rl.train", "saltmarket.rl.dqn"}
    assert not heavy & modules
    light_only = ("saltmarket.analysis", "saltmarket.sim.tournament")
    assert not any(m.startswith(light_only) for m in modules)
