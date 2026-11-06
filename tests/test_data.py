from collections import Counter

import numpy as np
import pytest

from saltmarket.engine.board import SpaceKind, default_board
from saltmarket.engine.cards import CardEffect, Deck, default_cards

pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def board():
    return default_board()


@pytest.fixture(scope="module")
def cards():
    return default_cards()


def test_board_has_40_spaces_with_expected_kinds(board):
    assert board.size == 40
    counts = Counter(s.kind for s in board.spaces)
    assert counts == {
        SpaceKind.PROPERTY: 23,
        SpaceKind.FERRY: 3,
        SpaceKind.UTILITY: 2,
        SpaceKind.CARD: 6,
        SpaceKind.TAX: 2,
        SpaceKind.START: 1,
        SpaceKind.BRIG: 1,
        SpaceKind.REST: 1,
        SpaceKind.GO_TO_BRIG: 1,
    }


def test_group_sizes(board):
    assert {g: len(v) for g, v in board.groups.items()} == {
        "kelp": 3, "reef": 2, "coral": 3, "driftwood": 3,
        "amber": 3, "cinder": 4, "jade": 3, "crown": 2,
    }


def test_property_data_is_well_formed(board):
    for space in board.spaces:
        if space.kind != SpaceKind.PROPERTY:
            continue
        assert len(space.rents) == 6
        assert list(space.rents) == sorted(set(space.rents)), space.name
        assert space.mortgage == space.price // 2
        assert space.build_cost > 0 and space.build_cost % 2 == 0


def test_prices_rise_around_the_board(board):
    group_floor = [min(board[i].price for i in lots) for lots in board.groups.values()]
    assert group_floor == sorted(group_floor)


def test_ferry_and_utility_tables(board):
    assert all(len(board[i].rents) == 3 for i in board.ferries)
    assert all(len(board[i].rents) == 2 for i in board.utilities)


@pytest.mark.parametrize(
    ("position", "expected"), [(3, 5), (5, 19), (16, 19), (25, 30), (38, 5)]
)
def test_nearest_ferry_moves_forward_and_wraps(board, position, expected):
    assert board.nearest(position, board.ferries) == expected


def test_each_deck_has_16_unique_cards(cards):
    assert set(cards) == {"tide", "ledger"}
    for deck in cards.values():
        assert len(deck) == 16
        assert len({c.id for c in deck}) == 16


def test_card_targets_are_on_the_board(cards, board):
    for deck in cards.values():
        for card in deck:
            if card.effect == CardEffect.MOVE_TO:
                assert 0 <= card.target < board.size


def test_every_card_space_names_a_real_deck(board, cards):
    decks = {s.deck for s in board.spaces if s.kind == SpaceKind.CARD}
    assert decks == set(cards)


def test_deck_cycles_cards_in_order(cards):
    deck = Deck(cards["ledger"], np.random.default_rng(1))
    held = []
    first_pass = []
    for _ in range(16):
        card = deck.draw()
        first_pass.append(card.id)
        if card.effect == CardEffect.BRIG_PASS:
            held.append(card)
    assert len(set(first_pass)) == 16
    assert len(held) == 1 and len(deck) == 15
    second_pass = [deck.draw().id for _ in range(15)]
    assert second_pass == [c for c in first_pass if c != held[0].id]


def test_held_pass_returns_to_deck(cards):
    deck = Deck(cards["tide"], np.random.default_rng(2))
    held = next(c for c in iter(deck.draw, None) if c.effect == CardEffect.BRIG_PASS)
    assert len(deck) == 15
    deck.put_back(held)
    assert len(deck) == 16


def test_same_seed_shuffles_identically(cards):
    first = Deck(cards["tide"], np.random.default_rng(7))
    second = Deck(cards["tide"], np.random.default_rng(7))
    assert [first.draw().id for _ in range(10)] == [second.draw().id for _ in range(10)]
