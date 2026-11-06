from pathlib import Path

import pytest

from conftest import give, make_state
from saltmarket.bots import catalog
from saltmarket.bots.catalog import ALL_BOTS, BOTS, make_bot
from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.values import (
    blocks_rival,
    completes_group,
    highest_rival_rent,
    roi_scores,
    unowned_share,
)
from saltmarket.engine.actions import BrigChoice, LiquidationKind
from saltmarket.engine.game import Game
from saltmarket.engine.trade import TradeOffer
from saltmarket.sim.fuzz import fuzz_bot_seeds, run_bot_fuzz

DOCS = Path(__file__).resolve().parents[1] / "docs" / "strategies.md"
smoke = pytest.mark.smoke


def seated(bot, state, seat=0):
    bot.reset(seat, None)
    return bot


@smoke
def test_at_least_twenty_uniquely_named_bots():
    assert len(ALL_BOTS) >= 20
    assert len(BOTS) == len(ALL_BOTS)


@smoke
@pytest.mark.parametrize("name", sorted(BOTS))
def test_every_bot_is_documented(name):
    assert f"### `{name}`" in DOCS.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", sorted(BOTS))
def test_each_bot_plays_short_mixed_games(name):
    assert fuzz_bot_seeds(name, range(6)).games == 6


@smoke
def test_same_seed_is_deterministic_for_mixed_bots():
    def play():
        game = Game([make_bot(n) for n in ("expert", "random", "port_rush")], seed=5,
                    record_log=True)
        game.play()
        return game.log

    assert play() == play()


@pytest.mark.slow
def test_no_two_bots_play_identically():
    tables = (
        ("aggressive_trader",),
        ("expert", "always_buy"),
        ("monopoly_trader", "port_rush", "random"),
    )

    def fingerprint(name):
        logs = []
        for seed in range(6):
            for table in tables:
                bots = [make_bot(name), *(make_bot(n) for n in table)]
                game = Game(bots, seed=seed, record_log=True)
                game.play()
                logs.append(repr(game.log))
        return hash(tuple(logs))

    assert len({fingerprint(name) for name in BOTS}) == len(BOTS)


@smoke
def test_balanced_leaves_brig_even_late_in_the_game(state):
    bot = seated(HeuristicBot(), state)
    give(state, 1, *state.board.ownable)
    assert bot.brig_choice(state) == BrigChoice.PAY


@smoke
def test_roi_scores_cover_all_ownable_spaces(state):
    scores = roi_scores()
    assert set(scores) == set(state.board.ownable)
    assert all(score > 0 for score in scores.values())


@smoke
def test_unowned_share(state):
    assert unowned_share(state) == 1.0
    give(state, 0, *state.board.ownable)
    assert unowned_share(state) == 0.0


@smoke
def test_completes_group(state):
    give(state, 0, 6)
    assert completes_group(state, 0, 8)
    assert not completes_group(state, 0, 1)
    assert not completes_group(state, 0, 5)
    assert completes_group(state, 0, 1, also_owned=(2, 4))


@smoke
def test_blocks_rival(state):
    give(state, 1, 6)
    assert blocks_rival(state, 0, 8)
    assert not blocks_rival(state, 1, 8)
    assert not blocks_rival(state, 0, 1)


@smoke
def test_highest_rival_rent(state):
    assert highest_rival_rent(state, 0) == 0
    give(state, 1, 39)
    give(state, 0, 37)
    assert highest_rival_rent(state, 0) == state.board[39].rents[0]


@smoke
def test_buying_respects_cash_floor(state):
    bot = seated(HeuristicBot(), state)
    state.players[0].cash = 90 + 149
    assert not bot.should_buy(state, 6)
    state.players[0].cash = 90 + 150
    assert bot.should_buy(state, 6)


@smoke
def test_bid_never_exceeds_spendable_cash(state):
    bot = seated(HeuristicBot(), state)
    state.players[0].cash = 200
    assert bot.auction_bid(state, 39) == 50
    state.players[0].cash = 100
    assert bot.auction_bid(state, 39) == 0


@smoke
def test_never_buy_declines_everything(state):
    bot = seated(make_bot("never_buy"), state)
    assert not bot.should_buy(state, 6)
    assert bot.auction_bid(state, 6) == 0


@smoke
def test_auction_sniper_only_buys_at_auction(state):
    bot = seated(make_bot("auction_sniper"), state)
    assert not bot.should_buy(state, 6)
    assert bot.auction_bid(state, 6) == int(90 * 0.75)


@smoke
def test_specialist_targets_its_group(state):
    bot = seated(make_bot("amber_specialist"), state)
    assert bot.wants(state, 21)
    assert not bot.wants(state, 6)
    state.players[0].cash = 5000
    assert bot.wants(state, 6)


@smoke
def test_no_utilities_skips_utilities(state):
    bot = seated(make_bot("no_utilities"), state)
    assert not bot.wants(state, 12) and bot.wants(state, 5)


@smoke
@pytest.mark.parametrize(
    ("name", "index", "expected"),
    [("cheap_lots", 1, True), ("cheap_lots", 39, False),
     ("premium_lots", 1, False), ("premium_lots", 39, True)],
)
def test_price_band_bots(state, name, index, expected):
    assert seated(make_bot(name), state).wants(state, index) is expected


@smoke
def test_shortage_blocker_stops_at_four_depots(state):
    bot = seated(make_bot("shortage_blocker"), state)
    give(state, 0, 6, 8)
    state.players[0].cash = 10_000
    state.level[6] = state.level[8] = 4
    state.depots_left -= 8
    assert list(bot.choose_builds(state)) == []


@smoke
def test_three_depots_finishes_groups_before_going_higher(state):
    bot = seated(make_bot("three_depots"), state)
    give(state, 0, 6, 8, 37, 39)
    state.level[6] = state.level[8] = 3
    assert bot.level_cap(state) == 3
    state.level[37] = state.level[39] = 3
    assert bot.level_cap(state) == 5


@smoke
def test_port_rush_stays_on_the_developed_group(state):
    bot = seated(make_bot("port_rush"), state)
    give(state, 0, 6, 8, 37, 39)
    state.level[6] = state.level[8] = 2
    assert bot.build_choice(state, [6, 37]) == 6


@smoke
def test_rent_maximizer_picks_best_marginal_rent(state):
    bot = seated(make_bot("rent_maximizer"), state)
    best = max((6, 37), key=lambda i: (state.board[i].rents[1] - state.board[i].rents[0])
               / state.board[i].build_cost)
    assert bot.build_choice(state, [6, 37]) == best


@smoke
def test_aggressive_builder_mortgages_only_spare_spaces(state):
    bot = seated(make_bot("aggressive_builder"), state)
    give(state, 0, 6, 8, 5)
    actions = list(bot.choose_liquidations(state))
    assert [(a.kind, a.index) for a in actions] == [(LiquidationKind.MORTGAGE, 5)]


@smoke
def test_brig_stayer_rolls_late_but_leaves_early(state):
    bot = seated(make_bot("brig_stayer"), state)
    assert bot.brig_choice(state) == BrigChoice.PAY
    give(state, 1, *state.board.ownable)
    assert bot.brig_choice(state) == BrigChoice.ROLL


@smoke
def test_roi_buyer_wants_about_half_the_board(state):
    bot = seated(make_bot("roi_buyer"), state)
    wanted = sum(bot.wants(state, i) for i in state.board.ownable)
    assert len(state.board.ownable) // 2 <= wanted <= len(state.board.ownable) // 2 + 1


@smoke
def test_conservative_mortgager_sells_before_mortgaging(state):
    bot = seated(make_bot("conservative_mortgager"), state)
    give(state, 0, 6, 8, 5)
    state.level[6] = 1
    state.depots_left -= 1
    assert next(iter(bot.raise_cash(state, 100))).kind == LiquidationKind.SELL_BUILDING


@smoke
def test_default_bot_mortgages_before_selling(state):
    bot = seated(HeuristicBot(), state)
    give(state, 0, 6, 8, 5)
    state.level[6] = 1
    state.depots_left -= 1
    assert next(iter(bot.raise_cash(state, 100))).kind == LiquidationKind.MORTGAGE


@smoke
def test_group_blocker_pays_to_stop_rival(state):
    bot = seated(make_bot("group_blocker"), state)
    plain = bot.auction_bid(state, 8)
    give(state, 1, 6)
    assert bot.auction_bid(state, 8) == plain + 100


@smoke
def test_trader_offers_cash_for_last_lot(state):
    bot = seated(make_bot("monopoly_trader"), state)
    give(state, 0, 6)
    give(state, 1, 8)
    offer = bot.propose_trade(state)
    assert offer == TradeOffer(0, 1, take_spaces=(8,), give_cash=int(100 * 1.3))


@smoke
def test_non_trader_proposes_nothing(state):
    bot = seated(HeuristicBot(), state)
    give(state, 0, 6)
    give(state, 1, 8)
    assert bot.propose_trade(state) is None


@smoke
def test_swap_offered_when_cash_is_short(state):
    bot = seated(make_bot("aggressive_trader"), state)
    give(state, 0, 6, 1)
    give(state, 1, 8, 2, 4)
    state.players[0].cash = 100
    assert bot.propose_trade(state) == TradeOffer(0, 1, give_spaces=(6,), take_spaces=(2, 4))


@smoke
def test_accepts_good_cash_deal_and_rejects_bad_one(state):
    bot = seated(HeuristicBot(), state, seat=1)
    give(state, 1, 5)
    assert bot.accept_trade(state, TradeOffer(0, 1, take_spaces=(5,), give_cash=300))
    assert not bot.accept_trade(state, TradeOffer(0, 1, take_spaces=(5,), give_cash=100))


@smoke
def test_charges_premium_for_handing_over_a_group(state):
    bot = seated(HeuristicBot(), state, seat=1)
    give(state, 0, 6)
    give(state, 1, 8)
    assert not bot.accept_trade(state, TradeOffer(0, 1, take_spaces=(8,), give_cash=130))
    assert bot.accept_trade(state, TradeOffer(0, 1, take_spaces=(8,), give_cash=300))


@smoke
def test_values_completing_its_own_group(state):
    bot = seated(HeuristicBot(), state, seat=1)
    give(state, 0, 8)
    give(state, 1, 6)
    assert bot.accept_trade(state, TradeOffer(0, 1, give_spaces=(8,), take_cash=150))


@smoke
def test_expert_reserve_tracks_the_threat(state):
    bot = seated(make_bot("expert"), state)
    assert bot.cash_floor(state) == 50
    give(state, 1, *state.board.ownable)
    state.level[39] = state.level[37] = 5
    assert bot.cash_floor(state) == catalog.MAX_EXPERT_RESERVE


@smoke
def test_expert_bids_extra_to_finish_or_block_a_group(state):
    bot = seated(make_bot("expert"), state)
    plain = bot.auction_bid(state, 8)
    give(state, 1, 6)
    assert bot.auction_bid(state, 8) == plain + 50
    give(state, 0, 6)
    assert bot.auction_bid(state, 8) == plain + 100


@pytest.mark.slow
def test_every_bot_survives_1000_fuzz_games():
    summaries = run_bot_fuzz(1000, workers=20)
    assert len(summaries) == len(BOTS)
    assert all(s.games == 1000 for s in summaries)


def test_make_state_helper_supports_more_players():
    assert len(make_state(4).players) == 4
