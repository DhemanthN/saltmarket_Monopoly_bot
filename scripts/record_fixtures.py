"""Record full games as JSON fixtures for the web app, using a fixed script for the human.

The human is a simple deterministic player (see ``choose``), so each fixture lists the
answers it gave. Playing those answers back through ``GameSession`` gives the same events.
"""

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from saltmarket.paths import MODELS
from saltmarket.rl import encoding as enc
from saltmarket.sim.digest import game_digest
from saltmarket.web import contract as c
from saltmarket.web.live import final_state, result_view
from saltmarket.web.observed import ObservedGame
from saltmarket.web.seats import HUMAN, make_seat

FIXTURES = Path(__file__).resolve().parents[1] / "web" / "fixtures"


@dataclass(frozen=True, slots=True)
class FixtureSpec:
    """One game to record. Seeds are fixed so the files are reproducible."""

    name: str
    seed: int
    seats: tuple[str, ...]
    shows: str


SPECS = (
    FixtureSpec("vs_ppo_2p", 23, ("human", "ppo"), "a 2-player game against PPO"),
    FixtureSpec("vs_dqn_2p", 13, ("human", "dqn"), "a 2-player game against DQN"),
    FixtureSpec(
        "table_4p", 11, ("human", "ppo", "balanced", "expert"), "a 4-player table with PPO"
    ),
    FixtureSpec(
        "bots_3p", 11, ("human", "expert", "always_buy"),
        "an auction, a trade and a bankruptcy against bots",
    ),
    FixtureSpec("watch_2p", 5, ("expert", "balanced"), "a game with no human decisions"),
)


def _first(decision: c.Decision, *ids: int) -> int | None:
    legal = {action.id for action in decision.legal}
    return next((i for i in ids if i in legal), None)


def choose(decision: c.Decision) -> int:
    """Pick a legal action by a fixed rule: buy, bid low, build, trade, never sell.

    The rule is a pure function of the decision, so a recorded game replays exactly.
    """
    ids = [action.id for action in decision.legal]
    rules = {
        "buy": lambda: _first(decision, enc.YES),
        "auction": lambda: _first(decision, enc.BID),
        "build": lambda: next((i for i in ids if i != enc.PASS), None),
        "propose": lambda: next((i for i in ids if i >= enc.TRADE), None),
        "accept": lambda: _first(decision, enc.YES),
        "brig": lambda: _first(decision, enc.BRIG_PAY, enc.BRIG_ROLL),
        "unmortgage": lambda: _first(decision, enc.PASS),
        "liquidate": lambda: _first(decision, enc.PASS),
    }
    pick = rules.get(decision.kind, lambda: None)()
    return ids[0] if pick is None else pick


def record(spec: FixtureSpec) -> c.GameFixture:
    """Play one game with a scripted human and return everything about it."""
    answers: list[int] = []

    def answer(decision: c.Decision) -> int:
        answers.append(choose(decision))
        return answers[-1]

    strategies = [make_seat(kind, len(spec.seats), answer, MODELS) for kind in spec.seats]
    game = ObservedGame(strategies, spec.seed)
    result = game.play()
    game.finish(result)
    return c.GameFixture(
        name=spec.name,
        config=c.SessionConfig(spec.seed, spec.seats),
        answers=tuple(answers),
        events=tuple(game.events),
        result=result_view(result),
        final_state=final_state(game),
        fingerprint=game_digest(game),
    )


def coverage_problems(fixtures: list[c.GameFixture]) -> list[str]:
    """Return what the set lacks: PPO and DQN opponents, an auction, a trade, a bankruptcy."""
    problems = []
    if not any("ppo" in f.config.seats and HUMAN in f.config.seats for f in fixtures):
        problems.append("no game against PPO")
    if not any("dqn" in f.config.seats and HUMAN in f.config.seats for f in fixtures):
        problems.append("no game against DQN")
    for fixture in fixtures:
        seen = Counter(event.t for event in fixture.events)
        accepted = any(
            e.t == "trade_result" and e.accepted for e in fixture.events
        )
        if seen["auction_win"] and accepted and seen["bankrupt"]:
            return problems
    problems.append("no game with an auction, an accepted trade and a bankruptcy")
    return problems


def main() -> None:
    """Record every spec, check coverage, and write the files and an index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=FIXTURES)
    args = parser.parse_args()
    fixtures = [record(spec) for spec in SPECS]
    problems = coverage_problems(fixtures)
    if problems:
        raise SystemExit("Fixture set is incomplete: " + "; ".join(problems))
    args.out.mkdir(parents=True, exist_ok=True)
    index = []
    for spec, fixture in zip(SPECS, fixtures, strict=True):
        path = args.out / f"{spec.name}.json"
        text = json.dumps(c.to_json(fixture), separators=(",", ":"))
        path.write_text(text, encoding="utf-8", newline="\n")
        index.append(
            {
                "name": spec.name,
                "file": path.name,
                "shows": spec.shows,
                "seats": list(spec.seats),
                "seed": spec.seed,
                "turns": fixture.result.turns,
                "events": len(fixture.events),
                "humanDecisions": len(fixture.answers),
            }
        )
        print(f"{spec.name}: {len(fixture.events)} events, {path.stat().st_size // 1024} KB")
    (args.out / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
