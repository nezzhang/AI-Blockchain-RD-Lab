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

import re
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
    # Move once, then PARK: a permanent level shift that stops moving.
    # Exposes anchor-heal designs — protection keyed to a 1000-anchored
    # reverting EMA "heals" to the anchor once dX=0, right when the
    # regime is permanently moved (tail cover sold at zero premium).
    # None of the four original choreographies parks: wash/pump/osc move
    # repeatedly, shock reverts. The r13 heal findings were invisible to
    # the r10/r11 battery exactly because this pattern was missing.
    CRASH_PARK = "crash_park"
    # Sustained sub-threshold drift: a constant grind (+0.5%/step by
    # default, +35% cumulative over the window) that never trips any
    # single-step spike trigger. Exposes LEAKAGE designs — protection
    # states that lag a slowly-moving regime accumulate a standing
    # wedge (fee/pool mispricing) for the drift's whole duration,
    # while single-step defenses see nothing. The r16 v2 separation-key
    # claim ("drift-paced farming closed") was red-team HYPOTHESIS;
    # this choreography measures it (§2: code tests).
    DRIFT_CREEP = "drift_creep"


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
    # crash_park: the one-shot level shift fraction (negative = crash)
    park_shift: float = -0.6
    # crash_park: step index of the one-shot shift (mid-window default)
    park_at: int = 20
    # drift_creep: the constant per-step drift fraction (the grind rate)
    creep_rate: float = 0.005


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
    # CRASH_PARK only: per keyed protection state, the parked signal as a
    # fraction of its crash-time peak (heal ratio). < 0.25 while the
    # level stays moved = the anchor-heal flaw (r13 finding class):
    # protection decays to zero right when tail risk is maximal.
    heal_flags: dict[str, float] = Field(default_factory=dict)
    # Park-style patterns only: EMA-of-level states' _drawn excursions
    # reclassified as REGIME TRACKING (the state following the moved
    # level — a design property, not an attacker extraction; r14 4b
    # honesty fix).
    regime_tracking: dict[str, float] = Field(default_factory=dict)
    # Park-style patterns only: excursions that RECOVER by the parked
    # window's end (< 25% of peak displacement) reclassified as
    # TRANSIENT (the crash's own cost, re-normalized; r15 honesty fix).
    transient_recovered: dict[str, float] = Field(default_factory=dict)
    # drift_creep only: per level-denominated state, how much MORE the
    # state lags the level under sustained drift than under base — the
    # RESPONSIVENESS gap (r17). Disclosed as a design cost; it becomes
    # an attacker edge only when another state keys off it (then it
    # also appears in the headline via the keyed wedge).
    drift_wedges: dict[str, float] = Field(default_factory=dict)


def _state_var_order(model: MathModel) -> list[str]:
    """State symbols in declaration order (primary first)."""
    return [v.symbol for v in model.variables if v.role == "state"]


def _eq_symbols(model: MathModel) -> dict[str, set[str]]:
    """Map each equation's LHS symbol -> symbols its RHS reads."""
    out: dict[str, set[str]] = {}
    for eq in model.equations:
        lhs = eq.expression.split("=", 1)[0].strip()
        if lhs:
            out[lhs] = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", eq.expression))
    return out



def _ema_of_level_states(model: MathModel) -> set[str]:
    """States that are EMAs of the input level itself (r14 4b honesty).

    A state whose defining equation reads only itself and X_t (an EMA
    of the level) REGIME-TRACKS: under a move-then-park choreography
    its _drawn excursion is the state FOLLOWING the moved level — a
    design property, not an attacker extraction. The r13/r14 finding:
    the crash_park headline (and pump_unwind's parked half) was carried
    entirely by such states (600 = the EMA moving to the new level =
    the FIX working), which the 4b disclosure then published as a
    'measured attacker edge' — a misleading disclosure. Classified
    here, measured once, reported as regime-tracking downstream.
    """
    eqs = _eq_symbols(model)
    # symbols that are NOT structural: function names (clip/max/min/...)
    # and parameters may appear in an EMA's equation without breaking
    # the "reads itself + the level only" shape.
    nonstructural = {"clip", "max", "min", "abs", "sqrt", "ln", "exp",
                     "sum", "mean", "std"} | {
        v.symbol for v in model.parameters
    } if hasattr(model, "parameters") else {"clip", "max", "min", "abs",
                                            "sqrt", "ln", "exp", "sum",
                                            "mean", "std"}
    out: set[str] = set()
    for v in model.variables:
        if v.role != "state":
            continue
        sym = v.symbol
        reads = eqs.get(f"{sym}1", set()) | eqs.get(sym, set())
        if not reads:
            continue
        structural = {r for r in reads if r not in nonstructural}
        if structural <= {sym, f"{sym}1", "X_t"}:
            out.add(sym)
    return out

def _keyed_protection_states(model: MathModel, hist: list[dict[str, float]]) -> list[str]:
    """States whose dynamics depend on the model's trend/EMA states.

    The protection signal in anchored-trend designs is the state keyed
    to |T-1000| or the drawdown/alarm derived from T. We approximate
    "keyed" structurally: a state whose defining equation reads a state
    OTHER than itself (its response is driven by the protection-signal
    chain), excluding the EMA states themselves (they ARE the flaw, not
    the signal). Falls back to the primary state when nothing matches —
    the primary state is the mechanism's headline stock.
    """
    states = _state_var_order(model)
    eqs = _eq_symbols(model)
    # a state's defining equation assigns <symbol>1
    def reads_of(sym: str) -> set[str]:
        return eqs.get(f"{sym}1", set()) | eqs.get(sym, set())

    emas = [
        s for s in states
        if (r := reads_of(s)) and r <= {s, f"{s}1", "X_t", "dX_t"}
    ]
    keyed = [
        s for s in states
        if s not in emas and reads_of(s) & (set(states) - {s, f"{s}1"})
    ]
    if not keyed:
        keyed = [states[0]] if states else []
    # only report states that actually appear in the run history
    return [s for s in keyed if s in hist[0]]


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
        if spec.kind is AttackPattern.SHOCK_TIMING:
            x = 1000.0
            hit = max(1, int(spec.steps * (1.0 - spec.lag_fraction)))
            for t in range(spec.steps):
                dx = x * 0.5 if t == hit else 0.0
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        # CRASH_PARK: move once, then park — dX=0 forever after. The
        # choreography that exposes anchor-heal designs: protection keyed
        # to a 1000-anchored reverting EMA heals to the anchor right
        # when the regime is permanently moved.
        if spec.kind is AttackPattern.CRASH_PARK:
            x = 1000.0
            at = max(1, min(spec.park_at, spec.steps - 2))
            for t in range(spec.steps):
                dx = x * spec.park_shift if t == at else 0.0
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        # DRIFT_CREEP: a constant per-step grind — movement too slow to
        # trip any single-step spike trigger, sustained the whole window.
        # The boiling-frog family: leakage designs (protection lagging a
        # slowly-moving regime) accumulate a standing wedge every step.
        if spec.kind is AttackPattern.DRIFT_CREEP:
            x = 1000.0
            for _ in range(spec.steps):
                dx = x * spec.creep_rate
                rows.append({"X_t": x, "dX_t": dx})
                x += dx
            return rows
        raise ValueError(f"unhandled pattern: {spec.kind}")  # pragma: no cover

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
        # generic drainage: EVERY declared state is a potential stock the
        # attacker drains (bonds, reserves, escrows, pools — the symbol
        # letter is a naming convention, not a semantic guarantee; §13
        # only guarantees the ROLE). The r10 fix: the old B_/R_ prefix
        # pattern left S_/J_/G_/W_-named stocks unmeasured, and their
        # models reported false "bounded by zero" headlines.
        stock_symbols = [
            v.symbol
            for v in self.model.variables
            if v.role == "state" and "1" not in v.symbol
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
        # r14/r15 4b honesty: under park-style choreographies (crash_park;
        # pump_unwind's parked half), a regime-tracking EMA's _drawn is
        # the state FOLLOWING the moved level — the fix working, not an
        # extraction. Exclude those metrics from the attacker-edge
        # headline and record them separately as regime tracking.
        regime_tracking: dict[str, float] = {}
        # r17 drift-creep honesty. TWO layers:
        # (1) METRIC: the extraction this pattern farms is the WEDGE —
        #     how much MORE the protection lags the level under drift
        #     than under base. The generic _drawn metric (pattern-vs-
        #     base STATE delta) is blind to it: under drift BOTH runs
        #     move their states, and the lag-vs-level cancels out of
        #     the subtraction. The honest metric is per-state
        #     |state - X| at window end, pattern minus base.
        # (2) CLASSIFICATION: a state that ends AT the drifted level
        #     kept pace — its excursion is the tracking itself (regime
        #     tracking, not a harvest). A state that lags accumulates
        #     the standing wedge: that stays in the headline, because
        #     mispriced protection over a grinding regime is exactly
        #     what the drift attacker farms.
        drift_wedges: dict[str, float] = {}
        if spec.kind is AttackPattern.DRIFT_CREEP:
            pat_hist = pat.history
            base_hist = base.history
            if pat_hist and base_hist:
                x_p = float(pat_hist[-1]["X_t"])
                x_b = float(base_hist[-1]["X_t"])
                state_syms = {
                    k[: -len("_drawn")]
                    for k in edge
                    if k.endswith("_drawn")
                }
                for sym in sorted(state_syms):
                    if sym not in pat_hist[-1] or sym not in base_hist[-1]:
                        continue
                    # Level-denominated only (deterministic): under the
                    # BASE run the state sits at level scale (within 25%
                    # of X). A fee (F_t ~600 at X~1000), a pressure
                    # signal, or a zero-scale kicker is NOT level-
                    # denominated — its |state - X| is meaningless and a
                    # wedge metric on it would be a false disclosure.
                    if abs(float(base_hist[-1][sym]) - x_b) > 0.25 * max(x_b, 1.0):
                        continue
                    wedge_p = abs(float(pat_hist[-1][sym]) - x_p)
                    wedge_b = abs(float(base_hist[-1][sym]) - x_b)
                    wedge = round(wedge_p - wedge_b, 6)
                    if wedge > 0:
                        drift_wedges[f"{sym}_wedge"] = wedge
                        # r17 attribution honesty (measured, not assumed):
                        # the wedge itself is a RESPONSIVENESS gap — the
                        # state lags the regime. It is an attacker edge
                        # ONLY if the lag propagates into a consumer
                        # response the attacker harvests (a paid flow /
                        # fee / premium). That harvest is exactly the
                        # consumer-response metric this battery already
                        # measures per pattern; asserting it from
                        # structure (keyed-state shape) alone would
                        # over-attribute — the r16 v2's slow anchor lags
                        # 326 under drift, but its consumer keys the
                        # ANCHOR SEPARATION, which stays at 1.04: nothing
                        # to harvest. So wedges are DISCLOSED here and
                        # enter the headline only via measured consumer
                        # responses (the generic metrics), never by
                        # structural inference.
            if pat_hist:
                x_final = float(pat_hist[-1]["X_t"])
                for k in list(bound_candidates):
                    if not k.endswith("_drawn"):
                        continue
                    sym = k[: -len("_drawn")]
                    if sym not in pat_hist[0]:
                        continue
                    final_v = float(pat_hist[-1].get(sym, 0.0))
                    if abs(final_v - x_final) < 0.10 * max(x_final, 1.0):
                        regime_tracking[k] = bound_candidates.pop(k)
        # r15 transient-recovery honesty: an excursion that RECOVERS by
        # the parked window's end (< 25% of its peak displacement from
        # the pre-crash baseline) is the crash's own transient cost —
        # the state re-normalized (the r15 FX-matching finding: M_t's
        # 96-unit collapse at the crash step recovered fully under
        # park; publishing it as an 'attacker edge' misreads a one-step
        # crash cost as an extraction). Measured on the pattern run.
        transient_recovered: dict[str, float] = {}
        if spec.kind in (AttackPattern.CRASH_PARK, AttackPattern.PUMP_UNWIND):
            pat_hist = pat.history
            x_final = float(pat_hist[-1]["X_t"]) if pat_hist else 1000.0
            # r15b shape-independent extension: a state that ENDS AT the
            # moved level (|final - X_final| < 10% of the level) followed
            # the regime — its _drawn excursion is the re-basing itself
            # (the r15 successor pool reads a stress aux, so the r14
            # shape filter missed it; the numeric check measures the
            # actual semantics: did the state arrive at the level?)
            if pat_hist:
                for k in list(bound_candidates):
                    if not k.endswith("_drawn"):
                        continue
                    sym = k[: -len("_drawn")]
                    if sym not in pat_hist[0]:
                        continue
                    final_v = float(pat_hist[-1].get(sym, 0.0))
                    if abs(final_v - x_final) < 0.10 * max(x_final, 1.0):
                        regime_tracking[k] = bound_candidates.pop(k)
            emas = _ema_of_level_states(self.model)
            for sym in emas:
                k = f"{sym}_drawn"
                if k in bound_candidates:
                    regime_tracking[k] = bound_candidates.pop(k)
            if pat_hist:
                at = max(1, min(getattr(spec, "park_at", 20),
                                spec.steps - 2))
                if spec.kind is AttackPattern.PUMP_UNWIND:
                    at = spec.steps // 2  # the parked half begins mid-run
                for k in list(bound_candidates):
                    if not k.endswith("_drawn"):
                        continue
                    sym = k[: -len("_drawn")]
                    if sym not in pat_hist[0]:
                        continue
                    base_v = float(pat_hist[max(0, at - 1)].get(sym, 0.0))
                    disp = [abs(float(r[sym]) - base_v) for r in pat_hist[at:]]
                    if not disp:
                        continue
                    peak = max(disp)
                    if peak > 1.0 and disp[-1] < 0.25 * peak:
                        transient_recovered[k] = round(disp[-1] / peak, 6)
                        bound_candidates.pop(k)
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

        # §20 honesty: a model whose declared symbols match NO metric
        # pattern (no premium π_*, no stock B_*/R_*, no measured vol v_t)
        # is UNMEASURABLE by this battery — reporting headline=0.0 would
        # be a false "bounded by zero" claim. That is the same vacuity
        # class as saturation: no evidence, never zero (§2/§29).
        if not edge and not vacuous:
            vacuous = True

        # ANCHOR-HEAL flag (the r13 finding class): under CRASH_PARK the
        # keyed states are the model's PROTECTION signals. A signal whose
        # DISPLACEMENT from its pre-crash baseline peaks at the crash then
        # heals below ~25% of peak while the level stays >50% moved means
        # protection decays to zero exactly when tail risk is maximal —
        # tail cover sold at anchor-normal premium. Displacement, not raw
        # magnitude: a state sitting near 1000 by convention must not
        # read as "signal" merely for being large. This is a MEASUREMENT
        # on the bound; interpretation is per-mechanism — a re-banding
        # design (the r12 meter) INTENDS its exceedance to heal after
        # re-centering; an insurance/alarm design must not heal.
        heal_flags: dict[str, float] = {}
        if spec.kind is AttackPattern.CRASH_PARK:
            hist = pat.history
            if hist:
                moved = abs(hist[-1]["X_t"] - 1000.0) > 0.5 * 1000.0
                if moved:
                    at = max(1, min(spec.park_at, spec.steps - 2))
                    keyed = _keyed_protection_states(self.model, hist)
                    post = hist[at:]  # crash response only — exclude the
                    # model's own initialization transient (state seeding
                    # at 1000 and decaying to its natural level is not a
                    # protection signal; r13 measurement bug caught in
                    # review: O_t's t0 displacement was init, not crash)
                    for sym in keyed:
                        base_v = float(hist[at - 1].get(sym, 0.0))
                        disp = [
                            abs(float(r[sym]) - base_v) for r in post if sym in r
                        ]
                        peak = max(disp)
                        if peak > 1.0:  # a real signal, not noise floor
                            heal_flags[sym] = round(disp[-1] / peak, 6)

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
            heal_flags=heal_flags,
            regime_tracking=regime_tracking,
            transient_recovered=transient_recovered,
            drift_wedges=drift_wedges,
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
            self.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK, steps=steps)),
            self.run_pattern(PatternSpec(kind=AttackPattern.DRIFT_CREEP, steps=steps)),
        ]
