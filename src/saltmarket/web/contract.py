"""The data the website exchanges with the engine. These dataclasses are the source of truth.

``scripts/export_contract.py`` turns them into ``web/src/contract/types.ts``. Fields are
snake_case here and camelCase in JSON and TypeScript. A field that does not apply is
``None`` in Python and ``null`` in JSON, so every key is always present.
"""

from dataclasses import dataclass, fields, is_dataclass
from typing import Literal

ActionId = int
DecisionKindName = Literal[
    "buy", "auction", "build", "liquidate", "unmortgage", "brig", "propose", "accept",
    "raise_cash",
]
AgentName = Literal["ppo", "dqn"]
SubmitFailure = Literal["illegal", "not_your_turn", "game_over"]
BrigExit = Literal["roll", "pay", "pass"]
DeckName = Literal["tide", "ledger"]
LITERAL_ALIASES: dict[str, object] = {
    "DecisionKind": DecisionKindName,
    "AgentName": AgentName,
    "SubmitFailure": SubmitFailure,
    "BrigExit": BrigExit,
    "DeckName": DeckName,
}
"""Named string unions, so the TypeScript file can name them instead of repeating them."""


@dataclass(frozen=True, slots=True)
class SessionConfig:
    """How a game is set up. Seats are ``human``, ``ppo``, ``dqn``, or a bot name."""

    seed: int
    seats: tuple[str, ...]
    agent_delay_ms: int = 700


@dataclass(frozen=True, slots=True)
class TradeOfferView:
    """A trade offer. "give" is what the proposer hands over, "take" what they receive."""

    proposer: int
    responder: int
    give_spaces: tuple[int, ...]
    take_spaces: tuple[int, ...]
    give_cash: int
    take_cash: int
    give_passes: int
    take_passes: int


@dataclass(frozen=True, slots=True)
class LegalAction:
    """One choice a seat may make. ``id`` indexes the agent's fixed action list (0 to 107)."""

    id: ActionId
    label: str
    amount: int | None = None
    group: str | None = None
    space: int | None = None
    offer: TradeOfferView | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    """A choice waiting for the human. ``legal`` holds only moves the rules allow."""

    kind: DecisionKindName
    seat: int
    turn: int
    legal: tuple[LegalAction, ...]
    space: int | None = None
    price: int | None = None
    debt: int | None = None
    offer: TradeOfferView | None = None


@dataclass(frozen=True, slots=True)
class SubmitResult:
    """Outcome of submitting an action."""

    ok: bool
    reason: SubmitFailure | None = None


@dataclass(frozen=True, slots=True)
class ExplainedAction:
    """A legal action with the agent's score for it: ``prob`` for PPO, ``q`` for DQN."""

    id: ActionId
    label: str
    prob: float | None = None
    q: float | None = None


@dataclass(frozen=True, slots=True)
class Explanation:
    """Why an agent moved: its three best legal actions and the critic's value estimate."""

    agent: AgentName
    model: str
    top: tuple[ExplainedAction, ...]
    value: float | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EventBase:
    """Fields every event carries. ``seq`` counts up from 0 across the whole game."""

    turn: int
    seq: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Roll(EventBase):
    """Dice thrown, including the roll made to leave the Brig."""

    t: Literal["roll"] = "roll"
    seat: int
    dice: tuple[int, int]


@dataclass(frozen=True, slots=True, kw_only=True)
class Move(EventBase):
    """A piece moves. ``path`` lists every space passed, ending on the one landed on."""

    t: Literal["move"] = "move"
    seat: int
    path: tuple[int, ...]
    passed_home: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class Buy(EventBase):
    """A space is bought at list price."""

    t: Literal["buy"] = "buy"
    seat: int
    space: int
    price: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AuctionStart(EventBase):
    """A space goes to auction."""

    t: Literal["auction_start"] = "auction_start"
    space: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AuctionBid(EventBase):
    """A seat's limit bid. Each seat bids once, so this is not an ascending ladder."""

    t: Literal["auction_bid"] = "auction_bid"
    seat: int
    amount: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AuctionWin(EventBase):
    """The auction ends. ``seat`` is None when nobody bid."""

    t: Literal["auction_win"] = "auction_win"
    seat: int | None
    space: int
    amount: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Rent(EventBase):
    """Rent paid to a space's owner."""

    t: Literal["rent"] = "rent"
    payer: int
    payee: int
    space: int
    amount: int


@dataclass(frozen=True, slots=True, kw_only=True)
class LevelChange(EventBase):
    """A building level is added or removed. ``level`` is the new level of the space."""

    t: Literal["build", "sell"]
    seat: int
    space: int
    level: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MortgageChange(EventBase):
    """A mortgage is taken or lifted. ``amount`` is the sum of money that changed hands."""

    t: Literal["mortgage", "unmortgage"]
    seat: int
    space: int
    amount: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeOffered(EventBase):
    """One seat offers another a trade."""

    t: Literal["trade_offer"] = "trade_offer"
    offer: TradeOfferView


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeResult(EventBase):
    """The answer to the latest trade offer."""

    t: Literal["trade_result"] = "trade_result"
    accepted: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class BrigMove(EventBase):
    """A seat enters or leaves the Brig. ``how`` says how it left."""

    t: Literal["brig_in", "brig_out"]
    seat: int
    how: BrigExit | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CardDrawn(EventBase):
    """A Tide or Ledger card is drawn."""

    t: Literal["card"] = "card"
    seat: int
    deck: DeckName
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionMade(EventBase):
    """A seat chose an action. Agents attach an explanation."""

    t: Literal["decision"] = "decision"
    seat: int
    kind: DecisionKindName
    action: ActionId
    explanation: Explanation | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Bankrupt(EventBase):
    """A seat is out. ``creditor`` is None when the debt was owed to the bank."""

    t: Literal["bankrupt"] = "bankrupt"
    seat: int
    creditor: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CashChange(EventBase):
    """A seat's cash changed. Replaying these gives exact balances."""

    t: Literal["cash"] = "cash"
    seat: int
    balance: int
    delta: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerChange(EventBase):
    """A space changed owner. ``seat`` is None when it returned to the bank."""

    t: Literal["owner"] = "owner"
    space: int
    seat: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class GameOver(EventBase):
    """The game ended, by bankruptcy or by the turn cap."""

    t: Literal["game_over"] = "game_over"
    winner: int
    turns: int
    by_turn_cap: bool


GameEvent = (
    Roll | Move | Buy | AuctionStart | AuctionBid | AuctionWin | Rent | LevelChange
    | MortgageChange | TradeOffered | TradeResult | BrigMove | CardDrawn | DecisionMade
    | Bankrupt | CashChange | OwnerChange | GameOver
)


@dataclass(frozen=True, slots=True)
class ResultView:
    """The engine's result for a finished game."""

    winner: int
    turns: int
    hit_cap: bool
    net_worths: tuple[int, ...]
    bankrupt: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class FinalState:
    """The board at the end of a game, used to check that events replay to the same state."""

    cash: tuple[int, ...]
    owner: tuple[int | None, ...]
    level: tuple[int, ...]
    mortgaged: tuple[bool, ...]
    position: tuple[int, ...]
    bankrupt: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class GameFixture:
    """A recorded game: how it was set up, what the human chose, and everything that happened."""

    name: str
    config: SessionConfig
    answers: tuple[ActionId, ...]
    events: tuple[GameEvent, ...]
    result: ResultView
    final_state: FinalState
    fingerprint: str


EVENT_TYPES: tuple[type[EventBase], ...] = (
    Roll, Move, Buy, AuctionStart, AuctionBid, AuctionWin, Rent, LevelChange, MortgageChange,
    TradeOffered, TradeResult, BrigMove, CardDrawn, DecisionMade, Bankrupt, CashChange,
    OwnerChange, GameOver,
)
"""Every event class, in the order the TypeScript union lists them."""

VALUE_TYPES: tuple[type, ...] = (
    SessionConfig, TradeOfferView, LegalAction, Decision, SubmitResult, ExplainedAction,
    Explanation, ResultView, FinalState, GameFixture,
)
"""Every other exported class."""

def camel(name: str) -> str:
    """Turn a snake_case field name into camelCase."""
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


def to_json(value: object) -> object:
    """Convert contract objects into plain JSON values with camelCase keys."""
    if is_dataclass(value) and not isinstance(value, type):
        return {camel(f.name): to_json(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [to_json(item) for item in value]
    return value
