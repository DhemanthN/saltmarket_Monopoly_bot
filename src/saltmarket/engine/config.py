"""Tunable game settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Rule parameters for one game. Defaults are the standard Saltmarket rulebook."""

    starting_cash: int = 1400
    salary: int = 180
    brig_fine: int = 60
    max_brig_turns: int = 3
    max_doubles: int = 3
    total_depots: int = 30
    total_ports: int = 10
    depots_per_port: int = 4
    group_rent_multiplier: int = 2
    mortgage_interest: float = 0.10
    building_sale_fraction: float = 0.5
    auction_min_bid: int = 10
    auction_increment: int = 5
    max_trade_proposals: int = 2
    turn_cap: int = 2000
    calm_waters_jackpot: bool = False
