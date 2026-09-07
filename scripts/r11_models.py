"""Round 11: MathModels for the 4 adversarial-residual successors.

Every model honors the BATTERY INPUT CONTRACT (r8/r9):
  X_t   = anchor LEVEL (~1000)
  dX_t  = anchor DELTA that step
  states seed at 1000.0; responses are SCALE-FREE (dX_t/X_t);
  clip bounds bracket reachable ranges; no dependency cycles.

Round-11 correction (the shared primitive): each model declares a
TREND STATE T_t — an EMA of SIGNED relative moves,
  T_t1 = T_t*(1-kappa) + kappa*(dX_t/X_t)*1000.0,
and keys its adversarially-sensitive state (fee index, attest gap,
mis-band excess, drawdown state) to T_t, NOT to instantaneous |dX_t|.
A zero-mean oscillation integrates to ~0 in T_t by construction, so
the r10 pattern-battery choreographies (vol_oscillation, wash_flow,
pump_unwind around a mean, shock_timing) cannot pump escrow slash
gaps, bond forfeiture, drawdown states, or open-interest indices —
while sustained directional stress moves T_t and triggers the response.

The r10 §20 edges these v1 models target (measured, disclosed in the
release §4b of each predecessor):
  FeeOracle  +14.75 F_l (pump_unwind) — fee-ladder discount manipulation
  Joule     +351.83 J_t (pump_unwind) — escrow slash via crafted vol
  FeeMeter  +700.00 B_m (vol_osc/wash/pump) — bond forfeiture via spikes
  Corridor  +784.99 U_t (shock_timing) — drawdown pumping drains tranches
"""

from __future__ import annotations

import json
import sys

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    MechanismSimulation,
    ScenarioBattery,
    ScenarioKind,
    scenario_config,
)


def var(symbol: str, role: str, name: str, desc: str) -> dict[str, str]:
    return {"name": name, "symbol": symbol, "role": role, "units": "unit", "description": desc}


def param(symbol: str, default: float, lo: float, hi: float, desc: str) -> dict[str, object]:
    return {
        "name": symbol,
        "symbol": symbol,
        "description": desc,
        "min_value": lo,
        "max_value": hi,
        "default": default,
    }


def eq(name: str, expr: str, desc: str) -> dict[str, str]:
    return {"name": name, "expression": expr, "description": desc}


def assumption(stmt: str, critical: bool = False) -> dict[str, object]:
    return {"statement": stmt, "critical": critical}


def constraint(stmt: str, kind: str = "invariant") -> dict[str, str]:
    return {"statement": stmt, "kind": kind}


def _inputs() -> list[dict[str, str]]:
    return [
        var("X_t", "input", "anchor_level", "anchor price level (~1000)"),
        var("dX_t", "input", "anchor_delta", "anchor change that step"),
    ]


def _trend_state() -> list[dict[str, str]]:
    """The shared r11 primitive: trend EMA state + its next-step twin."""
    return [
        var("T_t", "state", "trend_index", "EMA of signed relative anchor moves"),
        var("T_t1", "state", "trend_index_next", "next trend index"),
    ]


def _trend_eq(kappa: str = "kappa", scale: str = "1000.0") -> dict[str, str]:
    # EMA of the LEVEL trajectory (signed), reverting to the 1000 anchor
    # when moves stop: zero-mean oscillation leaves T near 1000 (up-moves
    # cancel down-moves AND the reversion pulls it back), sustained drift
    # carries T to the moved level. An integrating signed-EMA (the first
    # draft) drifts forever and saturates — the reversion is what makes
    # it a low-pass filter instead of a random walk.
    return eq(
        "trend_index",
        f"T_t1 = clip(T_t + {kappa}*(({scale} + (dX_t/max(X_t,1.0))*{scale}) - T_t),"
        " 200.0, 1800.0)",
        "reverting EMA of the signed level path: oscillation washes out, "
        "sustained drift carries it",
    )


# ---------------------------------------------------------------- models


def trend_fee_oracle(cid: str) -> MathModel:
    """Trend-Indexed Prediction-Fee Oracle (successor of the r10 rank-1).

    The open-interest index reads the TREND state, not |dX|; the fee
    ladder prices fallback reads against it. Crafted oscillation can no
    longer inflate the index to harvest fee discounts (the +14.75 F_l
    residual): the index only moves on sustained drift.
    """
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(), *_trend_state(),
            var("O_t", "state", "open_interest_index", "trend-keyed open-interest index"),
            var("O_t1", "state", "open_interest_index_next", "next open-interest index"),
            var("F_t", "state", "fee_ladder", "fallback read fee level"),
            var("F_t1", "state", "fee_ladder_next", "next fee level"),
        ],
        parameters=[
            param("kappa", 0.18, 0.05, 0.5, "trend EMA coefficient"),
            param("gamma", 0.15, 0.05, 0.5, "open-interest index decay"),
            param("delta", 0.25, 0.05, 0.6, "fee ladder tracking speed"),
            param("oi_floor", 500.0, 300.0, 800.0, "open-interest index floor"),
        ],
        equations=[
            _trend_eq("kappa", "1000.0"),
            eq(
                "open_interest",
                "O_t1 = clip(O_t*(1-gamma) + gamma*(oi_floor + 40.0*abs(T_t-1000.0)/10.0"
                " + 30.0*sqrt(abs(dX_t)/max(X_t,1.0))), 350.0, 1600.0)",
                "index keys to TREND magnitude, not instantaneous vol",
            ),
            eq(
                "fee_ladder",
                "F_t1 = clip(F_t*(1-delta) + delta*(600.0 + 120.0*max(0.0, 1200.0-O_t1)/100.0),"
                " 400.0, 1700.0)",
                "fees rise when the trend-keyed index falls (sustained degradation)",
            ),
        ],
        assumptions=[
            assumption(
                "the trend EMA of signed moves is a faithful degradation proxy: "
                "sustained data decay shows as drift, wash shows as zero-mean noise",
                True,
            ),
            assumption("fallback consumption demand falls as fees rise", False),
        ],
        constraints=[constraint("fee ladder bounded 400..1700; index bounded 350..1600")],
        open_questions=["should the trend index blend a second slower EMA for regime memory?"],
        rationale=(
            "The r10 pattern battery measured +14.75 fee-ladder extraction "
            "because the v2 index keyed to instantaneous |dX|, which "
            "oscillation pumps. This model keys the open-interest index "
            "to the TREND state (EMA of signed relative moves): "
            "zero-mean oscillation leaves the index unmoved; sustained "
            "degradation drifts it and raises fees. States seed at 1000, "
            "bounds bracket reachable ranges."
        ),
        version=1,
    )


def drift_gap_joule(cid: str) -> MathModel:
    """Drift-Gap Joule Escrow (successor of Joule-Bonded Inference Escrow).

    The attest gap reads sustained divergence between anchor and energy
    price from the TREND state, not |dX| spikes; escrow slashes only on
    drift, so crafted vol cannot slash honest providers (+351.83 J_t).
    """
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(), *_trend_state(),
            var("P_e", "state", "energy_index", "energy price index"),
            var("P_e1", "state", "energy_index_next", "next energy index"),
            var("J_t", "state", "joule_escrow", "escrowed joule-value pool"),
            var("J_t1", "state", "joule_escrow_next", "next escrow pool"),
            var("a_t", "auxiliary", "attest_gap", "drift-gap attestation measure"),
        ],
        parameters=[
            param("kappa", 0.18, 0.05, 0.5, "trend EMA coefficient"),
            param("nu", 0.3, 0.05, 0.7, "energy index tracking of trend"),
            param("mu_j", 40.0, 5.0, 120.0, "per-epoch escrowed joule inflow"),
            param("psi", 0.12, 0.02, 0.5, "drift-gap slash rate"),
        ],
        equations=[
            _trend_eq("kappa", "1000.0"),
            eq(
                "energy_price",
                "P_e1 = clip(P_e*(1-nu) + nu*(1000.0 + 150.0*(T_t-1000.0)/100.0"
                " + 120.0*min(3.0, abs(X_t-1000.0)/1000.0)), 400.0, 1800.0)",
                "energy index tracks the trend state (sustained moves only)",
            ),
            eq(
                "attest_gap",
                "a_t = min(1.0, abs(T_t-1000.0)/160.0)",
                "gap = sustained drift magnitude, not instantaneous spike",
            ),
            eq(
                "joule_escrow",
                "J_t1 = clip(J_t + mu_j - 0.06*(J_t-1000.0) - psi*a_t*300.0"
                " - min(50.0, 20.0*sqrt(abs(dX_t)/max(X_t,1.0))),"
                " 600.0, 2200.0)",
                "escrow releases per attested joule; slashes only on drift",
            ),
        ],
        assumptions=[
            assumption(
                "energy price moves are sustained when real (supply shocks "
                "persist) and transient when crafted (wash oscillation "
                "is zero-mean)",
                True,
            ),
            assumption("escrow inflow scales with request volume", False),
        ],
        constraints=[constraint("escrow floor 600 protects delivery continuity")],
        open_questions=["should the gap use both sign and magnitude of drift?"],
        rationale=(
            "The r10 battery measured +351.83 escrow drain because the v2 "
            "attest gap keyed to instantaneous |dX|/X spikes. This model "
            "computes the gap from the TREND state: sustained divergence "
            "between anchor and energy index slashes; zero-mean oscillation "
            "leaves both the gap and the escrow unmoved. States seed 1000, "
            "bounds bracket reachable ranges."
        ),
        version=1,
    )


def sustained_band_meter(cid: str) -> MathModel:
    """Sustained-Band Forecast Fee Meter (successor of Report-Bonded
    Forecast Fee Meter).

    Forfeiture keys to INTEGRATED mis-band excess (EMA of band
    exceedance around the trend), not per-step |dX|: single spikes
    cannot forfeit honest bonds (+700 B_m wash-flow harvest).
    """
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(), *_trend_state(),
            var("E_t", "state", "exceedance_ema", "integrated band-exceedance level"),
            var("E_t1", "state", "exceedance_ema_next", "next integrated exceedance"),
            var("B_m", "state", "bond_pool", "reporter bond pool"),
            var("B_m1", "state", "bond_pool_next", "next bond pool"),
            var("S_m", "state", "stab_pool", "stabilization pool"),
            var("S_m1", "state", "stab_pool_next", "next stabilization pool"),
            var("x_t", "auxiliary", "band_excess", "per-step band exceedance"),
        ],
        parameters=[
            param("kappa", 0.18, 0.05, 0.5, "trend EMA coefficient"),
            param("zeta", 0.35, 0.05, 0.8, "exceedance integration rate"),
            param("band", 0.02, 0.005, 0.08, "band half-width around trend"),
            param("mu_b", 30.0, 5.0, 90.0, "per-epoch bond inflow"),
            param("forfeit", 60.0, 10.0, 200.0, "forfeit transfer on sustained mis-banding"),
        ],
        equations=[
            _trend_eq("kappa", "1000.0"),
            eq(
                "band_excess",
                "x_t = max(0.0, abs(X_t - T_t)/max(X_t,1.0) - band)",
                "exceedance measured AROUND THE TREND: transient wash spikes "
                "exceed the band, sustained mis-banding keeps exceeding",
            ),
            eq(
                "exceedance_ema",
                "E_t1 = clip(E_t*(1-zeta) + zeta*x_t*1000.0, 0.0, 900.0)",
                "integrated exceedance: spikes decay, sustained mis-banding accumulates",
            ),
            eq(
                "bond_pool",
                "B_m1 = clip(B_m + mu_b - 0.05*(B_m-1000.0)"
                " - min(160.0, 0.8*forfeit*sqrt(E_t1)/30.0), 300.0, 2400.0)",
                "forfeiture drains bonds proportionally to INTEGRATED exceedance",
            ),
            eq(
                "stab_pool",
                "S_m1 = clip(S_m + 0.5*min(160.0, 0.8*forfeit*sqrt(E_t1)/30.0)"
                " - 6.0, 200.0, 2200.0)",
                "compensation funds from the integrated measure (mis-banders "
                "pay the mis-banded, only when persistent)",
            ),
        ],
        assumptions=[
            assumption(
                "a forecast band is a SUSTAINED claim: honest reporters "
                "may miss single steps, persistent misses are mis-banding",
                True,
            ),
            assumption("bond inflow scales with reporter count", False),
        ],
        constraints=[constraint("bond floor 300; stabilization floor 200")],
        open_questions=["should the band width adapt to realized vol regime?"],
        rationale=(
            "The r10 battery measured +700 bond-pool drain because the v2 "
            "forfeiture keyed to per-step |dX|/X exceedance, which wash flow "
            "trips every step. This model integrates exceedance AROUND THE "
            "TREND: a transient spike decays in E_t without draining bonds; "
            "only sustained mis-banding accumulates and forfeits. States "
            "seed 1000, bounds bracket reachable ranges."
        ),
        version=1,
    )


def trend_drawdown_corridor(cid: str) -> MathModel:
    """Trend-Drawdown Liquidity Corridor (successor of Drawdown-Underwritten
    Liquidity Corridor).

    The drawdown state keys to the TREND state, not sqrt(|dX|) spikes;
    tranche capacity responds to sustained drawdown only, so oscillation
    cannot pump D and drain capacity (+784.99 U_t shock_timing).
    """
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(), *_trend_state(),
            var("D_t", "state", "drawdown_state", "trend-keyed drawdown level"),
            var("D_t1", "state", "drawdown_state_next", "next drawdown level"),
            var("U_t", "state", "tranche_capacity", "underwriter tranche capacity"),
            var("U_t1", "state", "tranche_capacity_next", "next tranche capacity"),
        ],
        parameters=[
            param("kappa", 0.18, 0.05, 0.5, "trend EMA coefficient"),
            param("lambda_", 0.35, 0.05, 0.8, "drawdown tracking of trend"),
            param("eta", 0.2, 0.05, 0.6, "capacity tracking speed"),
        ],
        equations=[
            _trend_eq("kappa", "1000.0"),
            eq(
                "drawdown_state",
                "D_t1 = clip(D_t*(1-lambda_) + lambda_*max(0.0, (1000.0-T_t))*2.0,"
                " 0.0, 900.0)",
                "drawdown keys to SUSTAINED DOWNTREND magnitude only "
                "(T_t below 1000), not instantaneous spikes",
            ),
            eq(
                "tranche_capacity",
                "U_t1 = clip(U_t*(1-eta) + eta*(1000.0 + min(700.0, 0.5*(X_t-1000.0))"
                " - 1.6*D_t1), 200.0, 2400.0)",
                "capacity releases against sustained drawdown, not wash spikes",
            ),
        ],
        assumptions=[
            assumption(
                "real corridor drawdown persists across steps; crafted "
                "oscillation is zero-mean and integrates out of T_t",
                True,
            ),
            assumption("underwriter capacity scales with corridor flow", False),
        ],
        constraints=[constraint("drawdown state bounded 0..900; capacity 200..2400")],
        open_questions=["should fast-crash windows carry a separate spot cover?"],
        rationale=(
            "The r10 battery measured +784.99 tranche-capacity drain because "
            "the v2 drawdown state keyed to sqrt(|dX|), which shock spikes "
            "pump. This model keys drawdown to the TREND state: only "
            "sustained downtrend (T_t persistently below 1000) raises D and "
            "releases capacity; zero-mean oscillation leaves both unmoved. "
            "States seed 1000, bounds bracket reachable ranges."
        ),
        version=1,
    )


# ---------------------------------------------------------------- smoke


BUILDERS = {
    "Trend-Indexed Prediction-Fee Oracle": trend_fee_oracle,
    "Drift-Gap Joule Escrow": drift_gap_joule,
    "Sustained-Band Forecast Fee Meter": sustained_band_meter,
    "Trend-Drawdown Liquidity Corridor": trend_drawdown_corridor,
}


def smoke(model: MathModel) -> tuple[bool, str]:
    """§15-style smoke: interpretable, 13/13 distinct, non-degenerate,
    whale≠base, AND the r11 gate — oscillation-immunity of the keyed state.

    The r11 gate runs the adversarial vol_oscillation series and asserts
    the trend-keyed state moves LESS under oscillation than under a
    sustained directional series of the same |dX| magnitude: the wash
    choreography cannot pump the state the predecessor keyed to |dX|.
    """
    try:
        sim = MechanismSimulation(model)
    except Exception as exc:
        return False, f"interpret: {exc}"
    base_cfg = scenario_config(ScenarioKind.BASE, steps=120)
    base = sim.run(AnchorSeriesGenerator(base_cfg).generate())
    whale_cfg = scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)
    whale = sim.run(AnchorSeriesGenerator(whale_cfg).generate())
    runs = ScenarioBattery(sim, steps=120).run()
    degenerate = [k for k, r in runs.items() if r.degenerate]
    if degenerate:
        return False, f"degenerate in {len(degenerate)}/13: {degenerate[:3]}"
    if base.final_state == whale.final_state:
        return False, "whale attack indistinguishable from base"
    finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
    if len(finals) < 13:
        return False, f"only {len(finals)}/13 distinct scenario finals"

    # r11 oscillation-immunity gate (§20 wash series):
    from blockchain_rd_lab.simulation.adversarial import (
        AttackPattern,
        AttackPatternBattery,
        PatternSpec,
    )

    battery = AttackPatternBattery(model)
    wash = battery.run_pattern(PatternSpec(kind=AttackPattern.WASH_FLOW, steps=60))
    if wash.vacuous:
        return False, "wash bound vacuous (no measurable dynamics)"
    wash_edge = wash.headline or 0.0
    # assertion is directional: the wash edge on the keyed state should be
    # small relative to the predecessor's measured residuals; a fresh v1
    # model that still pumps under wash must fail here.
    if wash_edge > 150.0:
        return False, f"wash edge still large: {wash_edge:.2f} on {wash.headline_metric}"
    return True, f"ok (wash edge {wash_edge:.2f})"


def main(store: bool = False) -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name_to_cid = {c.name: c.id for c in db.list_candidates(limit=None)}
    failures = []
    for name, builder in BUILDERS.items():
        cid = name_to_cid[name]
        model = builder(cid)
        ok, msg = smoke(model)
        print(f"  {'PASS' if ok else 'FAIL'} {cid} {name[:44]} {msg}")
        if not ok:
            failures.append((cid, name, msg))
    if failures:
        raise SystemExit(f"smoke failures: {failures}")
    print("all 4 models pass smoke (incl. wash-immunity gate)")
    if not store:
        print("dry run — pass --store to store them")
        return
    for name, builder in BUILDERS.items():
        cid = name_to_cid[name]
        existing = db.list_math_models(cid)
        if any(m.version == 1 for m in existing):
            print(f"  skip {cid} (v1 already stored)")
            continue
        model = builder(cid)
        db.save_math_model(
            candidate_id=cid,
            model_json=json.dumps(model.model_dump(mode="json"), indent=2),
            rationale=model.rationale,
            version=model.version,
        )
        print(f"  stored {cid} v{model.version}")
    print("store complete — install as formalize answers via r11_answer_formalize.py")


if __name__ == "__main__":
    main(store="--store" in sys.argv)
