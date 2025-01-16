"""
Data structures for chains.
"""

from enum import Enum


class Chain(Enum):
    MAINNET = "MAINNET"
    GNOSIS = "GNOSIS"
    BASE = "BASE"
    OPTIMISM = "OPTIMISM"
    ARBITRUM = "ARBITRUM"
    MODE = "MODE"


class SwapType(Enum):
    EXACT_IN = "EXACT_IN"
