"""§17 supply-stock composition layer (r43).

What r41 measured and r42 consumed left one boundary open: the
registry's supply functions are STATELESS per-step rates, so no
ratchet or death spiral is representable at the driver level — the
compounding dynamics live where rates INTEGRATE into a supply stock.
This module is that layer.

The composition (all deterministic, §2):
- A demand process D_t (the token's usage level) grows at gamma_t =
  scenario growth + elasticity x (V_t/V_0 - 1): demand responds to
  value (the reflexive channel — dilution below anchor pushes
  holders out; appreciation pulls them in).
- The driver's OWN signal axis (resolved by battery.resolve_signal —
  the same source the r41 crafts ride) carries the demand: level-type
  drivers read (D_t, D_{t-1}) through their reference key; the signed
  rate-type driver (gdp) reads gamma_t directly.
- Rates integrate multiplicatively: S_{t+1} = S_t x (1 + rate_t).
- Value per token: V_t = D_t / S_t (V_0 = 1 by construction).
- The verdict reads the QUIET TAIL (the r20 discipline): the last
  quarter of the window, after the scenario's shock has ended. A
  value that is still MOVING under quiet is a spiral; one that has
  settled is a rebase; one that never moved is stable.

Honest composition scope (the r40-F1 lineage — never credit behavior
outside the declared domain): level-type drivers compose through
their probe-declared reference pairs; rate-type axes compose ONLY
when the driver declares BOTH mint and burn probes spanning zero
(the signed-rate case — gdp). One-sided bounded indices (climate
risk, claims ratio, prediction confidence) are honestly VACUOUS:
their crisis-mapping is a modeling assumption the registry does not
declare.

All measures are SIMULATION-STAGE evidence under deterministic
choreographies (§28 research-only).
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

from blockchain_rd_lab.tokenomics.battery import resolve_signal
from blockchain_rd_lab.tokenomics.supply_drivers import SupplyDriver


class StockVerdict(enum.StrEnum):
    """The quiet-tail classification of one composed stock run."""

    STABLE = "stable"                # value never left the band
    REBASED_DOWN = "rebased_down"    # value settled below anchor
    REBASED_UP = "rebased_up"        # value settled above anchor
    SPIRAL_DOWN = "spiral_down"      # still deteriorating under quiet
    SPIRAL_UP = "spiral_up"          # still expanding under quiet
    VACUOUS = "vacuous"              # not composable (disclosed reason)


# Verdict thresholds (deterministic constants; rate-unit fractions).
_STABLE_BAND = 0.05      # |V_end/V_0 - 1| within this = never left
_GROWING_MARGIN = 0.0005  # tail excess still rising by this = diverging
_SUSTAINED_TOLERANCE = 0.02  # endogenous growth beyond drive = spiral
_GROWTH_CLAMP = 0.5      # per-step total demand growth clamp


@dataclass(frozen=True)
class StockScenario:
    """Deterministic demand-path parameters of one stock run.

    The growth path: inside [shock_from, shock_to) the growth is
    shock_growth — or, when oscillation_amplitude > 0, an alternating
    +/- amplitude (t - shock_from parity). Outside the window it is
    baseline_growth. The verdict always reads the LAST QUARTER of the
    window, so scenarios place their shocks early.
    """

    name: str
    steps: int = 90
    shock_from: int = 0
    shock_to: int = 30
    shock_growth: float = -0.02
    baseline_growth: float = 0.0
    oscillation_amplitude: float = 0.0
    # one-shot fractional mint (positive) landing at the step boundary
    supply_shock_at: int | None = None
    supply_shock: float = 0.10
    # demand-value elasticity (the reflexive channel strength)
    elasticity: float = 0.5


SCENARIOS: dict[str, StockScenario] = {
    "steady": StockScenario(
        name="steady",
        steps=90,
        shock_from=0,
        shock_to=0,
    ),
    "organic_growth": StockScenario(
        name="organic_growth",
        steps=90,
        shock_from=0,
        shock_to=0,
        baseline_growth=0.01,
    ),
    "demand_collapse": StockScenario(
        name="demand_collapse",
        steps=90,
        shock_from=0,
        shock_to=30,
        shock_growth=-0.02,
    ),
    "crash": StockScenario(
        name="crash",
        steps=90,
        shock_from=0,
        shock_to=5,
        shock_growth=-0.20,
    ),
    "supply_shock": StockScenario(
        name="supply_shock",
        steps=90,
        shock_from=0,
        shock_to=0,
        supply_shock_at=15,
        supply_shock=0.10,
    ),
    "oscillation": StockScenario(
        name="oscillation",
        steps=90,
        shock_from=0,
        shock_to=60,
        oscillation_amplitude=0.05,
    ),
    "hyper_growth": StockScenario(
        name="hyper_growth",
        steps=90,
        shock_from=0,
        shock_to=0,
        baseline_growth=0.05,
    ),
}


@dataclass(frozen=True)
class StockRunResult:
    """The deterministic result of one composed stock run."""

    driver: str
    scenario: str
    verdict: StockVerdict
    composition: str  # "level" | "rate" | "none"
    supply_ratio: float   # S_T / S_0
    demand_ratio: float   # D_T / D_0
    value_ratio: float    # V_T / V_0 (V_0 = 1)
    min_value: float
    max_value: float
    tail_drift: float     # mean endogenous motion per tail step
    endogenous_growth: float  # mean (rate - g) over the tail, signed
    max_abs_rate: float
    note: str


def _growth(sc: StockScenario, t: int) -> float:
    if sc.shock_from <= t < sc.shock_to:
        if sc.oscillation_amplitude > 0.0:
            sign = 1.0 if (t - sc.shock_from) % 2 == 0 else -1.0
            return sc.oscillation_amplitude * sign
        return sc.shock_growth
    return sc.baseline_growth


def _reference_key(
    axis: str, neutral: dict[str, float]
) -> str | None:
    """The key that carries the demand's previous level.

    Convention first (prev_<axis>), then the single-other-key case
    (market/energy/commodity/ai name their references freely but
    carry exactly one beside the axis).
    """
    prev = f"prev_{axis}"
    if prev in neutral:
        return prev
    others = [k for k in neutral if k != axis]
    if len(others) == 1:
        return others[0]
    return None


def _axis_is_signed_rate(driver: SupplyDriver, axis: str) -> bool:
    """Rate-type axes compose only when BOTH probe directions are
    declared AND the axis values span zero (the signed-rate case).

    The r40-F1 lineage: a one-sided index (climate risk in [0,1],
    claims ratio, prediction confidence) driven negative is a state
    outside its declared physical domain — never credited here."""
    mint_axes = [
        p[axis] for p in driver.mint_probe_states if axis in p
    ]
    burn_axes = [
        p[axis] for p in driver.burn_probe_states if axis in p
    ]
    if not mint_axes or not burn_axes:
        return False
    values = mint_axes + burn_axes
    return min(values) < 0.0 < max(values)


def run_stock_scenario(
    driver: SupplyDriver, scenario: StockScenario
) -> StockRunResult:
    """Compose the driver into a supply stock and run one scenario.

    Deterministic: same (driver, scenario) -> same floats.
    """
    resolved = resolve_signal(driver)
    if resolved is None:
        return StockRunResult(
            driver=driver.name,
            scenario=scenario.name,
            verdict=StockVerdict.VACUOUS,
            composition="none",
            supply_ratio=1.0,
            demand_ratio=1.0,
            value_ratio=1.0,
            min_value=1.0,
            max_value=1.0,
            tail_drift=0.0,
            endogenous_growth=0.0,
            max_abs_rate=0.0,
            note="no resolvable signal axis (no probe declared)",
        )
    axis, neutral, _probe = resolved

    ref = _reference_key(axis, neutral)
    if ref is not None:
        composition = "level"
        d_level = float(neutral[axis])
        if d_level <= 0.0:
            return StockRunResult(
                driver=driver.name,
                scenario=scenario.name,
                verdict=StockVerdict.VACUOUS,
                composition="none",
                supply_ratio=1.0,
                demand_ratio=1.0,
                value_ratio=1.0,
                min_value=1.0,
                max_value=1.0,
                tail_drift=0.0,
                endogenous_growth=0.0,
                max_abs_rate=0.0,
                note="non-positive neutral demand level",
            )
    elif _axis_is_signed_rate(driver, axis):
        composition = "rate"
        d_level = 1000.0  # scale-free anchor for rate-type axes
    else:
        return StockRunResult(
            driver=driver.name,
            scenario=scenario.name,
            verdict=StockVerdict.VACUOUS,
            composition="none",
            supply_ratio=1.0,
            demand_ratio=1.0,
            value_ratio=1.0,
            min_value=1.0,
            max_value=1.0,
            tail_drift=0.0,
            endogenous_growth=0.0,
            max_abs_rate=0.0,
            note=(
                "one-sided or unspanned signal axis; crisis-mapping "
                "is a modeling assumption the registry does not "
                "declare (the r40-F1 domain discipline)"
            ),
        )

    s0 = d_level
    d_prev = d_level
    d_cur = d_level
    s_cur = s0
    values: list[float] = [1.0]
    # per-step endogenous motion beyond the scenario's own drive:
    # (|gamma - g|, |rate - g|, |dV/V|) — the spiral signature is
    # movement the FEEDBACK causes, not movement the scenario drives
    excesses: list[float] = []
    # the signed endogenous supply growth (rate - g): the bleed /
    # explosion criteria read it from the quiet tail, and it ships in
    # the result for attribution
    endogenous: list[float] = []
    max_abs_rate = 0.0

    for t in range(scenario.steps):
        # a one-shot mint lands at the step boundary, before value
        if (
            scenario.supply_shock_at is not None
            and t == scenario.supply_shock_at
        ):
            s_cur *= 1.0 + scenario.supply_shock

        v_prev = d_cur / s_cur if s_cur > 0.0 else math.inf
        values.append(v_prev)
        g = _growth(scenario, t)
        feedback = scenario.elasticity * (v_prev - 1.0)
        gamma = max(
            -_GROWTH_CLAMP, min(_GROWTH_CLAMP, g + feedback)
        )

        if composition == "level":
            state = dict(neutral)
            state[axis] = d_cur
            assert ref is not None  # narrowed by the composition branch
            state[ref] = d_prev
        else:
            state = {axis: gamma}
        rate = driver.supply_fn(state)
        if not math.isfinite(rate):
            rate = 0.0
        rate = max(-1.0, min(1.0, rate))
        max_abs_rate = max(max_abs_rate, abs(rate))

        d_prev = d_cur
        d_cur = d_cur * (1.0 + gamma)
        s_cur = s_cur * (1.0 + rate)
        # guard the representable range (long spirals)
        if not math.isfinite(d_cur) or d_cur < 1e-300:
            d_cur = 0.0
        if not math.isfinite(s_cur) or s_cur < 1e-300:
            s_cur = 0.0

        v_next = d_cur / s_cur if s_cur > 0.0 else math.inf
        v_move = (
            abs(v_next / v_prev - 1.0)
            if v_prev > 0.0 and v_next > 0.0
            else math.inf
        )
        excesses.append(
            max(abs(gamma - g), abs(rate - g), v_move)
        )
        endogenous.append(rate - g)

    supply_ratio = s_cur / s0 if s0 > 0 else 0.0
    demand_ratio = d_cur / d_level if d_level > 0 else 0.0
    value_end = values[-1]
    v_min = min(values)
    v_max = max(values)

    # quiet tail: the last quarter of the window (the r20 discipline —
    # the verdict classifies what the system does AFTER the shock).
    # Two pathological signatures, honestly separated:
    # (a) GROWING excess — motion still accelerating under quiet;
    # (b) SUSTAINED endogenous growth — the system moves beyond its
    #     drive at a constant rate (the melt: demand/supply bleed
    #     with value looking settled; the inflationary collapse:
    #     mint compounding while demand dies; the deflationary
    #     runaway: supply collapsing while demand grows).
    # Both are spirals, signed by where VALUE ended (out of band) or
    # by the endogenous direction (value-neutral melt). Everything
    # else is stable (value never left the band) or rebased (value
    # settled at a new level).
    tail_from = len(excesses) - max(1, scenario.steps // 4)
    tail_ex = excesses[tail_from:]
    tail_drift = math.fsum(tail_ex) / len(tail_ex)
    endogenous_growth = (
        math.fsum(endogenous[tail_from:])
        / len(endogenous[tail_from:])
    )
    half = max(1, len(tail_ex) // 2)
    e1 = math.fsum(tail_ex[:half]) / half
    e2 = math.fsum(tail_ex[-half:]) / min(half, len(tail_ex))
    growing = e2 > e1 + _GROWING_MARGIN

    # r46 (the self-audit's boundary finding): the sustained-motion
    # comparison is >=, not > — a value still compounding AT the
    # tolerance (2%/step) has not "settled", so rebased would
    # mislabel it; and the anti-tracking drivers at eta=0/organic
    # land exactly ON the tolerance in real arithmetic, where one
    # float ULP was deciding spiral-vs-rebased (ai read
    # -0.020000000000000007 -> spiral, gdp read exactly -0.02 ->
    # rebased, identical economics). At-boundary is sustained
    # motion; noise must not decide the boundary.
    if growing or abs(endogenous_growth) >= _SUSTAINED_TOLERANCE:
        # diverging (excess still rising) or sustained endogenous
        # motion beyond the drive — a spiral either way, signed by
        # where VALUE went (out of band), else by the endogenous
        # direction (the value-neutral melt).
        if value_end < 1.0 - _STABLE_BAND:
            verdict = StockVerdict.SPIRAL_DOWN
        elif value_end > 1.0 + _STABLE_BAND:
            verdict = StockVerdict.SPIRAL_UP
        elif endogenous_growth < 0.0:
            verdict = StockVerdict.SPIRAL_DOWN
        else:
            verdict = StockVerdict.SPIRAL_UP
    elif abs(value_end - 1.0) <= _STABLE_BAND:
        verdict = StockVerdict.STABLE
    elif value_end < 1.0:
        verdict = StockVerdict.REBASED_DOWN
    else:
        verdict = StockVerdict.REBASED_UP

    return StockRunResult(
        driver=driver.name,
        scenario=scenario.name,
        verdict=verdict,
        composition=composition,
        supply_ratio=supply_ratio,
        demand_ratio=demand_ratio,
        value_ratio=value_end,
        min_value=v_min,
        max_value=v_max,
        tail_drift=tail_drift,
        endogenous_growth=endogenous_growth,
        max_abs_rate=max_abs_rate,
        note=f"composition={composition}; axis={axis}",
    )


def run_stock_suite(
    driver: SupplyDriver,
) -> dict[str, StockRunResult]:
    """Every scenario against one driver, deterministic order."""
    return {
        name: run_stock_scenario(driver, sc)
        for name, sc in SCENARIOS.items()
    }
