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


class SwapType(Enum):
    EXACT_IN = "EXACT_IN"
