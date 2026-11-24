"""Full seeded games through the live-play path for every table the site offers."""

import json
from dataclasses import dataclass

import pytest

from saltmarket.rl import encoding as enc
from saltmarket.web.live import play_live

TABLES = {
    "2p_ppo": (101, ("ppo", "balanced")),
    "2p_dqn": (102, ("dqn", "expert")),
    "2p_bots": (103, ("expert", "balanced")),
    "4p_ppo": (104, ("ppo", "balanced", "expert", "always_buy")),
    "4p_bots": (105, ("expert", "balanced", "always_buy", "expert")),
}
HUMAN_TABLE = (106, ("human", "ppo", "balanced", "expert"))


@dataclass
class Played:
    events: list[dict]
    summary: dict
    asked: int


def scripted(decision_json: str) -> int:
    """Answer like a cautious person: say yes, else pass, else bid, else the first choice."""
    legal = [a["id"] for a in json.loads(decision_json)["legal"]]
    for wanted in (enc.YES, enc.PASS, enc.BID):
        if wanted in legal:
            return wanted
    return legal[0]


def play(seed: int, seats: tuple[str, ...]) -> Played:
    events: list[dict] = []
    asked = 0

    def ask(decision_json: str) -> int:
        nonlocal asked
        asked += 1
        return scripted(decision_json)

    def emit(batch: str) -> None:
        events.extend(json.loads(batch))

    summary = json.loads(play_live(seed, seats, ask, emit))
    return Played(events, summary, asked)


def reduce_events(events: list[dict], seats: int, spaces: int) -> dict:
    """Rebuild cash, owners, levels and mortgages from events alone."""
    cash: dict[int, int] = {}
    owner: dict[int, int | None] = {}
    level: dict[int, int] = {}
    mortgaged: dict[int, bool] = {}
    for e in events:
        kind = e["t"]
        if kind == "cash":
            cash[e["seat"]] = e["balance"]
        elif kind == "owner":
            owner[e["space"]] = e["seat"]
        elif kind in ("build", "sell"):
            level[e["space"]] = e["level"]
        elif kind in ("mortgage", "unmortgage"):
            mortgaged[e["space"]] = kind == "mortgage"
    return {
        "cash": cash,
        "owner": [owner.get(i) for i in range(spaces)],
        "level": [level.get(i, 0) for i in range(spaces)],
        "mortgaged": [mortgaged.get(i, False) for i in range(spaces)],
    }


def check_game(game: Played, seats: int) -> None:
    events = game.events
    assert events, "no events were emitted"
    assert [e["seq"] for e in events] == list(range(len(events)))
    turns = [e["turn"] for e in events]
    assert turns == sorted(turns)
    assert events[-1]["t"] == "game_over"
    assert sum(e["t"] == "game_over" for e in events) == 1
    result = game.summary["result"]
    assert events[-1]["winner"] == result["winner"]
    assert events[-1]["turns"] == result["turns"]
    final = game.summary["finalState"]
    assert len(final["cash"]) == seats
    assert game.summary["fingerprint"]
    rebuilt = reduce_events(events, seats, len(final["owner"]))
    for seat, balance in rebuilt["cash"].items():
        assert balance == final["cash"][seat]
    expected_owner = [None if v is None or v < 0 else v for v in final["owner"]]
    assert rebuilt["owner"] == expected_owner
    assert rebuilt["level"] == final["level"]
    assert rebuilt["mortgaged"] == [bool(v) for v in final["mortgaged"]]


@pytest.mark.parametrize("name", TABLES)
def test_table_finishes_and_matches_reducer(name: str) -> None:
    seed, seats = TABLES[name]
    game = play(seed, seats)
    assert game.asked == 0
    check_game(game, len(seats))


def test_four_player_table_with_scripted_human() -> None:
    seed, seats = HUMAN_TABLE
    game = play(seed, seats)
    assert game.asked > 0
    decisions = [e for e in game.events if e["t"] == "decision"]
    assert len(decisions) >= game.asked
    check_game(game, len(seats))


@pytest.mark.parametrize("name", ["2p_ppo", "2p_dqn", "4p_bots"])
def test_same_seed_gives_same_fingerprint(name: str) -> None:
    seed, seats = TABLES[name]
    first, second = play(seed, seats), play(seed, seats)
    assert first.summary["fingerprint"] == second.summary["fingerprint"]
    assert first.events == second.events


def test_different_seeds_differ() -> None:
    seed, seats = TABLES["2p_bots"]
    assert play(seed, seats).summary["fingerprint"] != play(seed + 1, seats).summary["fingerprint"]


DQN_BAD_TABLES = [("dqn", "balanced", "expert"), ("dqn",) * 4, ("human", "dqn", "ppo")]


@pytest.mark.smoke
@pytest.mark.parametrize("seats", DQN_BAD_TABLES)
def test_dqn_above_two_players_raises(seats: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="2-player"):
        play_live(1, seats, scripted, lambda _: None)
