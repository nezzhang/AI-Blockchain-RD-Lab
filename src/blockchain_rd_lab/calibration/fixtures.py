"""Known-mechanism calibration fixtures.

Each fixture encodes the CORE DYNAMICS of a mechanism whose real-world
properties are established consensus, in the same §13 MathModel DSL the
lab's candidates use (anchor inputs X_t/dX_t, states seeded at 1000,
stepped S_t1 roll-forward). The encoding is faithful to the referent's
feedback structure, not a full implementation; where fidelity is an
assumption, the expectation rationale says INFERENCE (§29).

Two negative controls (known-good: the batteries must NOT report a
fatal edge) and two positive controls (known-flawed: the batteries MUST
surface the documented failure mode). A suite that only confirms good
news would be marketing; the flawed fixtures are the ones that give the
good fixtures their meaning.
"""

from __future__ import annotations

from blockchain_rd_lab.calibration import (
    CalibrationFixture,
    CheckKind,
    ConsensusClass,
    Expectation,
    RatioDirection,
)
from blockchain_rd_lab.formalization import (
    MathModel,
    ModelAssumption,
    ModelConstraint,
    ModelEquation,
    ModelParameter,
    ModelVariable,
    VariableRole,
)
from blockchain_rd_lab.simulation import ScenarioKind
from blockchain_rd_lab.simulation.adversarial import FLAW_EDGE_THRESHOLD, AttackPattern


def _var(name: str, symbol: str, role: VariableRole, description: str) -> ModelVariable:
    return ModelVariable(name=name, symbol=symbol, role=role, description=description)


def _par(
    name: str, symbol: str, description: str, default: float, lo: float, hi: float
) -> ModelParameter:
    return ModelParameter(
        name=name, symbol=symbol, description=description,
        default=default, min_value=lo, max_value=hi,
    )


def _eq(name: str, expression: str, description: str = "") -> ModelEquation:
    return ModelEquation(name=name, expression=expression, description=description)


def _asm(statement: str, critical: bool = False) -> ModelAssumption:
    return ModelAssumption(statement=statement, critical=critical)


def _con(statement: str, kind: str = "invariant") -> ModelConstraint:
    return ModelConstraint(statement=statement, kind=kind)


_ANCHOR_INPUTS = [
    _var("level", "X_t", VariableRole.INPUT, "anchor level"),
    _var("delta", "dX_t", VariableRole.INPUT, "anchor level change"),
]


def pid_anchor_controller() -> CalibrationFixture:
    """Known-good negative control: relative-error PID feedback tracking a
    slow trend EMA of the anchor, with a clipped (anti-windup) integrator —
    the textbook bounded-output stabilizer, stable in any regime."""
    model = MathModel(
        candidate_id="fixture-pid-anchor-controller",
        variables=[
            *_ANCHOR_INPUTS,
            _var("trend", "X_m", VariableRole.STATE, "slow trend EMA of the anchor"),
            _var("trend_next", "X_m1", VariableRole.STATE, "next trend"),
            _var("integral", "I_t", VariableRole.STATE, "leaky integral of relative error"),
            _var("integral_next", "I_t1", VariableRole.STATE, "next integral"),
            _var("control", "U_t", VariableRole.STATE, "published control adjustment"),
            _var("control_next", "U_t1", VariableRole.STATE, "next control adjustment"),
            _var("error", "err", VariableRole.AUXILIARY, "relative tracking error vs trend"),
        ],
        parameters=[
            _par("km", "km", "trend EMA speed", 0.05, 0.01, 0.5),
            _par("kp", "kp", "proportional gain", 2.0, 0.0, 10.0),
            _par("ki", "ki", "integral gain", 0.1, 0.0, 1.0),
            _par("kd", "kd", "derivative gain (damps anchor jumps)", 1.0, 0.0, 10.0),
            _par("leak", "leak", "integrator leak (anti-windup)", 0.95, 0.5, 1.0),
        ],
        equations=[
            _eq(
                "trend",
                "X_m1 = clip(X_m + km*(X_t - X_m), 100.0, 100000.0)",
                "slow regime trend — the moving setpoint",
            ),
            _eq(
                "error",
                "err = (X_m - X_t) / max(X_m, 1.0)",
                "RELATIVE error vs trend: dimensionless, bounded in any regime "
                "(an absolute target under a drifting anchor is integral windup "
                "by construction — the first-draft encoding bug the suite caught)",
            ),
            _eq(
                "integral",
                "I_t1 = clip(leak*I_t + err, -50.0, 50.0)",
                "leaky, clipped integrator — the standard anti-windup bound",
            ),
            _eq(
                "control",
                "U_t1 = clip(kp*err + ki*I_t + kd*(0.0 - dX_t/max(X_t, 1.0)), -1.0, 1.0)",
                "bounded PID output: proportional + integral + derivative on the delta",
            ),
        ],
        assumptions=[_asm("anchor level observable each step", critical=True)],
        constraints=[
            _con("control output bounded to +/-1 by construction"),
        ],
        open_questions=[
            "is the integrator clip tight enough under repeated full-scale shocks?"
        ],
        rationale=(
            "PID feedback on the anchor's deviation from its own slow trend, "
            "with a leaky clipped integrator and clipped output. Bounded-input "
            "bounded-output in every regime by construction; the canonical "
            "stabilizer any evaluation instrument must NOT flag as flawed."
        ),
    )
    return CalibrationFixture(
        fixture_id="fixture-pid-anchor-controller",
        title="PID anchor controller",
        referent="Classical PID feedback control (textbook control theory)",
        consensus=ConsensusClass.KNOWN_GOOD,
        ground_truth=(
            "FACT: a PID loop with anti-windup clipping is BIBO-stable — the "
            "standard feedback stabilizer of control theory. INFERENCE: no §20 "
            "input choreography extracts a standing edge from a bounded "
            "controller output, so the strongest measured attack edge must stay "
            "under the canonical flaw threshold."
        ),
        model=model,
        expectations=[
            Expectation(
                kind=CheckKind.SCENARIOS_CLEAN,
                rationale=(
                    "FACT: no divisions or unclipped powers — no §15 scenario "
                    "can produce a numerical failure"
                ),
            ),
            Expectation(
                kind=CheckKind.NO_DEGENERATE,
                rationale=(
                    "INFERENCE: both states respond to the anchor through the "
                    "whole window — a live controller, not a saturated one"
                ),
            ),
            Expectation(
                kind=CheckKind.MAX_ATTACK_HEADLINE,
                threshold=FLAW_EDGE_THRESHOLD,
                rationale=(
                    "INFERENCE: a fatal-scale attacker edge (≥ the canonical "
                    "400) on a bounded stabilizer would be a battery FALSE "
                    "POSITIVE — the finding this control exists to catch"
                ),
            ),
        ],
    )



def utilization_kink_rate() -> CalibrationFixture:
    """Known-good negative control: the Compound/Aave-style kinked
    utilization-rate curve — rate tracks utilization with a slope jump
    past the kink, smoothed. The most deployed DeFi rate mechanism."""
    model = MathModel(
        candidate_id="fixture-utilization-kink-rate",
        variables=[
            *_ANCHOR_INPUTS,
            _var("rate", "R_t", VariableRole.STATE, "smoothed published rate"),
            _var("rate_next", "R_t1", VariableRole.STATE, "next rate"),
            _var("utilization", "util", VariableRole.AUXILIARY,
                 "anchor-position utilization proxy"),
            _var("rate_target", "r_tgt", VariableRole.AUXILIARY, "kinked rate target"),
        ],
        parameters=[
            _par("x_lo", "x_lo", "anchor level at 0% utilization", 500.0, 1.0, 5000.0),
            _par("x_hi", "x_hi", "anchor level at 100% utilization", 2000.0, 501.0, 1.0e6),
            _par("r_base", "r_base", "rate at zero utilization", 0.02, 0.0, 1.0),
            _par("slope", "slope", "rate slope below the kink", 0.1, 0.0, 1.0),
            _par("jump", "jump", "extra slope past the kink", 0.8, 0.0, 5.0),
            _par("kink", "kink", "utilization where the slope jumps", 0.8, 0.0, 1.0),
            _par("kr", "kr", "rate smoothing speed", 0.2, 0.01, 1.0),
        ],
        equations=[
            _eq(
                "utilization",
                "util = clip((X_t - x_lo) / max(x_hi - x_lo, 1.0), 0.0, 1.0)",
                "anchor position in the band, clipped to [0, 1]",
            ),
            _eq(
                "rate_target",
                "r_tgt = clip(r_base + slope*util + jump*max(util - kink, 0.0), 0.005, 0.9)",
                "kinked target: gentle slope, then a jump past the kink",
            ),
            _eq(
                "rate",
                "R_t1 = clip(R_t + kr*(r_tgt - R_t), 0.005, 0.9)",
                "smoothed publication: the rate EMA-tracks its target",
            ),
        ],
        assumptions=[_asm("anchor position is a usable utilization proxy", critical=True)],
        constraints=[
            _con("rate bounded to [0.005, 0.9] by construction"),
        ],
        open_questions=["does the anchor-band utilization proxy hold under regime shifts?"],
        rationale=(
            "Utilization-keyed kinked rate curve with smoothed publication — "
            "the Compound/Aave rate-rule shape. The rate FOLLOWS the regime; "
            "there is no stock to drain and no premium to harvest."
        ),
    )
    return CalibrationFixture(
        fixture_id="fixture-utilization-kink-rate",
        title="Utilization-kink rate curve",
        referent="Compound/Aave-style kinked utilization-rate rule",
        consensus=ConsensusClass.KNOWN_GOOD,
        ground_truth=(
            "FACT: kinked utilization-rate curves are the most deployed DeFi "
            "rate mechanism (Compound 2019; Aave), with no consensus fatal flaw "
            "in the rate rule itself — the documented risks are oracle and "
            "liquidity externalities outside this encoding. INFERENCE: the rate "
            "state tracks utilization regime shifts, which the battery's "
            "arrival/regime checks must read as following, not extraction."
        ),
        model=model,
        expectations=[
            Expectation(
                kind=CheckKind.SCENARIOS_CLEAN,
                rationale="FACT: guarded division and full clipping — no numerical failure mode",
            ),
            Expectation(
                kind=CheckKind.NO_DEGENERATE,
                rationale="INFERENCE: the rate keeps tracking utilization in every regime",
            ),
            Expectation(
                kind=CheckKind.MAX_ATTACK_HEADLINE,
                threshold=FLAW_EDGE_THRESHOLD,
                rationale=(
                    "INFERENCE: a fatal-scale edge on the deployed rate-rule "
                    "shape would be a battery FALSE POSITIVE"
                ),
            ),
        ],
    )



def vol_keyed_retention_ratchet() -> CalibrationFixture:
    """Known-flawed positive control: retention keyed to ABSOLUTE realized
    volatility feeding an integral escrow — the procyclical-margin class
    (VaR-style buffers). The lab's own r16 predecessor was rejected for
    exactly this ratchet; the battery MUST see it again here."""
    model = MathModel(
        candidate_id="fixture-vol-keyed-retention-ratchet",
        variables=[
            *_ANCHOR_INPUTS,
            _var("vol", "V_t", VariableRole.STATE, "realized-volatility EMA"),
            _var("vol_next", "V_t1", VariableRole.STATE, "next volatility"),
            _var("retention", "R_t", VariableRole.STATE, "retention fraction keyed to vol"),
            _var("retention_next", "R_t1", VariableRole.STATE, "next retention"),
            _var("escrow", "E_t", VariableRole.STATE, "integral escrow accumulator"),
            _var("escrow_next", "E_t1", VariableRole.STATE, "next escrow"),
            _var("activity", "act", VariableRole.AUXILIARY, "per-step fractional move"),
        ],
        parameters=[
            _par("kv", "kv", "volatility EMA speed", 0.9, 0.1, 1.0),
            _par("v_target", "v_target", "reference volatility", 0.01, 0.0001, 0.5),
            _par("r0", "r0", "retention at reference vol", 0.2, 0.0, 0.95),
            _par("kr", "kr", "procyclical retention gain", 8.0, 0.1, 50.0),
            _par("inflow", "inflow", "escrow inflow at full retention", 100.0, 1.0, 1000.0),
            _par("outflow", "outflow", "constant escrow outflow", 10.0, 0.0, 500.0),
        ],
        equations=[
            _eq("activity", "act = abs(dX_t) / max(X_t, 1.0)", "fractional per-step move"),
            _eq(
                "vol",
                "V_t1 = clip(V_t + kv*(act - V_t), 0.0, 1.0)",
                "realized-vol EMA — the VaR-style risk meter",
            ),
            _eq(
                "retention",
                "R_t1 = clip(r0 + kr*(V_t - v_target), 0.0, 0.95)",
                "procyclical keying: absolute vol up -> retention up (the flaw class)",
            ),
            _eq(
                "escrow",
                "E_t1 = clip(E_t + inflow*R_t - outflow, 0.0, 1000000.0)",
                "integral accumulator — retention history is never forgotten",
            ),
        ],
        assumptions=[_asm("anchor moves are the only volatility source", critical=True)],
        constraints=[
            _con("repeated vol spikes ratchet the escrow monotonically", kind="failure_condition"),
        ],
        open_questions=["does any strike cadence leave the escrow standing higher each cycle?"],
        rationale=(
            "Retention keyed to ABSOLUTE realized volatility feeding an "
            "integral escrow: every vol spike raises retention, the escrow "
            "accumulates, and nothing bleeds the accumulation back — the "
            "procyclical ratchet class."
        ),
    )
    return CalibrationFixture(
        fixture_id="fixture-vol-keyed-retention-ratchet",
        title="Vol-keyed retention ratchet",
        referent=(
            "Procyclical VaR-style margin/buffer class (BIS/CCP "
            "procyclicality literature; the lab's own rejected r16 predecessor)"
        ),
        consensus=ConsensusClass.KNOWN_FLAWED,
        ground_truth=(
            "FACT: margin/buffer rules keyed to absolute realized volatility "
            "are the documented procyclicality class — protection demand rises "
            "with stress and amplifies it (BIS/CCP margin literature); the "
            "lab's r16 predecessor of this exact shape was rejected after a "
            "measured resonance ratchet (285 -> 6479, linear-unbounded in N). "
            "INFERENCE: the §20 resonance choreography must surface the "
            "standing accumulation above the canonical flaw threshold."
        ),
        model=model,
        expectations=[
            Expectation(
                kind=CheckKind.SCENARIOS_CLEAN,
                rationale=(
                    "FACT: the flaw is ECONOMIC, not numerical — the model "
                    "runs clean while the ratchet accumulates"
                ),
            ),
            Expectation(
                kind=CheckKind.NO_DEGENERATE,
                rationale="INFERENCE: all three states exercise dynamics in every scenario",
            ),
            Expectation(
                kind=CheckKind.MIN_PATTERN_EDGE,
                pattern=AttackPattern.RESONANCE,
                threshold=FLAW_EDGE_THRESHOLD,
                rationale=(
                    "FACT: the lab already rejected this class for a measured "
                    "resonance ratchet — a battery that cannot re-detect it "
                    "under a known answer has a blind spot"
                ),
            ),
        ],
    )



def reflexive_mint_burn() -> CalibrationFixture:
    """Known-flawed positive control: Terra/Luna-style seigniorage —
    redemptions mint the volatile asset INVERSELY to its price. A shock
    through the arbitrage band starts a self-fueling spiral; calm markets
    stay quiescent (the flaw is regime-dependent, like the referent's)."""
    model = MathModel(
        candidate_id="fixture-reflexive-mint-burn",
        variables=[
            *_ANCHOR_INPUTS,
            _var("supply", "S_t", VariableRole.STATE, "volatile-asset supply"),
            _var("supply_next", "S_t1", VariableRole.STATE, "next supply"),
            _var("price", "P_t", VariableRole.STATE, "volatile-asset price"),
            _var("price_next", "P_t1", VariableRole.STATE, "next price"),
            _var("liability", "L_t", VariableRole.STATE, "outstanding redeemable liability"),
            _var("liability_next", "L_t1", VariableRole.STATE, "next liability"),
            _var("stress", "stress", VariableRole.AUXILIARY, "fractional down-move this step"),
            _var("market_coupling", "track", VariableRole.AUXILIARY, "signed market co-movement"),
            _var("depeg", "depeg", VariableRole.AUXILIARY, "depth below the arbitrage band"),
            _var("redeemed", "redeem", VariableRole.AUXILIARY,
                 "liability value redeemed this step"),
            _var("minted", "mint", VariableRole.AUXILIARY, "units minted by redemptions"),
        ],
        parameters=[
            _par("par", "par", "redemption par value", 1000.0, 1.0, 1.0e6),
            _par("band", "band", "arbitrage band around par (no redemptions inside)",
                 0.08, 0.0, 0.5),
            _par("impact", "impact", "price impact of anchor down-moves", 0.5, 0.0, 10.0),
            _par("ptrack", "ptrack", "market co-movement coupling", 0.5, 0.0, 2.0),
            _par("arb", "arb", "arbitrage restoring force when depegged", 0.1, 0.0, 2.0),
            _par("redeem_k", "redeem_k", "flight rate: liability share fleeing per unit depeg",
                 1.0, 0.01, 1.0),
            _par("mint_scale", "mint_scale", "asset units minted per unit of par value",
                 8.0, 0.1, 100.0),
            _par("dilution", "dilution", "price dilution per unit minted", 1.0, 0.01, 10.0),
        ],
        equations=[
            _eq("stress", "stress = max(0.0 - dX_t, 0.0) / max(X_t, 1.0)", "down-move fraction"),
            _eq(
                "market_coupling",
                "track = ptrack * dX_t / max(X_t, 1.0)",
                "the volatile asset co-moves with the market",
            ),
            _eq(
                "depeg",
                "depeg = max(1.0 - band - P_t / par, 0.0)",
                "zero inside the arbitrage band; depth below it otherwise",
            ),
            _eq(
                "redeemed",
                "redeem = clip(redeem_k * depeg * L_t, 0.0, 1000000.0)",
                "flight: a depeg-proportional share of the outstanding liability "
                "runs for the exit each step",
            ),
            _eq(
                "minted",
                "mint = clip(redeem * mint_scale * par / max(P_t, 0.001), 0.0, 1000000000.0)",
                "reflexive core: redemptions mint MORE units as the price falls "
                "(the referent's exact mint rule: units = value / price)",
            ),
            _eq(
                "supply",
                "S_t1 = clip(S_t + mint, 1.0, 1000000000000.0)",
                "supply absorbs redemptions",
            ),
            _eq(
                "liability",
                "L_t1 = clip(L_t - redeem, 0.0, 1000000000000.0)",
                "redeemed liability burns down",
            ),
            _eq(
                "price",
                "P_t1 = clip(P_t * (1.0 + track + arb*depeg*1000.0/max(S_t, 1.0) "
                "- impact*stress - dilution*mint/max(S_t, 1.0)), 0.001, 100000.0)",
                "arbitrage restores small depegs, but the restoring force is "
                "spread over the whole supply — once supply hyperinflates the "
                "bid per unit is nothing and dilution overwhelms it (the "
                "death-spiral feedback)",
            ),
        ],
        assumptions=[
            _asm("redemption demand appears whenever price is below the band", critical=True),
        ],
        constraints=[
            _con(
                "below the band, minting scales with 1/price — self-fueling spiral",
                kind="failure_condition",
            ),
        ],
        open_questions=["how deep a shock can the arbitrage force absorb before the spiral wins?"],
        rationale=(
            "Algorithmic-stablecoin seigniorage: redemptions mint the volatile "
            "asset inversely to its price. Small depegs self-correct through "
            "arbitrage; a shock through the band makes dilution overwhelm the "
            "restoring force and the loop runs away."
        ),
    )

    return CalibrationFixture(
        fixture_id="fixture-reflexive-mint-burn",
        title="Reflexive mint-burn seigniorage",
        referent="Terra/Luna-style algorithmic stablecoin (May 2022 collapse)",
        consensus=ConsensusClass.KNOWN_FLAWED,
        ground_truth=(
            "FACT: Terra/Luna redemptions minted LUNA inversely to its price; "
            "a confidence shock through the peg started a self-fueling spiral — "
            "supply ~350M to ~6.5T in days, price ~$80 to ~$0.0001 (May 2022), "
            "after ~18 months of holding the peg in calm markets. INFERENCE: in "
            "this encoding the §15 bank-run shock knocks the price through the "
            "arbitrage band and the same feedback runs away (supply >= 5x, "
            "price <= 0.5x) while the base scenario stays quiescent."
        ),
        model=model,
        expectations=[
            Expectation(
                kind=CheckKind.SCENARIOS_CLEAN,
                rationale=(
                    "INFERENCE: the flaw is ECONOMIC, not numerical — the "
                    "interpreter runs clean while the economy dies (a clean "
                    "run is not a healthy mechanism)"
                ),
            ),
            Expectation(
                kind=CheckKind.STATE_RATIO,
                scenario=ScenarioKind.BASE,
                symbol="S_t",
                direction=RatioDirection.BELOW,
                threshold=2.0,
                rationale=(
                    "FACT: the referent held its peg ~18 months in calm "
                    "markets — the flaw is regime-dependent, so calm scenarios "
                    "must NOT spiral (supply < 2x)"
                ),
            ),
            Expectation(
                kind=CheckKind.STATE_RATIO,
                scenario=ScenarioKind.BANK_RUN,
                symbol="S_t",
                direction=RatioDirection.ABOVE,
                threshold=5.0,
                rationale=(
                    "FACT: runaway supply expansion is the documented collapse "
                    "signature — the §15 battery must show it under a bank-run "
                    "shock (>= 5x; the referent expanded ~4 orders of magnitude)"
                ),
            ),
            Expectation(
                kind=CheckKind.STATE_RATIO,
                scenario=ScenarioKind.BANK_RUN,
                symbol="P_t",
                direction=RatioDirection.BELOW,
                threshold=0.5,
                rationale=(
                    "FACT: the referent's price collapsed through every floor "
                    "— under a bank-run shock the battery must show the price "
                    "broken (<= 0.5x), not a dip-and-recover"
                ),
            ),
        ],
    )


def all_fixtures() -> list[CalibrationFixture]:
    """Fresh instances of every calibration fixture (order is stable)."""
    return [
        pid_anchor_controller(),
        utilization_kink_rate(),
        vol_keyed_retention_ratchet(),
        reflexive_mint_burn(),
    ]

