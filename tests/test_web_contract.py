import json
import sys
from pathlib import Path

import pytest

from saltmarket.web import contract as c
from saltmarket.web.export_ts import render_types
from saltmarket.web.session import GameSession

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "fixtures"
EVENT_BY_TAG = {
    tag: cls
    for cls in c.EVENT_TYPES
    for tag in (
        cls.__dataclass_fields__["t"].type.__args__
    )
}


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_types_ts_matches_python_contract():
    written = (ROOT / "web" / "src" / "contract" / "types.ts").read_text(encoding="utf-8")
    assert written.replace("\r\n", "\n") == render_types()


def test_fixture_index_lists_five_existing_files():
    index = json.loads((FIXTURES / "index.json").read_text(encoding="utf-8"))
    assert len(index) == 5
    assert all((FIXTURES / entry["file"]).exists() for entry in index)
    seats = [seat for entry in index for seat in entry["seats"]]
    assert "ppo" in seats and "dqn" in seats


@pytest.mark.parametrize("file", sorted(p.name for p in FIXTURES.glob("*_*.json")))
def test_fixture_events_match_the_schema(file):
    game = load(file)
    for index, event in enumerate(game["events"]):
        cls = EVENT_BY_TAG[event["t"]]
        expected = {c.camel(name) for name in cls.__dataclass_fields__}
        assert set(event) == expected
        assert event["seq"] == index
    assert game["events"][-1]["t"] == "game_over"


def test_covering_fixture_has_auction_trade_and_bankruptcy():
    seen = {e["t"] for e in load("bots_3p.json")["events"]}
    assert {"auction_win", "trade_result", "bankrupt"} <= seen


def test_fixture_replays_through_game_session():
    game = load("vs_ppo_2p.json")
    session = GameSession(game["config"]["seed"], game["config"]["seats"])
    session.start()
    for action in game["answers"]:
        assert session.submit(action).ok
    assert session.current() is None
    assert c.to_json(session.events()) == game["events"]
    assert session.fingerprint() == game["fingerprint"]


def test_export_script_check_passes(monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import export_contract

    monkeypatch.setattr(sys, "argv", ["export_contract.py", "--check"])
    assert export_contract.main() == 0
