"""§17 token design scoring.

Extends the lab's measurement framework with token-specific
dimensions: dilution resistance, death-spiral resistance, oracle
manipulability, and game-theoretic stability. Each dimension is
scored 0.0-10.0 deterministically from the TokenDesign's driver
properties — no LLM, no randomness.

These are RESEARCH scores (§28). They measure structural properties
of the supply function, not live market behavior.

r39: initial implementation.
r42: the dynamics-informed path — the SAME four dimensions and
    weights, but the dimension inputs CONSUME the r41 battery's
    measured edges (mint-extraction surface, drain depth, ratchet
    ratio) instead of structural proxies. Structural scoring is
    unchanged and published side-by-side (never a silent re-score).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from blockchain_rd_lab.tokenomics.battery import SupplyAttackBattery
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


@dataclass(frozen=True)
class DynamicsEvidence:
    """The r41 battery measurements that fed a dynamics-informed score.

    Every field is a MEASURED quantity (rate-unit fractions) or None
    where the attack surface is honestly absent (vacuous pattern).
    Published with the score so no number is unattributable.
    """

    driver: str
    steps: int
    # max(wash_mint, creep) / steps — the measured mint-extraction
    # surface. None: no forgeable mint surface (both patterns vacuous).
    mint_extraction: float | None
    # burn_park / steps — the measured drain depth under sustained
    # forged crisis. None: no forgeable burn surface.
    drain_fraction: float | None
    # resonance / (cycles x round_trip) — 1.0 exactly = measured
    # NO-RATCHET (linear in cycles). None: no manipulable surface or
    # unmeasurable (resonance extracts where single excursions
    # cannot — the compounding case, scored 0 stability).
    ratchet_ratio: float | None
    # pattern names that were honestly vacuous for this driver
    vacuous_patterns: tuple[str, ...]
    # r47: "<pattern>:<metric>" entries whose measured edge DIVERGED
    # (non-finite — the supply function ran away under the pattern).
    # Divergence maps the corresponding dimension to the FLOOR and is
    # disclosed here so a floor score is attributable to evidence,
    # never to a silent coercion.
    diverged_surfaces: tuple[str, ...] = ()


# Weights per §19 extension for token economics
_WEIGHTS = {
    "dilution_resistance": 0.30,
    "death_spiral_resistance": 0.25,
    "oracle_manipulability": 0.25,   # badness, subtracted in composite
    "game_theory_stability": 0.20,
}

# The r41 battery's default resonance cycle count — the ratchet ratio
# divides by cycles x single-excursion, so it must match the spec the
# evidence was measured under.
_RESONANCE_CYCLES = 4


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


def _oracle_badness(driver: SupplyDriver) -> float:
    """Oracle manipulability (BADNESS, 0 = best): min(10, 2.5 per
    known vector); live-oracle drivers floor at 5.0.

    r42 note: this dimension stays STRUCTURAL in both scoring paths —
    it counts SELF-REPORTED manipulation vectors, and the r41 battery
    has no oracle-analogue choreography (disclosed in the report).
    """
    n_vectors = _count_manipulation_vectors(driver)
    badness = min(10.0, n_vectors * 2.5)
    if not driver.offline_scoreable:
        badness = max(badness, 5.0)
    return badness


def _composite(
    dilution: float,
    death_spiral: float,
    oracle_manip: float,
    gt_stability: float,
) -> float:
    """The weighted composite — ONE formula, both scoring paths (the
    drift-proof convention: structural and dynamics can never
    disagree on how the composite combines dimensions)."""
    return (
        dilution * _WEIGHTS["dilution_resistance"]
        + death_spiral * _WEIGHTS["death_spiral_resistance"]
        - oracle_manip * _WEIGHTS["oracle_manipulability"]
        + gt_stability * _WEIGHTS["game_theory_stability"]
    )


def score_design(design: TokenDesign) -> TokenScore:
    """Compute deterministic token economics scores for a design.

    Scoring logic:
    - Dilution resistance: bounded supply fn (+5) + has burn path (+5).
      An unbounded mint-only driver scores 0.
    - Death spiral resistance: bounded supply fn (+5) + has mint path (+5).
      A burn-only driver with no mint scores 0.
    - Oracle manipulability (BADNESS, 0 = best): min(10, 2.5 per known
      vector); live-oracle drivers floor at 5.0. SUBTRACTED in the
      composite (weights sum to 1.0; composite bounds [0, 10]).
    - Game theory stability: bidirectional (has both mint AND burn) +5,
      bounded +3, offline_scoreable +2.

    r40: probe states are the driver's OWN declared probes — the
    climate driver's mint probe previously asserted a physically
    impossible input (negative risk index), buying a bidirectional
    credit no real state can exercise.
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
    overall = _composite(dilution, death_spiral, oracle_manip, gt_stability)

    return TokenScore(
        design_id=design.design_id,
        dilution_resistance=dilution,
        death_spiral_resistance=death_spiral,
        oracle_manipulability=oracle_manip,
        game_theory_stability=gt_stability,
        overall=overall,
    )


def score_design_with_dynamics(
    design: TokenDesign, steps: int = 60
) -> tuple[TokenScore, DynamicsEvidence]:
    """Dynamics-informed scoring: the SAME dimensions and weights as
    score_design, but the dimension inputs CONSUME the r41 battery's
    measured edges instead of structural proxies.

    Dimension mapping (measured evidence -> score):
    - Dilution resistance <- the mint-extraction surface:
      max(wash_mint, creep)/steps. A driver that can be forged to
      full clamp every step measures 0.0; the asymmetric-clamp driver
      (corridor-population, hi=0.5) measures 5.0. Both scored 10.0
      under the structural probes — the measurement discriminates
      what the structure could not. Vacuous (no mint surface) = 10.0:
      nothing can be forged where no mint path exists.
    - Death-spiral resistance <- the measured drain depth:
      burn_park/steps. Vacuous (no burn surface) = 10.0.
    - Oracle manipulability: UNCHANGED STRUCTURAL (self-reported
      vectors; the battery has no oracle analogue — disclosed).
    - Game-theory stability <- the measured ratchet ratio:
      resonance/(cycles x round_trip). Exactly 1.0 = linear, the
      measured NO-RATCHET result (10.0). Above 1.0 = compounding
      (10 x (2 - ratio), floored at 0). Resonance extracting where
      single excursions cannot (round_trip ~ 0 < resonance) is the
      compounding class: 0.0. Vacuous = 10.0 (no manipulable
      surface at all).

    Deterministic; returns the score and the evidence that fed it
    (every number attributable, §2).
    """
    battery = SupplyAttackBattery(design.driver)
    bounds = {
        b.kind.value: b for b in battery.run_all(steps)
    }
    wash = bounds["wash_mint"]
    creep = bounds["creep"]
    round_trip = bounds["round_trip"]
    resonance = bounds["resonance"]
    burn_park = bounds["burn_park"]
    vacuous = tuple(
        sorted(name for name, b in bounds.items() if b.vacuous)
    )

    # Dilution: the measured mint-extraction surface.
    # r47: a diverged mint surface (non-finite edge) is the worst
    # possible measurement — score the FLOOR, never "no extraction".
    mint_diverged = any(
        m in b.diverged_metrics
        for b in (wash, creep)
        for m in b.bound_metrics
    )
    measured_mint = [
        b.headline
        for b in (wash, creep)
        if not b.vacuous and b.headline is not None
        and math.isfinite(b.headline)
    ]
    if mint_diverged:
        mint_extraction = math.inf
        dilution = 0.0
    elif not measured_mint:
        mint_extraction = None
        dilution = 10.0
    else:
        mint_extraction = max(measured_mint) / steps
        dilution = 10.0 * (1.0 - mint_extraction)

    # Death spiral: the measured drain depth.
    # r47: a diverged drain (runaway burn) is the death-spiral signature
    # this dimension exists to catch — score the FLOOR, never 10.0.
    burn_diverged = any(m in burn_park.diverged_metrics for m in burn_park.bound_metrics)
    if burn_park.vacuous or burn_park.headline is None:
        drain_fraction = None
        death_spiral = 10.0
    elif burn_diverged or not math.isfinite(burn_park.headline):
        drain_fraction = math.inf
        death_spiral = 0.0
    else:
        drain_fraction = burn_park.headline / steps
        death_spiral = 10.0 * (1.0 - drain_fraction)

    # Oracle manipulability: structural in both paths (see helper)
    oracle_manip = _oracle_badness(design.driver)

    # Game theory: the measured ratchet ratio.
    # r47: a diverged resonance/round_trip headline is the compounding
    # runaway class — score the floor, never the vacuous 10.0.
    gt_diverged = any(
        m in b.diverged_metrics
        for b in (resonance, round_trip)
        for m in b.bound_metrics
    )
    if (
        resonance.vacuous
        or round_trip.vacuous
        or resonance.headline is None
        or round_trip.headline is None
    ):
        ratchet_ratio = None
        gt_stability = 10.0
    elif gt_diverged or not math.isfinite(resonance.headline):
        ratchet_ratio = math.inf
        gt_stability = 0.0
    elif resonance.headline <= 1e-9:
        # nothing extracted across N cycles: nothing to ratchet
        ratchet_ratio = 1.0
        gt_stability = 10.0
    elif round_trip.headline <= 1e-9:
        # resonance extracts where a single excursion cannot: the
        # compounding class, measured — score the floor
        ratchet_ratio = None
        gt_stability = 0.0
    else:
        # round_trip is finite here: any divergence was floored above.
        ratchet_ratio = resonance.headline / (
            _RESONANCE_CYCLES * round_trip.headline
        )
        gt_stability = max(
            0.0, min(10.0, 10.0 * (2.0 - ratchet_ratio))
        )

    overall = _composite(dilution, death_spiral, oracle_manip, gt_stability)

    diverged_surfaces = tuple(
        sorted(
            f"{b.kind.value}:{m}"
            for b in bounds.values()
            for m in b.diverged_metrics
        )
    )
    evidence = DynamicsEvidence(
        driver=design.driver.name,
        steps=steps,
        mint_extraction=mint_extraction,
        drain_fraction=drain_fraction,
        ratchet_ratio=ratchet_ratio,
        vacuous_patterns=vacuous,
        diverged_surfaces=diverged_surfaces,
    )
    score = TokenScore(
        design_id=design.design_id,
        dilution_resistance=dilution,
        death_spiral_resistance=death_spiral,
        oracle_manipulability=oracle_manip,
        game_theory_stability=gt_stability,
        overall=overall,
    )
    return score, evidence


def rank_designs_with_dynamics(
    designs: list[TokenDesign], steps: int = 60
) -> list[tuple[TokenDesign, TokenScore, DynamicsEvidence]]:
    """Score and rank designs by the DYNAMICS-INFORMED composite
    descending, then design_id ascending (deterministic tiebreak).

    Published beside the structural ranking — never instead of it
    (the r42 contract: a flip is visible, never silent)."""
    scored = [score_design_with_dynamics(d, steps) for d in designs]
    ranked = [
        (d, s, e) for d, (s, e) in zip(designs, scored, strict=True)
    ]
    ranked.sort(key=lambda x: (-x[1].overall, x[0].design_id))
    return ranked


def rank_designs(designs: list[TokenDesign]) -> list[tuple[TokenDesign, TokenScore]]:
    """Score and rank designs by overall composite descending, then
    design_id ascending for deterministic tiebreaking."""
    scored = [(d, score_design(d)) for d in designs]
    scored.sort(key=lambda x: (-x[1].overall, x[0].design_id))
    return scored
