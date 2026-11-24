"""The blocking live path used by the browser worker matches the recorded desktop games."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from saltmarket.engine.state import IllegalMoveError
from saltmarket.web.live import play_live

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "fixtures"
FIXTURE_FILES = sorted(p.name for p in FIXTURES.glob("*_*.json"))


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run(fixture: dict, prefix: int | None = None) -> tuple[list[dict], dict, int]:
    """Play the fixture game, answering from its recorded answers. Return events, summary, asks."""
    answers = list(fixture["answers"])
    given = answers[:prefix] if prefix is not None else []
    queue = answers[len(given):]
    events: list[dict] = []
    asked = 0

    def ask(decision_json: str) -> int:
        nonlocal asked
        decision = json.loads(decision_json)
        assert decision["kind"]
        asked += 1
        return queue.pop(0)

    def emit(batch: str) -> None:
        events.extend(json.loads(batch))

    summary = json.loads(play_live(
        fixture["config"]["seed"], fixture["config"]["seats"], ask, emit, answers=given
    ))
    return events, summary, asked


@pytest.mark.parametrize("file", FIXTURE_FILES)
def test_live_game_matches_fixture(file: str) -> None:
    fixture = load(file)
    events, summary, asked = run(fixture)
    assert events == fixture["events"]
    assert [e["seq"] for e in events] == list(range(len(events)))
    assert summary["fingerprint"] == fixture["fingerprint"]
    assert summary["finalState"] == fixture["finalState"]
    assert summary["result"] == fixture["result"]
    assert asked == len(fixture["answers"])


def test_answer_prefix_resumes_the_same_game_without_asking() -> None:
    fixture = load("vs_ppo_2p.json")
    events, summary, asked = run(fixture, prefix=10)
    assert events == fixture["events"]
    assert summary["fingerprint"] == fixture["fingerprint"]
    assert asked == len(fixture["answers"]) - 10


def test_illegal_answer_is_refused() -> None:
    fixture = load("vs_ppo_2p.json")

    def ask(decision_json: str) -> int:
        legal = {a["id"] for a in json.loads(decision_json)["legal"]}
        return next(i for i in range(10_000) if i not in legal)

    with pytest.raises(IllegalMoveError):
        play_live(fixture["config"]["seed"], fixture["config"]["seats"], ask, lambda _: None)


def test_live_path_imports_no_tournament_dependencies() -> None:
    code = (
        "import sys, saltmarket.web.live\n"
        "bad = [m for m in ('tqdm', 'multiprocessing', 'torch', 'saltmarket.sim.tournament')"
        " if m in sys.modules]\n"
        "print(','.join(bad))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == ""
