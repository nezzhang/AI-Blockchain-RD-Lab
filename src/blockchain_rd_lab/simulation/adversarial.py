"""§15 adversarial attack-pattern battery: bound the named residuals.

The §15 scenario battery stresses a mechanism against NATURE (single
shocks: crashes, bank runs, oracle failures). The §20 red team names
attacker CHOREOGRAPHIES — multi-step input patterns crafted to harvest
the mechanism's own design asymmetries. Rounds 5-6 left those residuals
qualitatively bounded ("bounded per swing", "reduced to a frontier"):
this module executes each named pattern against the FINAL stored model
version and reports the number §2 demands — the deterministic,
reproducible (§21) bound on the extracted edge.

Every pattern is pure deterministic code shaping the model's INPUT rows
(X_t / dX_t and declared per-step parameters); nothing else varies. The
battery reuses MechanismSimulation.run() unchanged — the same §14
interpreter, invariant checks, and metrics — so an adversarial bound
composes with every model the lab formalizes, not just the current one.

Measurement: a pattern BOUND is defined per pattern from run history
(the premium overpaid per voucher, the subsidy extracted, the escrow
drained, or the margin trough depth), always comparing the crafted
pattern against a matched no-attack BASE run of the same length — so
the reported number is the ATTACKER'S EDGE, not the mechanism's
background behavior. Failed patterns (interpreter errors) are reported,
never hidden (§29).

This is §27 support: the release package's §4 residual disclosure can
now carry `bounded by <pattern>: <number>` per surface — evidence
replacing adjectives.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import MechanismSimulation, SimulationRun


class AttackPattern(StrEnum):
    """Named attacker choreographies (§20 findings this battery bounds).

    The four families the round-5/6 residual disclosures actually named;
    each shapes the input series the way the described attacker would.
    """

    VOL_OSCILLATION = "vol_oscillation"  # dv_t upswing cycling / oscillation on dv_t
    WASH_FLOW = "wash_flow"  # sustained wash patterns pinning measured vol high
    PUMP_UNWIND = "pump_unwind"  # manufacture vol, harvest premium, unwind
    SHOCK_TIMING = "shock_timing"  # spike timed into the subsidy trough


class PatternSpec(BaseModel):
    """Deterministic parameters of one crafted attack series."""

    kind: AttackPattern
    steps: int = 60
    # vol_oscillation / pump_unwind: the attacker's crafted |ΔX| amplitude
    amplitude: float = 0.05
    # wash_flow: sustained mild elevation fraction added to every step
    wash_level: float = 0.02
    # shock_timing: fraction of the window the defender lags
    lag_fraction: float = 0.2


class AttackBound(BaseModel):
    """The deterministic result of one adversarial pattern run."""

    model_config = {"validate_assignment": True}

    kind: AttackPattern
    pattern_metrics: dict[str, float] = Field(default_factory=dict)
    base_metrics: dict[str, float] = Field(default_factory=dict)
    # The attacker's edge: pattern metric minus matched-base metric.
    edge: dict[str, float] = Field(default_factory=dict)
    # Names of the metrics that define this pattern's bound (the worst
    # of these is the headline number for the release disclosure).
    bound_metrics: list[str] = Field(default_factory=list)
    headline: float | None = None
    headline_metric: str | None = None
    vacuous: bool = False
    failures: list[str] = Field(default_factory=list)


def _state_var_order(model: MathModel) -> list[str]:
    """State symbols in declaration order (primary first)."""
    return [v.symbol for v in model.variables if v.role == "state"]


class AttackPatternBattery:
    """Run §20-named adversarial input patterns against one model."""

    def __init__(self, model: MathModel) -> None:
        self.model = model
        self._inputs = [v.symbol for v in model.variables if v.role == "input"]
        if not self._inputs:
            raise ValueError("model declares no input variables to attack")

    # -- pattern series -------------------------------------------------------

    def craft_series(self, spec: PatternSpec) -> list[dict[str, float]]:
        """The attacker's input rows, shaped per pattern (deterministic).

        All patterns target the anchor pair (X_t, dX_t) — the §15
        AnchorSeriesGenerator's rows — expressed the way each §20 finding
        describes the attacker's actual move.
        """
        rows: list[dict[str, float]] = []
        if spec.kind is AttackPattern.VOL_OSCILLATION:
            # Alternate large |ΔX| with quiet steps: every rise is a
            # fresh positive vol change (dv_t > 0), every fall costs the
            # attacker nothing (asymmetric pricing reads only upswings).
            x = 1000.0
            for t in range(spec.steps):
                dx = (x * spec.amplitude) if t % 2 == 0 else 0.0
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        if spec.kind is AttackPattern.WASH_FLOW:
            # Sustained mild elevation: pins measured vol high while the
            # wash costs only mild |ΔX| per step.
            x = 1000.0
            for t in range(spec.steps):
                sign = 1.0 if t % 2 == 0 else -1.0
                dx = sign * x * spec.wash_level
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        if spec.kind is AttackPattern.PUMP_UNWIND:
            # Ramp up hard (manufacture vol), then stop (EMA window
            # reverts) — the classic pump then unwind before reversion.
            x = 1000.0
            ramp = spec.steps // 2
            for t in range(spec.steps):
                dx = x * spec.amplitude if t < ramp else 0.0
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        # SHOCK_TIMING: a spike timed into the defender's lag window —
        # quiet until mid-window, one hard shock, then quiet again.
        x = 1000.0
        hit = max(1, int(spec.steps * (1.0 - spec.lag_fraction)))
        for t in range(spec.steps):
            dx = x * 0.5 if t == hit else 0.0
            rows.append({"X_t": x, "dX_t": dx})
            x += dx
        return rows

    def base_series(self, spec: PatternSpec) -> list[dict[str, float]]:
        """The matched no-attack base: same length, mild natural noise."""
        x = 1000.0
        rows: list[dict[str, float]] = []
        for _ in range(spec.steps):
            dx = x * 0.0002  # §15 BASE mean drift
            rows.append({"X_t": x, "dX_t": dx})
            x += dx
        return rows

    # -- extraction metrics ---------------------------------------------------

    def extract_metrics(
        self, run: SimulationRun, spec: PatternSpec
    ) -> dict[str, float]:
        """Pattern-specific extraction measures from run history.

        Metrics are named after what the attacker extracts, computed
        from the same symbols the model declares (§13 guarantees the
        roles; the interpreter guarantees the values):
        - premium_paid: Σ π_t over the window (voucher-side overpay)
        - subsidy_deployed: Σ max(0, g_target - G) flows when a subsidy
          state exists (the escrow's counter-cyclical spend)
        - escrow_drawn: B_0 - min(B) over the window (worst drain)
        - vol_separation: mean(v) under attack minus under base
        """
        hist = run.history
        if not hist:
            return {}
        out: dict[str, float] = {}
        premium_keys = [k for k in hist[0] if k.startswith("pi_") and not k.endswith("1")]
        if premium_keys:
            key = premium_keys[0]
            out["premium_paid"] = sum(float(r.get(key, 0.0)) for r in hist)
        # generic drainage: any state whose symbol starts with B or R
        stock_symbols = [
            v.symbol
            for v in self.model.variables
            if v.role == "state"
            and (v.symbol.startswith("B") or v.symbol.startswith("R"))
            and "1" not in v.symbol
        ]
        for sym in stock_symbols:
            vals = [float(r.get(sym, 0.0)) for r in hist if sym in r]
            if vals:
                out[f"{sym}_drawn"] = vals[0] - min(vals)
        if "v_t" in hist[0]:
            out["mean_measured_vol"] = sum(float(r.get("v_t", 0.0)) for r in hist) / len(hist)
        return out

    # -- run -------------------------------------------------------------------

    def run_pattern(self, spec: PatternSpec) -> AttackBound:
        sim = MechanismSimulation(self.model)
        pat = sim.run(self.craft_series(spec))
        base = MechanismSimulation(self.model).run(self.base_series(spec))

        pm = self.extract_metrics(pat, spec)
        bm = self.extract_metrics(base, spec)
        edge = {
            k: round(pm[k] - bm.get(k, 0.0), 6)
            for k in pm
            if k in bm
        }

        # The headline bound: the largest positive extraction the pattern
        # achieves over base, excluding pure background metrics.
        bound_candidates = {
            k: v for k, v in edge.items() if v > 0 and k != "mean_measured_vol"
        }
        # vol separation IS the bound for wash/pump (the vol premium is
        # the harvest), so include it when no stock/premium metric moved.
        if not bound_candidates and "mean_measured_vol" in edge:
            bound_candidates = {"mean_measured_vol": edge["mean_measured_vol"]}
        headline = max(bound_candidates.values()) if bound_candidates else 0.0
        headline_metric = (
            max(bound_candidates, key=lambda k: bound_candidates[k])
            if bound_candidates
            else None
        )

        # §15 evidence quality: a saturated model exercises no dynamics —
        # the pattern is indistinguishable from base not because the
        # design bounds the attack, but because nothing responds. That
        # is a VACUOUS bound, not a zero bound (§2/§29).
        vacuous = bool(pat.degenerate or base.degenerate)

        return AttackBound(
            kind=spec.kind,
            pattern_metrics=pm,
            base_metrics=bm,
            edge=edge,
            bound_metrics=sorted(bound_candidates),
            headline=None if vacuous else round(headline, 6),
            headline_metric=None if vacuous else headline_metric,
            vacuous=vacuous,
            failures=list(pat.failures) + list(base.failures),
        )

    def run_all(self, steps: int = 60) -> list[AttackBound]:
        """The full named-pattern battery (§4 residual bounding)."""
        return [
            self.run_pattern(
                PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=steps)
            ),
            self.run_pattern(PatternSpec(kind=AttackPattern.WASH_FLOW, steps=steps)),
            self.run_pattern(
                PatternSpec(kind=AttackPattern.PUMP_UNWIND, steps=steps)
            ),
            self.run_pattern(PatternSpec(kind=AttackPattern.SHOCK_TIMING, steps=steps)),
        ]
