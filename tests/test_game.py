import pytest

from conftest import give, set_cash
from saltmarket.bots.base import Strategy
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation, LiquidationKind
from saltmarket.engine.cards import CardEffect, default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.game import Game
from saltmarket.engine.invariants import check_invariants
from saltmarket.engine.state import IllegalMoveError
from saltmarket.engine.trade import TradeOffer

pytestmark = pytest.mark.smoke


class ScriptedDice:
    def __init__(self, *rolls):
        self.rolls = list(rolls)

    def roll(self):
        return self.rolls.pop(0)


class Buyer(Strategy):
    def should_buy(self, state, index):
        return True


class Bidder(Strategy):
    def __init__(self, limit):
        self.limit = limit

    def auction_bid(self, state, index):
        return min(self.limit, state.players[self.me].cash)


class Jailbird(Strategy):
    def __init__(self, choice):
        self.choice = choice

    def brig_choice(self, state):
        return self.choice


def make_game(*rolls, strategies=None, **config):
    return Game(
        strategies or [Strategy(), Strategy()],
        seed=0,
        config=GameConfig(**config),
        dice=ScriptedDice(*rolls),
        debug=True,
        record_log=True,
    )


def card(card_id):
    return next(c for deck in default_cards().values() for c in deck if c.id == card_id)


def at(game, seat=0, position=0):
    player = game.state.players[seat]
    player.position = position
    return player


# Movement and salary


def test_roll_moves_player():
    game = make_game((2, 4))
    player = at(game)
    game.take_turn(player)
    assert player.position == 6


def test_passing_start_pays_salary():
    game = make_game((2, 4))
    player = at(game, position=39)
    game.take_turn(player)
    assert player.position == 5
    assert player.cash == 1400 + 180


def test_landing_exactly_on_start_pays_salary():
    game = make_game((1, 2))
    player = at(game, position=37)
    game.take_turn(player)
    assert player.position == 0
    assert player.cash == 1400 + 180


def test_tax_is_paid_to_bank():
    game = make_game((4, 5))
    player = at(game)
    game.take_turn(player)
    assert player.position == 9
    assert player.cash == 1400 - 120
    assert game.state.burned == 120


def test_calm_waters_does_nothing_by_default():
    game = make_game((1, 2))
    player = at(game, position=17)
    game.take_turn(player)
    assert player.position == 20 and player.cash == 1400


def test_jackpot_house_rule_collects_taxes():
    game = make_game((4, 5), (1, 2), calm_waters_jackpot=True)
    payer = at(game)
    game.take_turn(payer)
    assert game.state.jackpot == 120
    collector = at(game, seat=1, position=17)
    game.take_turn(collector)
    assert collector.cash == 1400 + 120 and game.state.jackpot == 0
    check_invariants(game.state)


# Doubles


def test_doubles_roll_again():
    game = make_game((1, 1), (1, 3))
    player = at(game)
    game.take_turn(player)
    assert player.position == 6
    assert not game.dice.rolls


def test_three_doubles_go_to_brig_without_moving_the_third_time():
    game = make_game((1, 1), (2, 2), (3, 3))
    player = at(game, position=23)
    game.take_turn(player)
    assert player.in_brig and player.position == game.state.board.brig


def test_third_double_landing_on_press_gang_still_goes_to_brig_once():
    game = make_game((1, 1), (2, 2), (3, 3))
    player = at(game, position=19)
    game.take_turn(player)
    assert player.in_brig and player.position == game.state.board.brig
    assert sum(1 for event in game.log if event[0] == "to_brig") == 1


def test_landing_on_press_gang_ends_doubles_streak():
    game = make_game((2, 2))
    player = at(game, position=27)
    game.take_turn(player)
    assert player.in_brig and player.position == game.state.board.brig


# Brig


def test_brig_pay_then_normal_roll():
    game = make_game((1, 2), strategies=[Jailbird(BrigChoice.PAY), Strategy()])
    player = at(game, position=14)
    player.in_brig = True
    game.take_turn(player)
    assert not player.in_brig and player.position == 17
    assert player.cash == 1400 - 60


def test_brig_pass_is_used_and_returned_to_deck():
    game = make_game((1, 2), strategies=[Jailbird(BrigChoice.USE_PASS), Strategy()])
    player = at(game, position=14)
    player.in_brig = True
    pass_card = card("tide-pass")
    game.state.decks["tide"]._cards.remove(pass_card)
    player.passes.append(pass_card)
    game.take_turn(player)
    assert not player.passes and not player.in_brig
    assert len(game.state.decks["tide"]) == 16


def test_using_a_pass_without_one_is_illegal():
    game = make_game(strategies=[Jailbird(BrigChoice.USE_PASS), Strategy()])
    player = at(game, position=14)
    player.in_brig = True
    with pytest.raises(IllegalMoveError):
        game.take_turn(player)


def test_paying_fine_without_cash_is_illegal():
    game = make_game(strategies=[Jailbird(BrigChoice.PAY), Strategy()])
    player = at(game, position=14)
    player.in_brig = True
    player.cash = 59
    with pytest.raises(IllegalMoveError):
        game.take_turn(player)


def test_brig_doubles_leave_without_another_roll():
    game = make_game((2, 2))
    player = at(game, position=14)
    player.in_brig = True
    game.take_turn(player)
    assert not player.in_brig and player.position == 18


def test_failed_brig_roll_stays():
    game = make_game((1, 2))
    player = at(game, position=14)
    player.in_brig = True
    game.take_turn(player)
    assert player.in_brig and player.brig_turns == 1 and player.position == 14


def test_third_failed_roll_forces_fine_and_moves():
    game = make_game((1, 2), (1, 2), (1, 2))
    player = at(game, position=14)
    player.in_brig = True
    for _ in range(3):
        game.take_turn(player)
    assert not player.in_brig and player.position == 17
    assert player.cash == 1400 - 60


def test_forced_fine_can_bankrupt():
    game = make_game((1, 2))
    player = at(game, position=14)
    player.in_brig = True
    player.brig_turns = 2
    player.cash = 10
    game.take_turn(player)
    assert player.bankrupt


# Buying, rent, auctions


def test_buy_when_strategy_agrees():
    game = make_game((4, 2), strategies=[Buyer(), Strategy()])
    player = at(game)
    game.take_turn(player)
    assert game.state.owner[6] == 0
    assert player.cash == 1400 - 90


def test_declined_space_goes_to_auction():
    game = make_game((4, 2), strategies=[Strategy(), Bidder(70)])
    game.take_turn(at(game))
    assert game.state.owner[6] == 1
    assert game.state.players[1].cash == 1400 - 10


def test_auction_winner_pays_just_over_second_highest():
    game = make_game(strategies=[Bidder(100), Bidder(60), Bidder(30)])
    game.auction(6)
    assert game.state.owner[6] == 0
    assert game.state.players[0].cash == 1400 - 65


def test_auction_price_never_exceeds_winning_bid():
    game = make_game(strategies=[Bidder(100), Bidder(100)])
    game.auction(6)
    assert game.state.players[0].cash == 1400 - 100


def test_auction_with_no_bids_leaves_space_unowned():
    game = make_game()
    game.auction(6)
    assert game.state.owner[6] is None


def test_bid_above_cash_is_illegal():
    class Overbidder(Strategy):
        def auction_bid(self, state, index):
            return state.players[self.me].cash + 1

    game = make_game(strategies=[Overbidder(), Strategy()])
    with pytest.raises(IllegalMoveError):
        game.auction(6)


def test_cannot_afford_price_goes_to_auction():
    game = make_game((4, 2), strategies=[Buyer(), Bidder(70)])
    player = at(game)
    player.cash = 80
    game.take_turn(player)
    assert game.state.owner[6] == 1


def test_rent_is_paid_to_owner():
    game = make_game((4, 2))
    give(game.state, 1, 6)
    game.take_turn(at(game))
    rent = game.state.board[6].rents[0]
    assert game.state.players[0].cash == 1400 - rent
    assert game.state.players[1].cash == 1400 + rent


def test_landing_on_own_space_is_free():
    game = make_game((4, 2))
    give(game.state, 0, 6)
    player = at(game)
    game.take_turn(player)
    assert player.cash == 1400


def test_landing_on_mortgaged_space_is_free():
    game = make_game((4, 2))
    give(game.state, 1, 6)
    game.state.mortgaged[6] = True
    player = at(game)
    game.take_turn(player)
    assert player.cash == 1400


def test_utility_rent_uses_the_roll():
    game = make_game((5, 2))
    give(game.state, 1, 12)
    player = at(game, position=5)
    game.take_turn(player)
    assert player.cash == 1400 - 5 * 7


# Cards


def test_move_to_card_pays_salary_when_passing_start():
    game = make_game()
    player = at(game, position=38)
    game.apply_card(player, card("tide-staghorn"), 0)
    assert player.position == 11 and player.cash == 1400 + 180


def test_move_to_card_resolves_destination_rent():
    game = make_game()
    give(game.state, 1, 39)
    player = at(game, position=3)
    game.apply_card(player, card("tide-pier"), 0)
    assert player.cash == 1400 - game.state.board[39].rents[0]


def test_back_three_never_pays_salary_and_resolves_space():
    game = make_game()
    player = at(game, position=3)
    game.apply_card(player, card("tide-back"), 0)
    assert player.position == 0 and player.cash == 1400


def test_forward_card_can_chain_into_a_second_card_draw():
    game = make_game()
    player = at(game, position=3)
    game.apply_card(player, card("tide-current"), 0)
    drawn = [event for event in game.log if event[0] == "card"]
    assert len(drawn) == 2


def test_nearest_ferry_pays_double_when_owned():
    game = make_game()
    give(game.state, 1, 5)
    player = at(game, position=3)
    game.apply_card(player, card("tide-ferry"), 7)
    assert player.position == 5 and player.cash == 1400 - 60


def test_nearest_ferry_wraps_and_pays_salary():
    game = make_game()
    player = at(game, position=38)
    game.apply_card(player, card("tide-ferry"), 7)
    assert player.position == 5 and player.cash == 1400 + 180


def test_nearest_ferry_can_be_bought_if_unowned():
    game = make_game(strategies=[Buyer(), Strategy()])
    player = at(game, position=3)
    game.apply_card(player, card("tide-ferry"), 7)
    assert game.state.owner[5] == 0


def test_nearest_utility_pays_ten_times_a_new_roll():
    game = make_game((3, 4))
    give(game.state, 1, 12)
    player = at(game, position=3)
    game.apply_card(player, card("tide-utility"), 2)
    assert player.position == 12 and player.cash == 1400 - 70


def test_nearest_mortgaged_utility_pays_nothing():
    game = make_game()
    give(game.state, 1, 12)
    game.state.mortgaged[12] = True
    player = at(game, position=3)
    game.apply_card(player, card("tide-utility"), 2)
    assert player.cash == 1400


def test_repairs_charge_depots_and_ports():
    game = make_game()
    give(game.state, 0, 6, 8)
    game.state.level[6], game.state.level[8] = 5, 4
    player = at(game)
    game.apply_card(player, card("tide-repairs"), 0)
    assert player.cash == 1400 - (4 * 30 + 120)


def test_pay_each_and_collect_each():
    game = make_game(strategies=[Strategy(), Strategy(), Strategy()])
    player = at(game)
    game.apply_card(player, card("tide-crew"), 0)
    assert [p.cash for p in game.state.players] == [1320, 1440, 1440]
    game.apply_card(player, card("ledger-launch"), 0)
    assert [p.cash for p in game.state.players] == [1380, 1410, 1410]


def test_go_to_brig_card_does_not_pay_salary():
    game = make_game()
    player = at(game, position=33)
    game.apply_card(player, card("ledger-brig"), 0)
    assert player.in_brig and player.cash == 1400


def test_every_card_effect_has_a_handler():
    game = make_game()
    assert set(game._card_handlers) == set(CardEffect)


# Debts and bankruptcy


def test_debt_triggers_strategy_liquidation():
    class Seller(Strategy):
        def raise_cash(self, state, amount):
            yield Liquidation(LiquidationKind.MORTGAGE, 6)

    game = make_game(strategies=[Seller(), Strategy()])
    give(game.state, 0, 6)
    player = at(game)
    player.cash = 10
    assert game.charge(player, 50, None)
    assert game.state.mortgaged[6] and player.cash == 5


def test_game_forces_liquidation_when_strategy_does_nothing():
    game = make_game()
    give(game.state, 0, 6, 8)
    game.state.level[6] = game.state.level[8] = 1
    game.state.depots_left -= 2
    player = at(game)
    player.cash = 0
    assert game.charge(player, 100, None)
    assert not player.bankrupt
    assert game.state.level[6] == 0


def test_bankruptcy_to_player_transfers_assets_and_charges_interest():
    game = make_game()
    state = game.state
    give(state, 0, 6, 8, 5)
    state.level[6] = state.level[8] = 1
    state.depots_left -= 2
    state.mortgaged[5] = True
    pass_card = card("ledger-pass")
    state.decks["ledger"]._cards.remove(pass_card)
    debtor, creditor = state.players
    debtor.passes.append(pass_card)
    set_cash(state, 0, 7)
    assert not game.charge(debtor, 10_000, creditor)
    assert debtor.bankrupt and debtor.cash == 0
    assert state.owner[6] == state.owner[8] == state.owner[5] == 1
    assert state.level[6] == 0 and state.depots_left == state.config.total_depots
    assert state.mortgaged[5]
    assert creditor.passes == [pass_card]
    assert creditor.cash == 1400 + 7 + 50 - 9
    check_invariants(state)


def test_bankruptcy_to_bank_auctions_spaces_unmortgaged():
    game = make_game(strategies=[Strategy(), Bidder(200), Strategy()])
    state = game.state
    give(state, 0, 6, 5)
    state.mortgaged[5] = True
    debtor = state.players[0]
    set_cash(state, 0, 0)
    assert not game.charge(debtor, 10_000, None)
    assert state.owner[6] == state.owner[5] == 1
    assert not state.mortgaged[5]
    check_invariants(state)


def test_bankrupt_to_bank_returns_pass_to_deck():
    game = make_game()
    state = game.state
    pass_card = card("tide-pass")
    state.decks["tide"]._cards.remove(pass_card)
    state.players[0].passes.append(pass_card)
    state.players[0].cash = 0
    game.charge(state.players[0], 10, None)
    assert len(state.decks["tide"]) == 16


def test_bankrupt_mid_card_pay_each_stops_paying():
    game = make_game(strategies=[Strategy(), Strategy(), Strategy()])
    player = at(game)
    set_cash(game.state, 0, 50)
    game.apply_card(player, card("tide-crew"), 0)
    state = game.state
    assert player.bankrupt
    assert [p.cash for p in state.players] == [0, 1440, 1410]
    check_invariants(state)


def test_collect_each_can_bankrupt_other_player_to_card_holder():
    game = make_game()
    player, other = game.state.players
    other.cash = 5
    game.apply_card(player, card("ledger-launch"), 0)
    assert other.bankrupt and player.cash == 1405


def test_repairs_debt_forces_selling_buildings():
    game = make_game()
    state = game.state
    give(state, 0, 6, 8)
    state.level[6] = state.level[8] = 5
    state.ports_left -= 2
    player = at(game)
    set_cash(state, 0, 0)
    game.apply_card(player, card("tide-repairs"), 0)
    assert not player.bankrupt
    assert state.level[6] == 0 and state.ports_left == state.config.total_ports
    check_invariants(state)


def test_creditor_can_be_bankrupted_by_inherited_mortgage_interest():
    game = make_game(strategies=[Strategy(), Strategy(), Strategy()])
    state = game.state
    give(state, 0, 5)
    state.mortgaged[5] = True
    debtor, creditor, _ = state.players
    set_cash(state, 0, 0)
    set_cash(state, 1, 0)
    assert not game.charge(debtor, 1000, creditor)
    assert creditor.bankrupt
    assert state.owner[5] is None
    check_invariants(state)


def test_rolling_stops_when_player_goes_bankrupt_on_doubles():
    game = make_game((2, 2), strategies=[Strategy(), Strategy(), Strategy()])
    give(game.state, 1, 4)
    player = at(game)
    player.cash = 0
    game.take_turn(player)
    assert player.bankrupt


# Trades and whole games


def test_trade_runs_through_manage_phase():
    class Proposer(Strategy):
        def propose_trade(self, state):
            if state.owner[6] == self.me:
                return TradeOffer(self.me, 1, give_spaces=(6,), take_cash=100)
            return None

    class Accepter(Strategy):
        def accept_trade(self, state, offer):
            return True

    game = make_game((1, 2), strategies=[Proposer(), Accepter()])
    give(game.state, 0, 6)
    player = at(game, position=17)
    game.take_turn(player)
    assert game.state.owner[6] == 1


def test_invalid_trade_proposal_is_illegal():
    class Cheater(Strategy):
        def propose_trade(self, state):
            return TradeOffer(self.me, 1, take_spaces=(6,))

    game = make_game(strategies=[Cheater(), Strategy()])
    with pytest.raises(IllegalMoveError):
        game.take_turn(at(game))


def test_trade_proposals_are_limited_per_phase():
    calls = []

    class Spammer(Strategy):
        def propose_trade(self, state):
            calls.append(1)
            return TradeOffer(self.me, 1, give_cash=1)

    game = make_game((1, 2), strategies=[Spammer(), Strategy()], max_trade_proposals=2)
    game.take_turn(at(game, position=17))
    assert len(calls) == 4


def test_turn_cap_ends_game_with_richest_winner():
    game = Game([Strategy(), Strategy()], seed=3, config=GameConfig(turn_cap=50), debug=True)
    set_cash(game.state, 1, 1900)
    result = game.play()
    assert result.hit_cap and result.turns == 50
    assert result.winner == max(range(2), key=lambda p: result.net_worths[p])


def test_last_player_standing_wins():
    game = make_game()
    game.state.players[0].cash = 0
    game.charge(game.state.players[0], 10, None)
    result = game.play()
    assert result.winner == 1 and not result.hit_cap and result.bankrupt == (True, False)


def test_net_worth_helper_counts_for_winner():
    game = make_game()
    give(game.state, 0, 39)
    assert rules.net_worth(game.state, 0) == 1400 + 420
