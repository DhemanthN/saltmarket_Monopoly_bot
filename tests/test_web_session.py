import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.game import Game
from saltmarket.engine.state import IllegalMoveError
from saltmarket.rl import encoding as enc
from saltmarket.sim.digest import game_digest
from saltmarket.web import contract as c
from saltmarket.web.seats import HumanSeat
from saltmarket.web.session import GameSession

smoke = pytest.mark.smoke
MAX_DECISIONS = 120
SHORT_SEED = 5


def chooser(decision: c.Decision) -> int:
    return decision.legal[0].id


def drive(session: GameSession) -> int:
    session.start()
    count = 0
    while (decision := session.current()) is not None:
        assert count < MAX_DECISIONS, "game too long for a test"
        assert session.submit(chooser(decision)).ok
        count += 1
    return count


def illegal_id(decision: c.Decision) -> int:
    legal = {a.id for a in decision.legal}
    return next(i for i in range(enc.NUM_ACTIONS) if i not in legal)


@settings(max_examples=15, deadline=None, suppress_health_check=list(HealthCheck))
@given(
    seed=st.integers(0, 10_000),
    seats=st.sampled_from([["human", "balanced"], ["human", "ppo"]]),
    data=st.data(),
)
def test_human_only_gets_legal_actions(seed, seats, data):
    session = GameSession(seed, seats)
    session.start()
    steps = 0
    while (decision := session.current()) is not None and steps < 25:
        ids = [a.id for a in decision.legal]
        assert ids and len(ids) == len(set(ids))
        assert all(0 <= i < enc.NUM_ACTIONS for i in ids)
        assert decision.seat == 0
        assert session.submit(data.draw(st.sampled_from(ids))).ok
        steps += 1


@smoke
def test_illegal_submit_rejected_and_changes_nothing():
    session = GameSession(3, ["human", "balanced"])
    session.start()
    decision = session.current()
    events = session.events()
    assert session.submit(illegal_id(decision)) == c.SubmitResult(False, "illegal")
    assert session.submit(-1) == c.SubmitResult(False, "illegal")
    assert session.current() == decision
    assert session.events() == events


@smoke
def test_submit_before_start_and_after_game_over():
    assert GameSession(3, ["human", "balanced"]).submit(0) == c.SubmitResult(
        False, "not_your_turn"
    )
    seats = ["human", "balanced"]
    done = GameSession(SHORT_SEED, seats)
    drive(done)
    assert done.result is not None
    assert done.submit(0) == c.SubmitResult(False, "game_over")


@smoke
def test_human_seat_in_plain_game_rejects_illegal_answer():
    game = Game([HumanSeat(illegal_id), make_any_bot("balanced")], 1)
    with pytest.raises(IllegalMoveError):
        game.play()


@smoke
def test_round_trip_matches_direct_engine_run():
    seats = ["human", "balanced"]
    seed = SHORT_SEED
    direct = Game([HumanSeat(chooser), make_any_bot("balanced")], seed, record_log=True)
    result = direct.play()
    session = GameSession(seed, seats)
    drive(session)
    assert session.result == result
    assert session.fingerprint() == game_digest(direct)


@smoke
def test_all_bot_session_matches_direct_run():
    seats = ["balanced", "balanced"]
    session = GameSession(5, seats)
    session.start()
    assert session.current() is None
    direct = Game([make_any_bot(s) for s in seats], 5, record_log=True)
    result = direct.play()
    assert session.result == result
    assert session.fingerprint() == game_digest(direct)


def _no_tuples(value) -> bool:
    if isinstance(value, tuple):
        return False
    if isinstance(value, dict):
        return all(_no_tuples(v) for v in value.values())
    if isinstance(value, list):
        return all(_no_tuples(v) for v in value)
    return True


@smoke
def test_event_json_and_ordering():
    session = GameSession(7, ["balanced", "balanced", "balanced"])
    session.start()
    events = session.events()
    encoded = [c.to_json(e) for e in events]
    assert all(_no_tuples(e) for e in encoded)
    assert not any("_" in key for e in encoded for key in e)
    assert json.loads(json.dumps(encoded)) == encoded
    for index, event in enumerate(events):
        assert event.seq == index
    turns = [e.turn for e in events]
    assert turns == sorted(turns)
    assert session.events(10) == events[10:]
    assert session.events(len(events)) == []
    last = events[-1]
    assert isinstance(last, c.GameOver)
    assert last.winner == session.result.winner


@smoke
@pytest.mark.parametrize(
    "seed,seats",
    [
        (1, ["balanced", "balanced"]),
        (2, ["balanced", "balanced", "balanced"]),
        (3, ["balanced", "balanced", "balanced", "balanced"]),
    ],
)
def test_event_reducer_reproduces_final_state(seed, seats):
    session = GameSession(seed, seats)
    session.start()
    cash: dict[int, int] = {}
    owner: dict[int, int | None] = {}
    level: dict[int, int] = {}
    mortgaged: dict[int, bool] = {}
    for e in session.events():
        if isinstance(e, c.CashChange):
            cash[e.seat] = e.balance
        elif isinstance(e, c.OwnerChange):
            owner[e.space] = e.seat
        elif isinstance(e, c.LevelChange):
            level[e.space] = e.level
        elif isinstance(e, c.MortgageChange):
            mortgaged[e.space] = e.t == "mortgage"
    final = session.final_state()
    for seat, balance in cash.items():
        assert balance == final["cash"][seat]
    for space, value in enumerate(final["owner"]):
        expected = None if value is None or value < 0 else value
        assert owner.get(space) == expected
    for space, value in enumerate(final["level"]):
        assert level.get(space, 0) == value
    for space, value in enumerate(final["mortgaged"]):
        assert mortgaged.get(space, False) == bool(value)


@pytest.mark.parametrize(
    "seats",
    [["human", "ppo"], ["human", "dqn"], ["human", "ppo", "balanced", "expert"]],
)
def test_agent_explanations(seats):
    session = GameSession(SHORT_SEED, seats)
    drive(session)
    seen = 0
    for e in session.events():
        if not isinstance(e, c.DecisionMade):
            continue
        kind = seats[e.seat]
        if kind == "human":
            assert e.explanation is None
            continue
        if kind not in ("ppo", "dqn"):
            continue
        seen += 1
        ex = e.explanation
        assert ex.agent == kind
        assert 1 <= len(ex.top) <= 3
        assert ex.top[0].id == e.action
        assert ex.value is not None
        if kind == "ppo":
            probs = [t.prob for t in ex.top]
            assert all(t.q is None for t in ex.top)
            assert all(p is not None and 0 <= p <= 1 for p in probs)
            assert probs == sorted(probs, reverse=True)
        else:
            assert all(t.q is not None and t.prob is None for t in ex.top)
    assert seen >= 1


@smoke
def test_labels_non_empty():
    checked = 0
    for seed in range(3):
        session = GameSession(seed, ["human", "balanced", "balanced"])
        session.start()
        for _ in range(30):
            decision = session.current()
            if decision is None:
                break
            assert all(a.label.strip() for a in decision.legal)
            checked += 1
            session.submit(chooser(decision))
    assert checked > 10


def test_dqn_is_limited_to_two_player_tables():
    with pytest.raises(ValueError, match="2-player"):
        GameSession(1, ["human", "dqn", "balanced"])
