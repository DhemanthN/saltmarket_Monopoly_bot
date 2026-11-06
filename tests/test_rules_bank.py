import pytest

from conftest import give, make_state
from saltmarket.engine import bank, rules
from saltmarket.engine.state import IllegalMoveError

pytestmark = pytest.mark.smoke

KELP = (1, 2, 4)
REEF = (6, 8)
CROWN = (37, 39)


def test_base_rent_and_double_rent_for_full_group(state):
    give(state, 0, 6)
    assert rules.rent(state, 6, 7) == state.board[6].rents[0]
    give(state, 0, 8)
    assert rules.rent(state, 6, 7) == 2 * state.board[6].rents[0]


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_building_rent_replaces_double_rent(state, level):
    give(state, 0, *REEF)
    state.level[6] = level
    assert rules.rent(state, 6, 7) == state.board[6].rents[level]


def test_mortgaged_space_pays_no_rent_but_group_still_doubles(state):
    give(state, 0, *REEF)
    state.mortgaged[6] = True
    assert rules.rent(state, 6, 7) == 0
    assert rules.rent(state, 8, 7) == 2 * state.board[8].rents[0]


@pytest.mark.parametrize(("owned", "expected"), [(1, 30), (2, 80), (3, 180)])
def test_ferry_rent_scales_with_number_owned(state, owned, expected):
    give(state, 0, *state.board.ferries[:owned])
    assert rules.rent(state, 5, 7) == expected


@pytest.mark.parametrize(("owned", "multiplier"), [(1, 5), (2, 12)])
def test_utility_rent_multiplies_dice(state, owned, multiplier):
    give(state, 0, *state.board.utilities[:owned])
    assert rules.rent(state, 12, 9) == 9 * multiplier


def test_cannot_build_without_full_group(state):
    give(state, 0, 6)
    assert not rules.can_build(state, 0, 6)


def test_cannot_build_on_group_with_mortgage(state):
    give(state, 0, *REEF)
    state.mortgaged[8] = True
    assert not rules.can_build(state, 0, 6)


def test_cannot_build_without_cash(state):
    give(state, 0, *REEF)
    state.players[0].cash = state.board[6].build_cost - 1
    assert not rules.can_build(state, 0, 6)


def test_even_building_rule(state):
    give(state, 0, *REEF)
    bank.build(state, 0, 6)
    assert not rules.can_build(state, 0, 6)
    assert rules.can_build(state, 0, 8)
    with pytest.raises(IllegalMoveError):
        bank.build(state, 0, 6)


def test_build_charges_cost_and_uses_depot(state):
    give(state, 0, *REEF)
    cash = state.players[0].cash
    bank.build(state, 0, 6)
    assert state.players[0].cash == cash - state.board[6].build_cost
    assert state.depots_left == state.config.total_depots - 1
    assert state.burned == state.board[6].build_cost


def test_upgrade_to_port_returns_four_depots(state):
    give(state, 0, *REEF)
    state.players[0].cash = 10_000
    for _ in range(4):
        bank.build(state, 0, 6)
        bank.build(state, 0, 8)
    assert state.depots_left == state.config.total_depots - 8
    bank.build(state, 0, 6)
    assert state.level[6] == 5
    assert state.ports_left == state.config.total_ports - 1
    assert state.depots_left == state.config.total_depots - 4


def test_cannot_build_past_port(state):
    give(state, 0, *REEF)
    state.level[6] = state.level[8] = 5
    assert not rules.can_build(state, 0, 6)


def test_depot_shortage_blocks_building(state):
    give(state, 0, *REEF)
    state.depots_left = 0
    assert not rules.can_build(state, 0, 6)


def test_port_shortage_blocks_upgrade(state):
    give(state, 0, *REEF)
    state.level[6] = state.level[8] = 4
    state.ports_left = 0
    assert not rules.can_build(state, 0, 6)


def test_sell_building_refunds_half_and_must_stay_even(state):
    give(state, 0, *REEF)
    state.level[6], state.level[8] = 2, 1
    state.depots_left -= 3
    assert not rules.can_sell_building(state, 0, 8)
    cash = state.players[0].cash
    bank.sell_building(state, 0, 6)
    assert state.players[0].cash == cash + state.board[6].build_cost // 2
    assert state.level[6] == 1


def test_selling_port_needs_four_depots(state):
    give(state, 0, *REEF)
    state.level[6] = state.level[8] = 5
    state.depots_left = 3
    assert not rules.can_sell_building(state, 0, 6)
    state.depots_left = 4
    bank.sell_building(state, 0, 6)
    assert state.level[6] == 4 and state.depots_left == 0


def test_sell_group_works_during_shortage(state):
    give(state, 0, *REEF)
    state.level[6] = state.level[8] = 5
    state.ports_left -= 2
    state.depots_left = 0
    cash = state.players[0].cash
    bank.sell_group(state, 0, "reef")
    assert state.level[6] == state.level[8] == 0
    assert state.ports_left == state.config.total_ports
    assert state.depots_left == 0
    assert state.players[0].cash == cash + 10 * state.board[6].build_cost // 2


def test_mortgage_pays_value_and_needs_no_buildings_in_group(state):
    give(state, 0, *REEF)
    state.level[8] = 1
    assert not rules.can_mortgage(state, 0, 6)
    state.level[8] = 0
    cash = state.players[0].cash
    bank.mortgage(state, 0, 6)
    assert state.mortgaged[6]
    assert state.players[0].cash == cash + state.board[6].mortgage


def test_cannot_mortgage_twice_or_unowned(state):
    give(state, 0, 6)
    bank.mortgage(state, 0, 6)
    with pytest.raises(IllegalMoveError):
        bank.mortgage(state, 0, 6)
    with pytest.raises(IllegalMoveError):
        bank.mortgage(state, 0, 8)


@pytest.mark.parametrize(("index", "cost"), [(1, 25 + 3), (12, 70 + 7), (5, 90 + 9)])
def test_unmortgage_costs_ten_percent_interest_rounded_up(state, index, cost):
    give(state, 0, index)
    bank.mortgage(state, 0, index)
    cash = state.players[0].cash
    bank.unmortgage(state, 0, index)
    assert not state.mortgaged[index]
    assert state.players[0].cash == cash - cost


def test_cannot_unmortgage_without_cash(state):
    give(state, 0, 6)
    state.mortgaged[6] = True
    state.players[0].cash = rules.unmortgage_cost(state, 6) - 1
    assert not rules.can_unmortgage(state, 0, 6)


def test_liquidation_value_counts_buildings_and_unmortgaged_spaces(state):
    give(state, 0, *REEF, 5)
    state.level[6], state.level[8] = 2, 1
    state.mortgaged[5] = False
    expected = 3 * state.board[6].build_cost // 2 + 45 + 50 + 90
    assert rules.liquidation_value(state, 0) == expected
    state.mortgaged[5] = True
    assert rules.liquidation_value(state, 0) == expected - 90


def test_net_worth(state):
    give(state, 0, 6, 5)
    state.mortgaged[5] = True
    assert rules.net_worth(state, 0) == state.config.starting_cash + 90 + 90


def test_burn_cannot_overdraw(state):
    with pytest.raises(IllegalMoveError):
        bank.burn(state, state.players[0], state.players[0].cash + 1)


def test_transfer_cannot_overdraw():
    state = make_state()
    payer, payee = state.players
    with pytest.raises(IllegalMoveError):
        bank.transfer(payer, payee, payer.cash + 1)
