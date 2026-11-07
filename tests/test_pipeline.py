import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.smoke


def load_script():
    spec = importlib.util.spec_from_file_location(
        "reproduce_all", ROOT / "scripts" / "reproduce_all.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["FULL", "QUICK"])
def test_every_step_calls_a_real_script(name):
    module = load_script()
    for step in module.build_steps(getattr(module, name)):
        assert (ROOT / "scripts" / step[0]).exists()


def test_training_comes_before_evaluation_and_analysis_is_last():
    module = load_script()
    order = [step[0] for step in module.build_steps(module.QUICK)]
    assert order.index("simulate.py") < order.index("analyze.py")
    assert max(i for i, s in enumerate(order) if s == "train.py") < order.index("evaluate.py")
    assert order[-1] == "analyze.py"


def test_quick_output_is_separate_from_real_results():
    module = load_script()
    assert module.QUICK_OUTPUT != ROOT
    assert "quick_output/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
