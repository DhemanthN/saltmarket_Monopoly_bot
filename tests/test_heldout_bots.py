import os
from pathlib import Path

import numpy as np
import pytest

from conftest import give, make_state
from saltmarket.bots.catalog import BOTS
from saltmarket.bots.forecast import chain_state, expected_landings, roll_distributions
from saltmarket.bots.heldout.adaptive import BALANCED, Finisher, PhaseShifter, ScoreAware
from saltmarket.bots.heldout.catalog import ALL_HELDOUT_BOTS, HELDOUT_BOTS
from saltmarket.bots.heldout.markov_aware import rent_at_risk
from saltmarket.bots.heldout.opponents import rival_progress
from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.registry import ALL_NAMED_BOTS, make_any_bot
from saltmarket.engine import bank
from saltmarket.engine.actions import BrigChoice, LiquidationKind
from saltmarket.engine.game import Game
from saltmarket.engine.trade import TradeOffer
from saltmarket.rl.train import CURRICULUM
from saltmarket.sim.fuzz import fuzz_bot_seeds, run_bot_fuzz

DOCS = Path(__file__).resolve().parents[1] / "docs" / "strategies.md"
smoke = pytest.mark.smoke
RIVAL_HALF_BOARD = (15, 17, 18, 21, 23, 24, 25, 26, 28, 29, 32, 34, 35, 37, 39)


def seated(name, seat=0):
    bot = make_any_bot(name)
    bot.reset(seat, np.random.default_rng(0))
    return bot


# Catalog and hold-out guarantees


@smoke
def test_fourteen_heldout_bots_with_unique_names():
    assert len(ALL_HELDOUT_BOTS) == len(HELDOUT_BOTS) == 14
    assert len(ALL_NAMED_BOTS) == len(BOTS) + len(HELDOUT_BOTS) == 40


@smoke
def test_heldout_bots_are_not_in_the_training_pool():
    assert not set(HELDOUT_BOTS) & set(BOTS)
    for stage in CURRICULUM:
        assert not set(stage.pool) & set(HELDOUT_BOTS), stage.name


@smoke
@pytest.mark.parametrize("name", sorted(HELDOUT_BOTS))
def test_every_heldout_bot_is_documented(name):
    assert f"### `{name}`" in DOCS.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", sorted(HELDOUT_BOTS))
def test_each_heldout_bot_plays_short_mixed_games(name):
    assert fuzz_bot_seeds(name, range(6), pool=sorted(ALL_NAMED_BOTS)).games == 6


@smoke
def test_heldout_games_are_deterministic():
    def play():
        names = ("reciprocator", "mortgage_flipper", "ambush_builder", "expert")
        game = Game([make_any_bot(n) for n in names], seed=11, record_log=True)
        game.play()
        return game.log

    assert play() == play()


@pytest.mark.slow
def test_no_two_of_the_forty_bots_play_identically():
    tables = (("swap_negotiator",), ("expert", "always_buy"), ("reciprocator", "random"))

    def fingerprint(name):
        logs = []
        for seed in range(6):
            for table in tables:
                game = Game([make_any_bot(n) for n in (name, *table)], seed=seed,
                            record_log=True)
                game.play()
                logs.append(repr(game.log))
        return hash(tuple(logs))

    assert len({fingerprint(name) for name in ALL_NAMED_BOTS}) == len(ALL_NAMED_BOTS)


@pytest.mark.slow
def test_every_heldout_bot_survives_1000_fuzz_games():
    summaries = run_bot_fuzz(
        1000, workers=os.cpu_count() or 1, names=sorted(HELDOUT_BOTS), pool=sorted(ALL_NAMED_BOTS)
    )
    assert [s.name for s in summaries] == sorted(HELDOUT_BOTS)
    assert all(s.games == 1000 for s in summaries)


# Forecasts


@smoke
def test_roll_distributions_are_probabilities(state):
    for distribution in roll_distributions(state, 0, 3):
        assert distribution.sum() == pytest.approx(1.0)
        assert (distribution >= 0).all()
    assert expected_landings(state, 0, 3).sum() == pytest.approx(3.0)


@smoke
def test_brig_players_start_from_a_brig_state(state):
    player = state.players[0]
    free = chain_state(player, state.config)
    player.in_brig, player.brig_turns = True, 1
    assert chain_state(player, state.config) != free
    assert chain_state(player, state.config) == 40 * state.config.max_doubles + 1


@smoke
def test_rent_at_risk_is_zero_without_rival_land(state):
    give(state, 0, 6, 8)
    assert rent_at_risk(state, 0, 2) == 0


# Adaptive bots


@smoke
def test_phase_shifter_grabs_then_consolidates_then_develops(state):
    bot = seated("phase_shifter")
    assert bot.posture(state) is PhaseShifter.GRAB
    state.players[0].cash = 420
    assert bot.should_buy(state, 39)

    give(state, 1, *RIVAL_HALF_BOARD)
    assert bot.posture(state) is PhaseShifter.CONSOLIDATE
    assert not bot.wants(state, 1)
    give(state, 0, 2)
    assert bot.wants(state, 1)

    give(state, 0, 6, 8, 5)
    assert bot.posture(state) is PhaseShifter.DEVELOP
    actions = list(bot.choose_liquidations(state))
    assert [(a.kind, a.index) for a in actions] == [
        (LiquidationKind.MORTGAGE, 2), (LiquidationKind.MORTGAGE, 5)
    ]


@smoke
def test_score_aware_protects_a_lead_and_gambles_from_behind(state):
    bot = seated("score_aware")
    assert bot.posture(state) is BALANCED
    give(state, 0, 37, 39)
    assert bot.posture(state) is ScoreAware.PROTECT
    state.players[0].cash = 90 + 349
    state.players[1].cash = 500
    assert bot.posture(state) is ScoreAware.PROTECT
    assert not bot.should_buy(state, 6)

    give(state, 1, 37, 39, 32, 34)
    state.players[0].cash = 90
    assert bot.posture(state) is ScoreAware.GAMBLE
    assert bot.should_buy(state, 6)


@smoke
def test_finisher_closes_only_when_a_rival_is_in_reach(state):
    bot = seated("finisher")
    give(state, 0, 37, 39)
    assert bot.posture(state) is Finisher.PATIENT
    assert bot.brig_choice(state) == BrigChoice.PAY

    state.level[37] = state.level[39] = 5
    assert bot.posture(state) is Finisher.CLOSE
    assert bot.brig_choice(state) == BrigChoice.ROLL


# Opponent models


@smoke
def test_rival_progress(state):
    assert rival_progress(state, 0, 23) == 0
    give(state, 1, 21)
    assert rival_progress(state, 0, 23) == pytest.approx(1 / 3)
    assert rival_progress(state, 1, 23) == 0


@smoke
def test_rival_watcher_contests_groups_rivals_are_collecting(state):
    bot = seated("rival_watcher")
    plain = bot.auction_bid(state, 23)
    give(state, 1, 21)
    assert bot.auction_bid(state, 23) == plain + int(210 / 3)
    state.players[0].cash = 210
    assert bot.should_buy(state, 23)
    assert not bot.should_buy(state, 6)


@smoke
def test_rival_watcher_refuses_to_hand_over_half_a_group(state):
    bot = seated("rival_watcher")
    give(state, 1, 21)
    give(state, 0, 23, 1)
    assert not bot.accept_trade(state, TradeOffer(1, 0, take_spaces=(23,), give_cash=1000))
    assert bot.accept_trade(state, TradeOffer(1, 0, take_spaces=(1,), give_cash=300))


@smoke
def test_leader_denier_shuns_the_leader(state):
    bot = seated("leader_denier")
    give(state, 0, 6)
    give(state, 1, 8, 39)
    assert not bot.accept_trade(state, TradeOffer(1, 0, take_spaces=(6,), give_cash=1000))
    assert bot.propose_trade(state) is None
    give(state, 0, 37, 32)
    assert bot.propose_trade(state) == TradeOffer(0, 1, take_spaces=(8,), give_cash=130)


@smoke
def test_leader_denier_bids_extra_against_the_leader(state):
    bot = seated("leader_denier")
    plain = bot.auction_bid(state, 23)
    give(state, 1, 21)
    assert bot.auction_bid(state, 23) == plain + 105


@smoke
def test_leader_denier_is_generous_to_trailing_players_at_crowded_tables():
    for players, expected in ((3, True), (2, False)):
        state = make_state(players)
        give(state, 0, 5)
        offer = TradeOffer(players - 1, 0, take_spaces=(5,), give_cash=160)
        assert seated("leader_denier").accept_trade(state, offer) is expected


@smoke
def test_cash_reader_sends_space_to_auction_when_rivals_are_broke(state):
    bot = seated("cash_reader")
    assert bot.should_buy(state, 39)
    state.players[1].cash = 50
    assert not bot.should_buy(state, 39)
    assert bot.auction_bid(state, 39) > 55


@smoke
def test_reciprocator_stops_offering_after_a_rejection_and_forgives(state):
    bot = seated("reciprocator")
    give(state, 0, 6)
    give(state, 1, 8)
    assert bot.propose_trade(state) == TradeOffer(0, 1, take_spaces=(8,), give_cash=120)
    assert bot.propose_trade(state) is None
    state.turn = bot.forgive_turns
    assert bot.propose_trade(state) == TradeOffer(0, 1, take_spaces=(8,), give_cash=120)


@smoke
def test_reciprocator_pays_more_to_partners_who_accept(state):
    bot = seated("reciprocator")
    give(state, 0, 6)
    give(state, 1, 8)
    bot.propose_trade(state)
    give(state, 0, 8)
    bot.propose_trade(state)
    assert bot.premium_for(state, 1) == pytest.approx(bot.trade_premium + bot.trusted_bonus)


@smoke
def test_reciprocator_holds_a_grudge_against_lowballers(state):
    bot = seated("reciprocator")
    give(state, 0, 5)
    lowball = TradeOffer(1, 0, take_spaces=(5,), give_cash=50)
    decent = TradeOffer(1, 0, take_spaces=(5,), give_cash=216)
    assert seated("reciprocator").accept_trade(state, decent)
    assert not bot.accept_trade(state, lowball)
    assert not bot.accept_trade(state, lowball)
    assert not bot.accept_trade(state, decent)


# Trading


@smoke
def test_swap_negotiator_offers_a_swap_a_plain_bot_accepts(state):
    bot = seated("swap_negotiator")
    give(state, 0, 6, 1, 2)
    give(state, 1, 8, 4)
    offer = bot.propose_trade(state)
    assert offer.give_spaces and offer.take_spaces
    responder = HeuristicBot()
    responder.reset(1, None)
    assert responder.accept_trade(state, offer)


@smoke
def test_mortgage_flipper_mortgages_then_sells_a_dead_lot(state):
    bot = seated("mortgage_flipper")
    give(state, 0, 21)
    give(state, 1, 23)
    assert bot.is_dead(state, 21)
    actions = list(bot.choose_liquidations(state))
    assert [(a.kind, a.index) for a in actions] == [(LiquidationKind.MORTGAGE, 21)]
    bank.mortgage(state, 0, 21)
    assert list(bot.choose_unmortgages(state)) == []

    offer = bot.propose_trade(state)
    assert offer == TradeOffer(0, 1, give_spaces=(21,), take_cash=int(210 * 0.9))
    responder = HeuristicBot()
    responder.reset(1, None)
    assert responder.accept_trade(state, offer)


@smoke
def test_mortgage_flipper_does_not_repeat_a_refused_offer(state):
    bot = seated("mortgage_flipper")
    give(state, 0, 21)
    give(state, 1, 23)
    bank.mortgage(state, 0, 21)
    assert bot.propose_trade(state) is not None
    assert bot.propose_trade(state) is None
    assert list(bot.choose_unmortgages(state)) == [21]


@smoke
def test_mortgage_flipper_keeps_lots_it_can_still_complete(state):
    bot = seated("mortgage_flipper")
    give(state, 0, 21, 23)
    give(state, 1, 24)
    assert not bot.is_dead(state, 21)


# Markov-aware bots


@smoke
def test_risk_manager_reserve_grows_with_nearby_rival_rent(state):
    bot = seated("risk_manager")
    assert bot.reserve_needed(state) == bot.min_reserve
    give(state, 1, 15, 17, 18)
    state.level[15] = state.level[17] = state.level[18] = 5
    state.players[0].position = 9
    assert bot.reserve_needed(state) > 500
    state.players[0].cash = 600
    assert not bot.should_buy(state, 39)
    assert bot.brig_choice(state) == BrigChoice.ROLL


@smoke
@pytest.mark.parametrize(("rival_position", "builds"), [(0, True), (9, False)])
def test_ambush_builder_builds_where_rivals_are_about_to_land(state, rival_position, builds):
    bot = seated("ambush_builder")
    give(state, 0, 6, 8)
    state.players[0].cash = 500
    state.players[1].position = rival_position
    assert (next(iter(bot.choose_builds(state)), None) is not None) is builds


@smoke
def test_ambush_builder_builds_anyway_when_flush(state):
    bot = seated("ambush_builder")
    give(state, 0, 6, 8)
    state.players[0].cash = 5000
    state.players[1].position = 9
    assert next(iter(bot.choose_builds(state)), None) is not None


@smoke
def test_npv_bidder_values_crowded_tables_and_early_games_more(state):
    bot = seated("npv_bidder")
    crowded = make_state(4)
    assert bot.value(crowded, 21) > bot.value(state, 21)
    early = bot.value(state, 21)
    state.turn = 10_000
    assert bot.value(state, 21) < early
    assert not bot.should_buy(state, 21)


@smoke
def test_npv_bidder_caps_its_bid(state):
    bot = seated("npv_bidder")
    crowded = make_state(4)
    state.players[0].cash = crowded.players[0].cash = 10_000
    assert bot.auction_bid(crowded, 1) == 50 * bot.max_bid_multiple


# Exploits


@smoke
def test_stalemate_seeker_never_trades_and_spoils_groups(state):
    bot = seated("stalemate_seeker")
    give(state, 0, 6)
    assert not bot.accept_trade(state, TradeOffer(1, 0, take_spaces=(6,), give_cash=1300))
    give(state, 1, 21)
    assert bot.auction_bid(state, 23) == 210 + 105
    give(state, 1, 15, 17)
    assert bot.auction_bid(state, 18) == 180 + 180


@smoke
def test_leveraged_buyer_fills_its_war_chest_during_the_land_grab(state):
    bot = seated("leveraged_buyer")
    give(state, 0, 5, 12, 21, 6)
    give(state, 1, 23)
    state.players[0].cash = 100
    mortgaged = []
    for action in bot.choose_liquidations(state):
        bank.mortgage(state, 0, action.index)
        mortgaged.append(action.index)
    assert mortgaged == [12, 5, 21]
    assert list(bot.choose_unmortgages(state)) == []


@smoke
def test_leveraged_buyer_stops_leveraging_after_the_land_grab(state):
    bot = seated("leveraged_buyer")
    give(state, 1, *RIVAL_HALF_BOARD, 1, 2, 4, 10)
    give(state, 0, 5)
    state.players[0].cash = 100
    assert list(bot.choose_liquidations(state)) == []

