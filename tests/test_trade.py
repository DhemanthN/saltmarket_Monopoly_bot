import pytest

from conftest import give
from saltmarket.engine import rules
from saltmarket.engine.cards import CardEffect
from saltmarket.engine.state import IllegalMoveError
from saltmarket.engine.trade import TradeOffer, execute_trade, is_valid_trade

pytestmark = pytest.mark.smoke


def brig_pass(state):
    return next(
        c for deck in state.decks.values() for c in deck._cards
        if c.effect == CardEffect.BRIG_PASS
    )


def test_swap_spaces_and_cash(state):
    give(state, 0, 6)
    give(state, 1, 8)
    start = [p.cash for p in state.players]
    execute_trade(state, TradeOffer(0, 1, give_spaces=(6,), take_spaces=(8,), give_cash=100))
    assert state.owner[6] == 1 and state.owner[8] == 0
    assert [p.cash for p in state.players] == [start[0] - 100, start[1] + 100]


def test_trade_brig_pass(state):
    state.players[1].passes.append(brig_pass(state))
    execute_trade(state, TradeOffer(0, 1, give_cash=50, take_passes=1))
    assert len(state.players[0].passes) == 1 and not state.players[1].passes


def test_receiver_of_mortgaged_space_pays_interest(state):
    give(state, 0, 6)
    state.mortgaged[6] = True
    cash = state.players[1].cash
    execute_trade(state, TradeOffer(0, 1, give_spaces=(6,)))
    assert state.mortgaged[6]
    assert state.players[1].cash == cash - rules.unmortgage_fee(state, 6)
    assert state.burned == rules.unmortgage_fee(state, 6)


@pytest.mark.parametrize(
    "offer",
    [
        TradeOffer(0, 0, give_cash=1),
        TradeOffer(0, 1),
        TradeOffer(0, 1, give_spaces=(8,)),
        TradeOffer(0, 1, take_spaces=(6,)),
        TradeOffer(0, 1, give_spaces=(6, 6)),
        TradeOffer(0, 1, give_cash=-5),
        TradeOffer(0, 1, take_cash=-5),
        TradeOffer(0, 1, give_cash=10**6),
        TradeOffer(0, 1, take_cash=10**6),
        TradeOffer(0, 1, give_passes=1),
        TradeOffer(0, 1, take_passes=1),
    ],
)
def test_invalid_offers(state, offer):
    give(state, 0, 6)
    assert not is_valid_trade(state, offer)
    with pytest.raises(IllegalMoveError):
        execute_trade(state, offer)


def test_cannot_trade_a_space_in_a_group_with_buildings(state):
    give(state, 0, 6, 8)
    state.level[8] = 1
    assert not is_valid_trade(state, TradeOffer(0, 1, give_spaces=(6,)))


def test_cannot_trade_with_bankrupt_player(state):
    state.players[1].bankrupt = True
    assert not is_valid_trade(state, TradeOffer(0, 1, give_cash=10))


def test_receiver_must_afford_mortgage_interest(state):
    give(state, 0, 6)
    state.mortgaged[6] = True
    state.players[1].cash = 0
    assert not is_valid_trade(state, TradeOffer(0, 1, give_spaces=(6,)))
    assert is_valid_trade(state, TradeOffer(0, 1, give_spaces=(6,), give_cash=20))
