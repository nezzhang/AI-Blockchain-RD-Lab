"""§17 supply-dynamics attack battery (r41).

The §20 pattern applied to token supply functions: named attacker
choreographies craft STATE series (per-step input dicts) against a
driver's supply function and measure what the attacker extracts or
ratchets, versus a matched honest base.

Why this exists (the r40 audit's disclosed boundary): §17 scores were
STRUCTURAL — they check that a burn path EXISTS (probe states) and
that the function is BOUNDED (clamps). They never measured what a
manipulated input SERIES does over time. This battery closes that
disclosure: supply dynamics are MEASURED, not asserted.

Design contracts:
- Deterministic: same (driver, spec) -> same floats. No randomness,
  no wall-clock, no LLM. (§2)
- Crafts are built from the driver's OWN declared probe states (the
  r40-F1 mechanism reused honestly): the wash craft holds the mint
  probe, the burn park holds the burn probe. A driver with no probe
  for a direction makes that pattern honestly VACUOUS — never 0.0
  (a false "bounded by zero" claim; the §20 convention).
- The matched base is the NEUTRAL state: the probe with its signal
  axis(es) moved to zero-pressure values, found by a deterministic
  iterated search with a GUARD-SMOOTHNESS rejection (a value whose
  zero output explodes under 1e-6 perturbation is a degenerate
  guard return, not a neutral — the r41 first-draft bug class: a
  zeroed baseline triggered the driver's own `<= 0` guard and
  manufactured fake bases).
- Edge = pattern metric minus matched-base metric, in RATE-UNITS
  (steps x clamped rate). NOT comparable to §20's FLAW_EDGE_THRESHOLD
  (400, $-denominated stock edges); any future supply-flaw threshold
  is a separate calibration decision, deliberately not imported.
- Headline = the worst edge over the pattern's bound metrics.

All measures are SIMULATION-STAGE evidence under deterministic
choreographies (§28 research-only; the same caveat every §20 bound
carries).
"""

from __future__ import annotations

import enum
import itertools
import math
from dataclasses import dataclass

from blockchain_rd_lab.tokenomics.supply_drivers import SupplyDriver

# Neutral-search tolerances (deterministic constants).
_PERTURB = 1e-6  # guard-smoothness perturbation
_SMOOTH_MAX = 1e-3  # |fn| allowed under perturbation at a true neutral
_ZERO_PRESSURE = 1e-9  # |fn| below this counts as zero pressure


def _is_reference_key(key: str) -> bool:
    """Reference (denominator) keys by the registry's naming
    conventions: prev_<signal>, <signal>_baseline, <signal>_target.
    The neutral search moves SIGNALS, never references (r44 F1)."""
    return (
        key.startswith("prev_")
        or key.endswith("_baseline")
        or key.endswith("_target")
    )


class SupplyAttackPattern(enum.StrEnum):
    """Named attacker choreographies against supply functions.

    Each is the supply-side analogue of a §20 pattern, shaped by the
    manipulation vectors the §17 registry itself declares (wash
    trading, sybil activity, virtual nodes, no-op AI calls...).
    """

    # Sustained false positive signal: the attacker holds the mint
    # probe's signal state every step (wash volume, sybil users,
    # virtual nodes, no-op throughput). Bound: total minted under
    # sustained manipulation vs the neutral base — the wash premium.
    # A driver whose mint saturates (clamps at 1.0 early) extracts
    # nothing further per extra step: bounded by construction, and
    # the battery says so numerically.
    WASH_MINT = "wash_mint"
    # The round trip: manipulate the mint signal up, then release to
    # neutral. Bound: the minted total over the manipulated legs (the
    # release legs pay nothing back if the driver is one-directional
    # on the mint axis) plus any final-rate residue.
    ROUND_TRIP = "round_trip"
    # Repeated strike-release cycles: N manipulate-hold-release
    # cycles. Bound: the minted total + final-rate residue — the
    # supply-side ratchet check (pressure that compounds instead of
    # reverting across cycles).
    RESONANCE = "resonance"
    # Sub-threshold creep: the signal grinds from neutral toward the
    # probe's declared magnitude, never reaching it within the window
    # (the §20 drift_creep analogue). Bound: cumulative minted over
    # the grind — leakage through sub-threshold accumulation.
    CREEP = "creep"
    # Sustained false NEGATIVE signal: hold the burn probe's state
    # (fake crisis, manufactured risk). Bound: the burn depth — how
    # deep the drain goes under sustained manipulation.
    BURN_PARK = "burn_park"


@dataclass(frozen=True)
class SupplySpec:
    """Deterministic parameters of one supply attack run."""

    kind: SupplyAttackPattern
    steps: int = 60
    # wash_mint / round_trip / resonance: multiple of the mint probe's
    # signal displacement (from neutral to probe) the attacker forges
    # (1.0 = exactly the declared canonical signal)
    forge_scale: float = 1.0
    # round_trip / resonance: steps held at the forged level before
    # the release leg (resonance's per-cycle cadence)
    hold: int = 5
    # resonance: number of strike cycles in the window
    cycles: int = 4
    # creep: per-step fraction of the (neutral -> probe) displacement
    # added each step; the interpolation factor is capped at 1.0 (the
    # craft never exceeds the probe's declared magnitude)
    creep_rate: float = 0.01


@dataclass(frozen=True)
class SupplyAttackBound:
    """The deterministic result of one supply attack run."""

    kind: SupplyAttackPattern
    driver: str
    pattern_metrics: dict[str, float]
    base_metrics: dict[str, float]
    edge: dict[str, float]
    # The metrics that define this pattern's bound; the worst of
    # these is the headline.
    bound_metrics: list[str]
    headline: float | None
    headline_metric: str | None
    vacuous: bool
    note: str
    # Metrics whose edge is NON-FINITE (the supply function ran away to
    # +/-inf under the pattern). r47: a non-finite edge is the WORST
    # possible measurement for that axis — a diverging burn/mint — and
    # must never be coerced to 0.0 ("no edge") nor parsed as vacuous.
    # Scoring maps any diverged bound-metric to the dimension FLOOR.
    diverged_metrics: tuple[str, ...] = ()


def _interp(neutral: float, probe: float, factor: float) -> float:
    """Interpolate one axis from neutral toward the probe value."""
    return neutral + (probe - neutral) * factor


class SupplyAttackBattery:
    """Runs named supply-side attack choreographies against one driver."""

    def __init__(self, driver: SupplyDriver) -> None:
        self.driver = driver

    # -- probe / neutral resolution ---------------------------------

    def _probe(self, kind: SupplyAttackPattern) -> dict[str, float] | None:
        probes = (
            self.driver.burn_probe_states
            if kind is SupplyAttackPattern.BURN_PARK
            else self.driver.mint_probe_states
        )
        return probes[0] if probes else None

    def _fn_abs(self, state: dict[str, float]) -> float:
        return abs(self.driver.supply_fn(state))

    def _guard_smooth(self, state: dict[str, float]) -> bool:
        """Reject degenerate-guard fake neutrals: perturb EACH axis
        ALONE and require |fn| to stay small. Perturbing all axes
        together masks symmetric degenerates (the r41 third-draft bug:
        (vol=0, baseline=0) passed because (1e-6, 1e-6) is still
        zero-rate — but (0, 1e-6) hits the driver's `baseline <= 0`
        guard's cliff at rate -1.0)."""
        for k, v in state.items():
            for direction in (1.0, -1.0):
                perturbed = dict(state)
                perturbed[k] = v + direction * _PERTURB * (1.0 + abs(v))
                if self._fn_abs(perturbed) > _SMOOTH_MAX:
                    return False
        return True

    def _neutral_state(self, probe: dict[str, float]) -> dict[str, float]:
        """The probe's zero-pressure state, chosen deterministically:

        1. Enumerate assignments over a fixed candidate set per axis
           ({0.0, 0.5, the probe's own value, every other key's probe
           value}) — exhaustive (registry probes carry at most 4 keys;
           >6 falls back to greedy descent).
        2. Keep only ZERO-PRESSURE (|fn| < 1e-9) assignments that are
           guard-smooth (not sitting on a `<= 0` cliff).
        3. Among those, pick the one CLOSEST to the probe (L1) — the
           interpolation path from neutral to probe then stays near
           the probe's own denominators, so the crafted displacement
           means what the probe declared (the fourth-draft bug: the
           equally-valid neutral (0.5, 0.5) inflated market-volume's
           interpolated rates 2x by shrinking the baseline en route).
        4. Ties break by enumeration order (deterministic).

        If no true neutral exists, the best-|fn| assignment is the
        honest fallback (disclosed by the base metrics).
        """
        keys = sorted(probe)
        if not keys:
            return dict(probe)
        if len(keys) > 6:
            return self._neutral_greedy(probe)

        cand_lists = [
            sorted(
                {0.0, 0.5, probe[k]}
                | {v for j, v in probe.items() if j != k}
            )
            for k in keys
        ]
        best_zero: tuple[float, int, int, dict[str, float]] | None = None
        best_any: tuple[float, float, int, dict[str, float]] | None = None
        for order, assignment in enumerate(
            itertools.product(*cand_lists)
        ):
            state = dict(zip(keys, assignment, strict=True))
            f = self._fn_abs(state)
            dist = sum(abs(state[k] - probe[k]) for k in keys)
            # r44 (the pre-audit sweep's F1): among equidistant
            # zero-pressure candidates, prefer the one that moves
            # the SIGNAL, not the REFERENCE. The r41 tie-break was
            # alphabetical luck: productivity-deflation's probe
            # (prod=0.5, prev=1.0) has two dist-0.5 neutrals —
            # (prod=1, prev=1) moves the signal, (prod=0.5,
            # prev=0.5) moves the reference — and "prev_" sorted
            # first, so the wrong one won, INVERTING the stock
            # layer's composition for that driver (it minted into
            # growth where the design burns). market-volume got
            # lucky ("trading_volume" sorts first); the luck is
            # now replaced by the rule.
            ref_moved = sum(
                1
                for k in keys
                if state[k] != probe[k] and _is_reference_key(k)
            )
            if best_any is None or (f, dist, order) < best_any[:3]:
                best_any = (f, dist, order, state)
            if (
                f < _ZERO_PRESSURE
                and self._guard_smooth(state)
                and (
                    best_zero is None
                    or (dist, ref_moved, order) < best_zero[:3]
                )
            ):
                best_zero = (dist, ref_moved, order, state)
        if best_zero is not None:
            return best_zero[3]
        assert best_any is not None  # product is never empty
        return best_any[3]

    def _neutral_greedy(
        self, probe: dict[str, float]
    ) -> dict[str, float]:
        """Fallback for oversized probes: iterate single-axis moves
        (best-first, deterministic order) until no improvement."""
        state = dict(probe)
        keys = sorted(probe)
        for _ in range(len(keys)):
            if self._fn_abs(state) < _ZERO_PRESSURE:
                break
            best: tuple[float, str, float] | None = None
            for k in keys:
                for c in sorted({0.0, 0.5} | set(state.values())):
                    if c == state[k]:
                        continue
                    trial = dict(state)
                    trial[k] = c
                    f = self._fn_abs(trial)
                    if f < _ZERO_PRESSURE and not self._guard_smooth(trial):
                        f = math.inf
                    cand = (f, k, c)
                    if best is None or cand < best:
                        best = cand
            if best is None or best[0] >= self._fn_abs(state):
                break
            state[best[1]] = best[2]
        return state

    # -- series construction ----------------------------------------

    def _forged(
        self, probe: dict[str, float], neutral: dict[str, float], factor: float
    ) -> dict[str, float]:
        """The probe state with every axis interpolated from neutral
        toward the probe by `factor` (1.0 = the declared probe)."""
        return {
            k: _interp(neutral[k], probe[k], factor) for k in probe
        }

    def _series(
        self,
        spec: SupplySpec,
        probe: dict[str, float],
        neutral: dict[str, float],
    ) -> list[dict[str, float]]:
        kind = spec.kind
        steps = spec.steps
        full = self._forged(probe, neutral, spec.forge_scale)
        rest = self._forged(probe, neutral, 0.0)  # == neutral
        if kind is SupplyAttackPattern.WASH_MINT:
            return [dict(full) for _ in range(steps)]
        if kind is SupplyAttackPattern.BURN_PARK:
            return [dict(probe) for _ in range(steps)]
        if kind in (
            SupplyAttackPattern.ROUND_TRIP,
            SupplyAttackPattern.RESONANCE,
        ):
            # round_trip is ONE excursion (the clawback test);
            # resonance is N cycles at the cadence (the ratchet test)
            cycles = (
                1
                if kind is SupplyAttackPattern.ROUND_TRIP
                else spec.cycles
            )
            series: list[dict[str, float]] = []
            for _ in range(cycles):
                series.extend([dict(full) for _ in range(spec.hold)])
                series.extend([dict(rest) for _ in range(spec.hold)])
            while len(series) < steps:
                series.append(dict(rest))
            return series[:steps]
        if kind is SupplyAttackPattern.CREEP:
            series = []
            for t in range(steps):
                factor = min(1.0, spec.creep_rate * (t + 1))
                series.append(self._forged(probe, neutral, factor))
            return series
        raise AssertionError(f"unhandled pattern {kind}")

    # -- measurement ------------------------------------------------

    def run_pattern(self, spec: SupplySpec) -> SupplyAttackBound:
        """One pattern against this driver. Deterministic."""
        kind = spec.kind
        probe = self._probe(kind)
        vacuous_note: str | None = None
        if probe is None:
            vacuous_note = (
                f"driver declares no "
                f"{'burn' if kind is SupplyAttackPattern.BURN_PARK else 'mint'} "
                f"probe state; no declared signal to forge"
            )
        else:
            probe_pressure = self._fn_abs(probe)
            if probe_pressure < _ZERO_PRESSURE:
                vacuous_note = (
                    "declared probe exerts zero supply pressure; "
                    "no signal to forge"
                )
        if vacuous_note is not None:
            # Honest vacuity — never a silent 0.0 (§20 convention).
            return SupplyAttackBound(
                kind=kind,
                driver=self.driver.name,
                pattern_metrics={},
                base_metrics={},
                edge={},
                bound_metrics=[],
                headline=None,
                headline_metric=None,
                vacuous=True,
                note=vacuous_note,
            )

        assert probe is not None
        neutral = self._neutral_state(probe)
        pattern = [self.driver.supply_fn(s) for s in self._series(spec, probe, neutral)]
        base = [self.driver.supply_fn(s) for s in self._base_series(spec, neutral)]
        n = len(pattern)
        assert n == len(base) > 0

        pattern_minted = math.fsum(v for v in pattern if v > 0)
        base_minted = math.fsum(v for v in base if v > 0)
        pattern_burned = math.fsum(-v for v in pattern if v < 0)
        base_burned = math.fsum(-v for v in base if v < 0)

        pattern_metrics: dict[str, float] = {
            "total_minted": pattern_minted,
            "total_burned": pattern_burned,
            "final_rate": pattern[-1],
            "max_abs_rate": max(abs(v) for v in pattern),
        }
        base_metrics: dict[str, float] = {
            "total_minted": base_minted,
            "total_burned": base_burned,
            "final_rate": base[-1],
            "max_abs_rate": max(abs(v) for v in base),
        }
        edge = {
            k: pattern_metrics[k] - base_metrics[k]
            for k in pattern_metrics
        }
        # r47: NEVER coerce a non-finite edge to 0.0 — that turns a
        # diverging runaway (the worst possible signal) into "no edge",
        # the §20 anti-hiding failure class one level down. Record the
        # divergence and remove the metric from headline arithmetic;
        # the bound reports the divergence explicitly instead.
        diverged_metrics = tuple(
            sorted(k for k, v in edge.items() if not math.isfinite(v))
        )
        edge = {k: v for k, v in edge.items() if math.isfinite(v)}

        if kind is SupplyAttackPattern.WASH_MINT:
            bound_metrics = ["total_minted"]
            note = "sustained forged mint signal vs neutral base"
        elif kind is SupplyAttackPattern.ROUND_TRIP:
            bound_metrics = ["total_minted", "final_rate"]
            _fr = edge.get("final_rate")
            note = (
                "up-leg mint not clawed back on release legs "
                f"(final-rate residue {abs(_fr):.3f})"
                if _fr is not None
                else "up-leg mint not clawed back on release legs "
                "(final-rate residue diverged)"
            )
        elif kind is SupplyAttackPattern.RESONANCE:
            bound_metrics = ["total_minted", "final_rate"]
            note = (
                f"{spec.cycles} strike-release cycles; per-cycle "
                "ratcheting check"
            )
        elif kind is SupplyAttackPattern.CREEP:
            bound_metrics = ["total_minted"]
            note = "sub-threshold signal accumulation over the grind"
        else:  # BURN_PARK
            bound_metrics = ["total_burned"]
            note = "sustained forged burn signal; drain depth"

        # Divergence dominates the headline: a diverged bound-metric is
        # the worst possible measurement (infinite edge), so it wins the
        # headline slot over every finite candidate.
        diverged_bound = [m for m in bound_metrics if m in diverged_metrics]
        candidates = [
            abs(edge[m]) for m in bound_metrics if m in edge
        ]
        headline: float | None
        headline_metric: str | None
        if diverged_bound:
            headline = math.inf
            headline_metric = diverged_bound[0]
            note = (
                f"{note} | DIVERGED: supply function ran away to a "
                f"non-finite rate on {', '.join(diverged_bound)} — "
                "unbounded extraction, scored at the floor"
            )
        else:
            headline = max(candidates) if candidates else None
            # deterministic worst-metric selection (tie -> first in list)
            headline_metric = None
            if candidates:
                worst = max(candidates)
                for m in bound_metrics:
                    if m in edge and abs(edge[m]) == worst:
                        headline_metric = m
                        break

        return SupplyAttackBound(
            kind=kind,
            driver=self.driver.name,
            pattern_metrics=pattern_metrics,
            base_metrics=base_metrics,
            edge=edge,
            bound_metrics=bound_metrics,
            headline=headline,
            headline_metric=headline_metric,
            vacuous=False,
            note=note,
            diverged_metrics=diverged_metrics,
        )

    def _base_series(
        self, spec: SupplySpec, neutral: dict[str, float]
    ) -> list[dict[str, float]]:
        """The matched honest base: the neutral state held for the
        whole window (the §20 matched-base convention — same shape,
        no manipulation)."""
        return [dict(neutral) for _ in range(spec.steps)]

    def run_all(self, steps: int = 60) -> list[SupplyAttackBound]:
        """Every pattern against this driver, deterministic order."""
        return [
            self.run_pattern(SupplySpec(kind=k, steps=steps))
            for k in SupplyAttackPattern
        ]


def run_supply_battery(
    driver: SupplyDriver, steps: int = 60
) -> list[SupplyAttackBound]:
    """Convenience entry: every pattern against one driver."""
    return SupplyAttackBattery(driver).run_all(steps)


def resolve_signal(
    driver: SupplyDriver,
) -> tuple[str, dict[str, float], dict[str, float]] | None:
    """(axis, neutral, probe) for the driver's dominant signal.

    The axis is the probe key with the LARGEST displacement from its
    neutral value (deterministic tie-break by key name) — the signal
    the probe was written to exercise. Returns None when the driver
    declares no probe or the probe exerts zero displacement (the
    vacuity conventions above).

    Shared resolution point: the r43 stock layer composes demand
    paths onto this same axis, so the battery and the stock layer can
    never disagree about what a driver's signal IS.
    """
    bat = SupplyAttackBattery(driver)
    probe = bat._probe(SupplyAttackPattern.WASH_MINT)
    if probe is None:
        probe = bat._probe(SupplyAttackPattern.BURN_PARK)
    if probe is None:
        return None
    neutral = bat._neutral_state(probe)
    diffs = {
        k: abs(probe[k] - neutral.get(k, probe[k])) for k in probe
    }
    if not diffs or max(diffs.values()) == 0.0:
        return None
    axis = max(diffs, key=lambda k: (diffs[k], k))
    return axis, neutral, probe
