"""§17 token design scoring.

Extends the lab's measurement framework with token-specific
dimensions: dilution resistance, death-spiral resistance, oracle
manipulability, and game-theoretic stability. Each dimension is
scored 0.0-10.0 deterministically from the TokenDesign's driver
properties — no LLM, no randomness.

These are RESEARCH scores (§28). They measure structural properties
of the supply function, not live market behavior.

r39: initial implementation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from blockchain_rd_lab.tokenomics.combinator import TokenDesign
from blockchain_rd_lab.tokenomics.supply_drivers import SupplyDriver


@dataclass(frozen=True)
class TokenScore:
    """Deterministic score for one token design across four dimensions."""

    design_id: str
    dilution_resistance: float      # 0-10
    death_spiral_resistance: float  # 0-10
    oracle_manipulability: float    # 0-10 (higher = MORE manipulable = WORSE)
    game_theory_stability: float    # 0-10
    overall: float                  # weighted composite

    @property
    def overall_display(self) -> float:
        """Rounded for display consistency."""
        return round(self.overall, 4)


# Weights per §19 extension for token economics
_WEIGHTS = {
    "dilution_resistance": 0.30,
    "death_spiral_resistance": 0.25,
    "oracle_manipulability": 0.25,   # badness, subtracted in composite
    "game_theory_stability": 0.20,
}


def _count_manipulation_vectors(driver: SupplyDriver) -> int:
    return len(driver.manipulation_vectors)


def _supply_fn_is_bounded(driver: SupplyDriver) -> bool:
    """Test whether the supply function clamps output to [-1, 1].
    A bounded function cannot produce runaway mint/burn, which is
    the structural defense against both dilution and death spirals."""
    test_states = [
        {},  # empty state
        {k: 1e6 for k in ["trading_volume", "active_users",
                          "corridor_population", "network_nodes",
                          "ai_throughput_ops"]},
        {k: -1e6 for k in ["trading_volume", "active_users",
                           "gdp_growth_rate", "productivity_index"]},
        {k: 0.0 for k in ["trading_volume", "active_users",
                          "renewable_energy_mwh", "commodity_basket_price"]},
    ]
    for state in test_states:
        try:
            val = driver.supply_fn(state)
            if math.isnan(val) or abs(val) > 1.0 + 1e-9:
                return False
        except Exception:
            return False
    return True


def _supply_fn_has_burn_path(driver: SupplyDriver) -> bool:
    """Can this driver produce negative (burn) pressure?"""
    for state in driver.burn_probe_states:
        try:
            val = driver.supply_fn(state)
            if val < -1e-9:
                return True
        except Exception:
            continue
    return False


def _supply_fn_has_mint_path(driver: SupplyDriver) -> bool:
    """Can this driver produce positive (mint) pressure?"""
    for state in driver.mint_probe_states:
        try:
            val = driver.supply_fn(state)
            if val > 1e-9:
                return True
        except Exception:
            continue
    return False


def score_design(design: TokenDesign) -> TokenScore:
    """Compute deterministic token economics scores for a design.

    Scoring logic:
    - Dilution resistance: bounded supply fn (+5) + has burn path (+5).
      An unbounded mint-only driver scores 0.
    - Death spiral resistance: bounded supply fn (+5) + has mint path (+5).
      A burn-only driver with no mint scores 0.
    - Oracle manipulability: based on vector count and offline_scoreable.
      More vectors = higher score = worse. Inverted in composite.
    - Game theory stability: bidirectional (has both mint AND burn) +5,
      bounded +3, offline_scoreable +2.
    """
    d = design.driver
    bounded = _supply_fn_is_bounded(d)
    has_burn = _supply_fn_has_burn_path(d)
    has_mint = _supply_fn_has_mint_path(d)
    n_vectors = _count_manipulation_vectors(d)

    # Dilution resistance: can the system resist value erosion from over-minting?
    dilution = 0.0
    if bounded:
        dilution += 5.0
    if has_burn:
        dilution += 5.0

    # Death spiral resistance: can the system inject supply when demand drops?
    death_spiral = 0.0
    if bounded:
        death_spiral += 5.0
    if has_mint:
        death_spiral += 5.0

    # Oracle manipulability is a badness score: more vectors = higher
    # risk. Live-oracle drivers carry at least moderate inherent risk.
    oracle_manip = min(10.0, n_vectors * 2.5)
    if not d.offline_scoreable:
        oracle_manip = max(oracle_manip, 5.0)

    # Game theory stability: does the supply function create Nash-stable incentives?
    gt_stability = 0.0
    if has_mint and has_burn:
        gt_stability += 5.0  # bidirectional = agents can't corner one direction
    if bounded:
        gt_stability += 3.0  # bounded = no infinite exploitation
    if d.offline_scoreable:
        gt_stability += 2.0  # offline = no oracle dependency game

    # Composite: oracle_manipulability is badness, so subtract it.
    overall = (
        dilution * _WEIGHTS["dilution_resistance"]
        + death_spiral * _WEIGHTS["death_spiral_resistance"]
        - oracle_manip * _WEIGHTS["oracle_manipulability"]
        + gt_stability * _WEIGHTS["game_theory_stability"]
    )

    return TokenScore(
        design_id=design.design_id,
        dilution_resistance=dilution,
        death_spiral_resistance=death_spiral,
        oracle_manipulability=oracle_manip,
        game_theory_stability=gt_stability,
        overall=overall,
    )


def rank_designs(designs: list[TokenDesign]) -> list[tuple[TokenDesign, TokenScore]]:
    """Score and rank designs by overall composite descending, then
    design_id ascending for deterministic tiebreaking."""
    scored = [(d, score_design(d)) for d in designs]
    scored.sort(key=lambda x: (-x[1].overall, x[0].design_id))
    return scored
