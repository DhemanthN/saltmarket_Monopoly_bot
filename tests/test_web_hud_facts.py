import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location("export_hud_facts", ROOT / "scripts" / "export_hud_facts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_results_facts_file_matches_results() -> None:
    script = _load_script()
    current = script.TARGET.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert current == script.render()


def test_every_fact_names_its_table_size_and_pool() -> None:
    for fact in _load_script().build_facts():
        assert fact["players"] in (2, 3, 4)
        assert fact["games"] > 0 and fact["bots"] > 0
        assert fact["ciLow"] <= fact["winRate"] <= fact["ciHigh"]
