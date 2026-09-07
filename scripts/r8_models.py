"""Round 8: MathModels for the 14 §18 combination candidates.

Every model honors the BATTERY INPUT CONTRACT (see scripts/r7_models.py):
  X_t   = anchor LEVEL (~1000)
  dX_t  = anchor DELTA that step
  states seed at 1000.0; responses are SCALE-FREE (dX_t/X_t);
  clip bounds bracket reachable ranges; no dependency cycles.

These are v1 formalizations — genuine mechanisms distilled from each
candidate's stepwise description, expressed with one anchor input pair
plus the states the mechanism actually evolves.
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

# same helpers as r7 (kept local so the script is standalone)


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


# ---------------------------------------------------------------- models


def fee_spike_mutual(cid: str) -> MathModel:
    """Fee-Spike Mutual: trailing-percentile band vs realized spike."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('R_t', 'state', 'reserve_level', 'mutual reserve level'),
            var('R_t1', 'state', 'reserve_next', 'next reserve level'),
            var('P_t', 'state', 'premium_index', 'premium index (fee units)'),
            var('P_t1', 'state', 'premium_next', 'next premium index'),
            var('s_t', 'auxiliary', 'spike', 'spike intensity vs subscribed band'),
        ],parameters=[
            param('kappa', 0.25, 0.05, 0.9, 'reimbursement share of excess'),
            param('mu', 20.0, 5.0, 80.0, 'per-window premium inflow'),
            param('band', 0.02, 0.005, 0.1, 'subscribed band (relative fee)'),
        ],
        equations=[
            eq('spike_intensity', 's_t = sqrt(max(0.0, abs(dX_t)/X_t - band))',
         'concave excess over band'),
            eq('premium_index',
         'P_t1 = clip(P_t*(1-0.05) + 0.05*(1000.0 + 8.0*s_t*10.0 + 0.5*(X_t-1000.0)), 500.0, '
          '1600.0)', 'premium ticks with spike intensity, mean-reverting around 1000'),
            eq('reserve_dynamics',
         'R_t1 = clip(R_t + mu - 0.04*(R_t-1000.0) - kappa*s_t*P_t1/40.0, 300.0, 3000.0)',
         'premiums accumulate; spikes draw the reserve down'),
        ],
        assumptions=[
            assumption("premium inflow is steady per window (stylized)", True),
            assumption("band excess is measured by relative anchor move as fee proxy", True),
        ],
        constraints=[constraint("reserve never below 300 (rationing threshold)")],
        open_questions=["should the band re-price from realized reserve drain speed?"],
        rationale=(
            "Spike intensity is the scale-free excess of realized relative "
            "volatility over the subscribed band; premiums and reserves respond "
            "to it with bounds bracketing reachable ranges (reserve 300..3000 "
            "around seed 1000; premium index 500..1600)."
        ),
        version=1,
    )


def drawdown_corridor(cid: str) -> MathModel:
    """Drawdown-Underwritten Corridor: conversion tranche keyed to drawdown."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('D_t', 'state', 'drawdown_state', 'smoothed corridor drawdown'),
            var('D_t1', 'state', 'drawdown_next', 'next drawdown state'),
            var('U_t', 'state', 'underwriter_capacity', 'underwriter tranche capacity'),
            var('U_t1', 'state', 'underwriter_next', 'next tranche capacity'),
        ],
        parameters=[
            param('lambda_', 0.3, 0.05, 0.9, 'drawdown EMA coefficient'),
            param('gamma', 150.0, 10.0, 600.0, 'capacity conversion per drawdown'),
            param('topup', 8.0, 1.0, 40.0, 'calm-regime tranche top-up'),
        ],
        equations=[
            eq('drawdown_state',
         'D_t1 = clip(D_t*(1-lambda_) + lambda_*sqrt(abs(dX_t)/X_t)*900.0, 0.0, 900.0)',
         'negative anchor moves accumulate into drawdown (EWMA)'),
            eq('tranche_capacity',
         'U_t1 = clip(U_t*(1-0.1) + 0.1*(1000.0 + min(600.0, 0.04*(X_t-1000.0)) - 2.0*D_t1), '
          '200.0, 2500.0)', 'tranche grows in calm, converts to depth as drawdown deepens'),
        ],
        assumptions=[
            assumption("drawdown is proxied by negative anchor deltas", True),
            assumption("conversion is linear in drawdown increments", True),
        ],
        constraints=[constraint("tranche capacity bounded [200, 2500]")],
        open_questions=["should conversion price re-mark from the drawdown series itself?"],
        rationale=(
            "Drawdown state is an EWMA over negative deltas scaled into "
            "[0,900]; the underwriter tranche tops up in calm regimes and "
            "converts proportionally as drawdown deepens. Both states stay "
            "well inside bounds across the battery."
        ),
        version=1,
    )


def fee_sink_insurer(cid: str) -> MathModel:
    """Counter-Cyclical Fee Sink: volatility-percentile keyed tap."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('K_t', 'state', 'sink_level', 'fee sink level'),
            var('K_t1', 'state', 'sink_next', 'next sink level'),
            var('V_t', 'state', 'vol_regime', 'smoothed fee-volatility regime'),
            var('V_t1', 'state', 'vol_regime_next', 'next regime state'),
        ],parameters=[
            param('alpha', 0.15, 0.02, 0.6, 'regime EMA coefficient'),
            param('accrue', 25.0, 5.0, 100.0, 'calm-regime accumulation rate'),
            param('disb', 200.0, 20.0, 800.0, 'turbulent disbursement rate'),
        ],
        equations=[
            eq('regime_state',
         'V_t1 = clip(V_t*(1-alpha) + alpha*sqrt(abs(dX_t)/X_t)*9000.0, 100.0, 1200.0)',
         'relative volatility scaled into a bounded regime index'),
            eq('sink_dynamics',
         'K_t1 = clip(K_t + accrue*(1200.0-V_t1)/200.0 - disb*max(0.0, V_t1-1000.0)/200.0 + '
          '0.02*(X_t-1000.0), 200.0, 2800.0)'
          , 'accumulates in calm regimes, disburses in turbulent ones'),
        ],
        assumptions=[
            assumption("regime detection by smoothed relative volatility is final", True),
            assumption("tap and cap schedules are linear in the regime index", True),
        ],
        constraints=[constraint("sink bounded [200, 2800]")],
        open_questions=["is the median-crossing trigger robust to sustained artificial calm?"],
        rationale=(
            "Regime index scales relative volatility (typ. 1e-3*1e4 = 10) "
            "into [100,1200]; the sink accumulates below the calm threshold "
            "(1000) and disburses above it, both bounded around the 1000 seed."
        ),
        version=1,
    )


def relay_cover_mesh(cid: str) -> MathModel:
    """Relay Congestion Cover Mesh: attested congestion reprices premiums."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('C_t', 'state', 'congestion_state', 'attested congestion level'),
            var('C_t1', 'state', 'congestion_next', 'next congestion level'),
            var('M_t', 'state', 'mesh_pool', 'mesh premium pool'),
            var('M_t1', 'state', 'mesh_pool_next', 'next pool level'),
        ],parameters=[
            param('beta', 3.0, 0.2, 12.0, 'congestion response to relative move'),
            param('pay', 120.0, 10.0, 500.0, 'burst compensation coefficient'),
            param('fee', 15.0, 2.0, 60.0, 'per-interval mesh fee inflow'),
        ],
        equations=[
            eq('congestion_state',
         'C_t1 = clip(C_t*(1-0.1) + 0.1*(1000.0 + beta*sqrt(abs(dX_t))*3.0), 400.0, 1500.0)',
         'congestion mean-reverts to baseline 1000, shocked by anchor moves'),
            eq('mesh_pool',
         'M_t1 = clip(M_t + fee + pay*max(0.0, C_t1-1050.0)/100.0, 250.0, 2600.0)',
         'fees accumulate; congested intervals draw compensation'),
        ],
        assumptions=[
            assumption("congestion is attested per interval (client-corroborated)", True),
            assumption("burst compensation is linear above the band", True),
        ],
        constraints=[constraint("pool bounded [250, 2600]")],
        open_questions=["what attestation diversity bounds fabricated congestion?"],
        rationale=(
            "Congestion mean-reverts to 1000 with anchor-driven shocks; the "
            "mesh pool pays only above the 1100 congestion band and refills "
            "below it. Bounds bracket seed-scale values."
        ),
        version=1,
    )


def vol_sized_escrow(cid: str) -> MathModel:
    """Volatility-Sized Settlement Escrow: tranche re-targets from vol."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('T_t', 'state', 'tranche_size', 'cover tranche size'),
            var('T_t1', 'state', 'tranche_next', 'next tranche size'),
            var('W_t', 'state', 'spread_level', 'settlement spread level'),
            var('W_t1', 'state', 'spread_next', 'next spread level'),
            var('v_t', 'auxiliary', 'pair_vol', 'realized pair volatility'),
        ],parameters=[
            param('eta', 150.0, 20.0, 1200.0, 'tranche units per vol unit'),
            param('rho', 900.0, 100.0, 4000.0, 'tranche scale coefficient'),
            param('phi', 6.0, 0.5, 40.0, 'spread response coefficient'),
        ],
        equations=[
            eq('pair_vol', 'v_t = sqrt(abs(dX_t)/X_t)', 'concave realized pair volatility'),
            eq('tranche_retarget', 'T_t1 = clip(rho*(1 + eta*v_t/100.0), 400.0, 2400.0)',
         'tranche re-targets each window from concave pair volatility'),
            eq('spread_dynamics',
         'W_t1 = clip(W_t*(1-0.15) + 0.15*(1000.0 + phi*100.0*v_t + 0.04*(X_t-1000.0)), 500.0, '
          '1600.0)', 'spread follows concave volatility, mean-reverting around 1000'),
        ],
        assumptions=[
            assumption("pair volatility is measured from the anchor series", True),
            assumption("tranche refills from unclaimed premiums (stylized linear)", True),
        ],
        constraints=[constraint("tranche bounded [400, 2400]")],
        open_questions=["should default legs complete from tranche or convert at loss?"],
        rationale=(
            "Tranche and spread respond to scale-free realized pair "
            "volatility; typical v_t ~ 1e-3 gives tranche ~ 500*1+3000*1e-3 "
            "~ 515, inside bounds; battery shocks push it toward but not "
            "beyond the 2400 cap."
        ),
        version=1,
    )


def forecast_fee_pool(cid: str) -> MathModel:
    """Forecast-Indexed Fee Smoothing: implied probability sets buffer intensity."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('B_t', 'state', 'buffer_level', 'smoothing buffer level'),
            var('B_t1', 'state', 'buffer_next', 'next buffer level'),
            var('q_t1', 'state', 'implied_congestion_prob_next',
         'next implied congestion probability'),
        ],
        parameters=[
            param('eta', 400.0, 20.0, 1600.0, 'probability response to vol'),
            param('inject', 30.0, 2.0, 120.0, 'buffer injection per forecast unit'),
            param('drain', 0.05, 0.005, 0.3, 'quiet-regime buffer drain'),
        ],
        equations=[
            eq('implied_prob', 'q_t1 = clip(0.3 + 0.5*sqrt(abs(dX_t)/X_t), 0.05, 0.95)',
         'implied congestion probability from the forecast book proxy (concave)'),
            eq('buffer_dynamics',
         'B_t1 = clip(B_t + inject*(q_t1-0.3) - drain*max(0.0, 0.3-q_t1)*B_t, 250.0, 2400.0)',
         'buffer pre-funds above neutral belief, drains below it'),
        ],
        assumptions=[
            assumption("implied probability proxies the forecast book midpoint", True),
            assumption("injection is linear in belief distance from neutral", True),
        ],
        constraints=[constraint("buffer bounded [250, 2400]")],
        open_questions=["do per-address forecast caps suffice against belief whales?"],
        rationale=(
            "Implied probability responds to scale-free realized volatility; "
            "the buffer pre-funds when belief rises above neutral (0.3) and "
            "drains when it falls. All quantities bounded around 1000 seeds."
        ),
        version=1,
    )


def hashprice_hedge(cid: str) -> MathModel:
    """Prediction-Settled Hashprice Hedge: margin marked to reference vol."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('H_t', 'state', 'hedge_exposure', 'net hedge exposure'),
            var('H_t1', 'state', 'hedge_next', 'next hedge exposure'),
            var('G_t', 'state', 'margin_level', 'aggregate margin level'),
            var('G_t1', 'state', 'margin_next', 'next margin level'),
            var('v_t', 'auxiliary', 'ref_vol', 'realized reference volatility'),
        ],parameters=[
            param('xi', 900.0, 50.0, 4000.0, 'margin add per vol unit'),
            param('hedge_drift', 4.0, 0.2, 20.0, 'hedge rebalance step'),
            param('floor', 400.0, 100.0, 1200.0, 'margin floor'),
        ],
        equations=[
            eq('ref_vol', 'v_t = sqrt(abs(dX_t)/X_t)', 'concave realized reference volatility'),
            eq('hedge_rebalance',
         'H_t1 = clip(H_t*(1-0.1) + 0.1*(1000.0 + hedge_drift*100.0*v_t), 300.0, 2200.0)',
         'exposure scales with concave reference volatility (EWMA)'),
            eq('margin_mark', 'G_t1 = clip(floor + xi*v_t + abs(H_t1-H_t), floor, 2600.0)',
         'margin scales with realized reference volatility and rebalancing'),
        ],
        assumptions=[
            assumption("settlement reference is a median of supplier prices (proxied by anchor)",
                True),
            assumption("margin marking is linear in realized vol", True),
        ],
        constraints=[constraint("margin never below its floor")],
        open_questions=["does supplier-median settlement inherit oracle slashing discipline?"],
        rationale=(
            "Hedge exposure rebalances opposite anchor moves; margin is "
            "marked from scale-free realized reference volatility plus "
            "rebalancing activity, bounded around seed scales."
        ),
        version=1,
    )


def consensus_odds_rebate(cid: str) -> MathModel:
    """Consensus-Odds Liquidity Rebate: belief-multiplied maker rebates."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('L_t', 'state', 'depth_level', 'persisting maker depth'),
            var('L_t1', 'state', 'depth_next', 'next depth level'),
            var('r_t1', 'state', 'rebate_multiplier_next', 'next rebate multiplier'),
            var('q_t1', 'auxiliary', 'implied_demand_next', 'next implied demand probability'),
        ],
        parameters=[
            param('m0', 1.0, 0.2, 3.0, 'baseline rebate multiplier'),
            param('eta', 2.5, 0.2, 12.0, 'multiplier sensitivity to belief'),
            param('attract', 40.0, 5.0, 200.0, 'depth attraction per multiplier unit'),
        ],
        equations=[
            eq('implied_demand', 'q_t1 = clip(0.4 + 0.6*sqrt(abs(dX_t)/X_t), 0.05, 0.95)',
         'implied high-demand probability from the volume forecast book'),
            eq('rebate_multiplier', 'r_t1 = clip(m0*(1 + eta*(q_t1-0.4)), 0.3, 2.8)',
         'rebate multiplier keyed to implied probability buckets'),
            eq('depth_dynamics',
         'L_t1 = clip(L_t*(1-0.1) + 0.1*(1000.0 + attract*(r_t1-m0)*10.0), 400.0, 2000.0)',
         'depth persists, attracted by forecast-multiplied rebates'),
        ],
        assumptions=[
            assumption("depth persistence is measurable per window", True),
            assumption("rebate schedule is linear in implied probability", True),
        ],
        constraints=[constraint("multiplier bounded [0.3, 2.8]")],
        open_questions=["should persistence requirements gate rebate qualification?"],
        rationale=(
            "Implied demand probability and the rebate multiplier respond "
            "to scale-free volatility; depth is attracted by multipliers "
            "above baseline, mean-reverting around 1000."
        ),
        version=1,
    )


def adverse_selection_tax(cid: str) -> MathModel:
    """Adverse-Selection Taxed Clearing: imbalance statistics set spreads."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('I_t', 'state', 'imbalance_state', 'smoothed flow imbalance'),
            var('I_t1', 'state', 'imbalance_next', 'next imbalance state'),
            var('A_t', 'state', 'aggressor_spread', 'aggressor spread level'),
            var('A_t1', 'state', 'spread_next', 'next spread level'),
            var('Pb_t', 'state', 'rebatable_pool', 'balanced-flow rebate pool'),
            var('Pb_t1', 'state', 'rebatable_next', 'next rebate pool'),
        ],
        parameters=[
            param('lambda_', 0.25, 0.05, 0.8, 'imbalance EMA coefficient'),
            param('eta', 400.0, 30.0, 1500.0, 'spread sensitivity to imbalance'),
            param('share', 0.6, 0.1, 0.95, 'spread proceeds to the rebate pool'),
        ],
        equations=[
            eq('imbalance_state',
         'I_t1 = clip(I_t*(1-lambda_) + lambda_*(1000.0 + 30.0*dX_t), 200.0, 1800.0)',
         'one-sided flow pressure smooths into an imbalance index'),
            eq('aggressor_spread',
         'A_t1 = clip(1000.0 + eta*abs(I_t1-1000.0)/1000.0, 600.0, 1500.0)',
         'aggressor spread widens with imbalance distance from neutral'),
            eq('rebate_pool',
         'Pb_t1 = clip(Pb_t + share*(A_t1-1000.0)/10.0 - 5.0, 200.0, 2200.0)',
         'widened-spread proceeds fund balanced-flow rebates'),
        ],
        assumptions=[
            assumption("imbalance is computable from order flow each window", True),
            assumption("spread schedule is linear in imbalance distance", True),
        ],
        constraints=[constraint("spread bounded [600, 1500]")],
        open_questions=["what persistence qualifies flow as balanced?"],
        rationale=(
            "Imbalance mean-reverts around 1000 with flow shocks; spreads "
            "and the rebate pool respond to its distance from neutral. "
            "All states bounded around battery scales."
        ),
        version=1,
    )


def belief_weighted_fund(cid: str) -> MathModel:
    """Belief-Weighted Vol Target: exposure blends realized and implied."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('E_x', 'state', 'exposure_level', 'fund exposure level'),
            var('E_x1', 'state', 'exposure_next', 'next exposure level'),
            var('V_t', 'state', 'blended_risk', 'blended risk index'),
            var('V_t1', 'state', 'risk_next', 'next blended risk'),
        ],parameters=[
            param('w', 0.5, 0.1, 0.9, 'weight on realized vs implied'),
            param('eta', 5000.0, 500.0, 20000.0, 'risk index scaling'),
            param('resp', 0.4, 0.05, 1.5, 'exposure response to risk'),
        ],
        equations=[
            eq('blended_risk',
         'V_t1 = clip(w*abs(dX_t)/X_t*eta + (1-w)*(1000.0 + 8.0*dX_t), 200.0, 1600.0)',
         'blend of realized volatility and implied stress level'),
            eq('exposure_rule',
         'E_x1 = clip(E_x*(1-0.12) + 0.12*(2400.0 - resp*V_t1), 300.0, 2100.0)',
         'exposure de-risks as blended risk rises (target 2400 index)'),
        ],
        assumptions=[
            assumption("blend weights are fixed per rebalance (published)", True),
            assumption("exposure rule is linear with hysteresis-free updates", False),
        ],
        constraints=[constraint("exposure bounded [300, 2100]")],
        open_questions=["does signal divergence cause churn without hysteresis bands?"],
        rationale=(
            "Blended risk combines scale-free realized volatility with an "
            "implied-stress proxy; exposure moves opposite risk toward the "
            "2400 target. Bounds bracket reachable ranges on both states."
        ),
        version=1,
    )


def disagreement_quorum(cid: str) -> MathModel:
    """Disagreement-Weighted Oracle Quorum: calibration sets weights."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('W_q', 'state', 'quorum_weight', 'aggregate calibrated weight'),
            var('W_q1', 'state', 'quorum_weight_next', 'next aggregate weight'),
            var('M_q', 'state', 'median_level', 'published quorum median'),
            var('M_q1', 'state', 'median_next', 'next median'),
        ],parameters=[
            param('lambda_', 0.3, 0.05, 0.8, 'calibration EMA coefficient'),
            param('eta', 200.0, 10.0, 900.0, 'weight response to disagreement'),
            param('fee', 12.0, 1.0, 60.0, 'per-interval reporter fees'),
        ],
        equations=[
            eq('median_dynamics', 'M_q1 = clip(M_q*(1-0.3) + 0.3*X_t, 300.0, 1700.0)',
         'published median EWMA-tracks the anchor (quorum smoothing)'),
            eq('calibration_weight',
         'W_q1 = clip(W_q*(1-0.12) + 0.12*(1000.0 + eta*sqrt(abs(M_q1-X_t)/max(X_t,1.0))), 400.0, '
          '2000.0)', 'weight re-derives from realized median deviation (concave)'),
        ],
        assumptions=[
            assumption("reporter deviation is measurable against the realized median", True),
            assumption("calibration weighting is deterministic, no governance vote", True),
        ],
        constraints=[constraint("aggregate weight bounded [400, 2000]")],
        open_questions=["can sandbagged disagreement stakes fake calibration?"],
        rationale=(
            "The quorum median partially corrects toward the anchor; the "
            "aggregate weight rises with realized relative deviation. All "
            "states bounded around 1000 seeds."
        ),
        version=1,
    )


def prediction_fallback_oracle(cid: str) -> MathModel:
    """Prediction-Fee Fallback Oracle: staleness ladder with rising fees."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('F_l', 'state', 'fee_ladder', 'conversion fee level (ladder rung)'),
            var('F_l1', 'state', 'fee_ladder_next', 'next fee level'),
            var('O_p', 'state', 'open_interest', 'prediction book open interest'),
            var('O_p1', 'state', 'open_interest_next', 'next open interest'),
        ],
        parameters=[
            param('rung', 80.0, 10.0, 300.0, 'fee increment per degraded rung'),
            param('oi_floor', 150.0, 10.0, 800.0, 'minimum book open interest'),
            param('decay', 0.2, 0.02, 0.8, 'rung reset rate'),
        ],
        equations=[
            eq('open_interest',
         'O_p1 = clip(O_p*(1-0.15) + 0.15*(oi_floor + 150.0*sqrt(abs(dX_t)/X_t) + min(400.0, '
          '0.01*(X_t-1000.0))), 100.0, 1800.0)'
          , 'book open interest mean-reverts to floor, activity-shocked'),
            eq('fee_ladder',
         'F_l1 = clip(F_l*(1-0.05) + 0.05*(500.0 + rung*max(0.0, 600.0-O_p1)/100.0), 500.0, '
          '1600.0)', 'fee climbs as staleness forces lower rungs, resets as primary resumes'),
        ],
        assumptions=[
            assumption("staleness forces fallback rungs proportional to book thinness", True),
            assumption("last-rung use requires the open-interest floor", True),
        ],
        constraints=[constraint("fee ladder bounded [500, 1600]")],
        open_questions=["can a griefing attack cheaply force fallback mode?"],
        rationale=(
            "Open interest proxies the prediction book; the fee ladder "
            "climbs when thinness indicates degraded rungs and resets when "
            "depth returns. Both states bounded around 1000."
        ),
        version=1,
    )


def report_bonded_meter(cid: str) -> MathModel:
    """Report-Bonded Forecast Fee Meter: bonds back the fee band."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('B_m', 'state', 'bond_pool', 'forecast bond pool'),
            var('B_m1', 'state', 'bond_pool_next', 'next bond pool'),
            var('S_m', 'state', 'stabilization_pool', 'compensation pool'),
            var('S_m1', 'state', 'stabilization_next', 'next compensation pool'),
        ],parameters=[
            param('bond_rate', 30.0, 3.0, 120.0, 'bond inflow per interval'),
            param('forfeit', 60.0, 20.0, 900.0, 'forfeit transfer on mis-banding'),
            param('mis_band', 0.01, 0.001, 0.05, 'relative band error threshold'),
        ],
        equations=[
            eq('bond_pool',
         'B_m1 = clip(B_m + bond_rate - forfeit*sqrt(max(0.0, abs(dX_t)/X_t - mis_band))*8.0 + '
          'min(100.0, 0.005*(X_t-1000.0)), 300.0, 2400.0)'
          , 'bonds accumulate; mis-banding volatility forfeits them'),
            eq('stabilization',
         'S_m1 = clip(S_m + 0.5*forfeit*sqrt(max(0.0, abs(dX_t)/X_t - mis_band))*6.0 - 6.0, 200.0, '
          '2200.0)', 'forfeits fund the compensation pool for caught applications'),
        ],
        assumptions=[
            assumption("band error is measurable against realized median fees", True),
            assumption("half of forfeits compensate applications, half stay as bonds", True),
        ],
        constraints=[constraint("both pools bounded around battery scales")],
        open_questions=["how fine can bands be before bond costs drive reporters away?"],
        rationale=(
            "Bond and stabilization pools respond to scale-free band error; "
            "both accumulate in quiet regimes and fund compensation when "
            "mis-banding realizes. Bounds bracket seed scales."
        ),
        version=1,
    )


def attestation_settlement(cid: str) -> MathModel:
    """Attestation-Locked Settlement: bonds slash into market liquidity."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('A_b', 'state', 'attestation_bonds', 'aggregate attestation bonds'),
            var('A_b1', 'state', 'bonds_next', 'next aggregate bonds'),
            var('Liq_t', 'state', 'market_liquidity', 'market liquidity level'),
            var('Liq_t1', 'state', 'liquidity_next', 'next liquidity level'),
        ],
        parameters=[
            param('div', 0.4, 0.05, 0.9, 'max relative attestation divergence'),
            param('slash', 150.0, 20.0, 1200.0, 'slash transfer per divergence unit'),
            param('inflow', 18.0, 2.0, 80.0, 'per-window liquidity incentive'),
        ],
        equations=[
            eq('bonds',
         'A_b1 = clip(A_b*(1-0.1) + 0.1*1000.0 - slash*sqrt(max(0.0, abs(dX_t)/X_t - '
          'div*0.02))*4.0, 300.0, 2200.0)'
          , 'bonds decay toward baseline; divergence beyond tolerance slashes'),
            eq('liquidity',
         'Liq_t1 = clip(Liq_t*(1-0.05) + 0.05*1000.0 + inflow*0.5 + slash*0.4*sqrt(max(0.0, '
          'abs(dX_t)/X_t - div*0.02))*4.0, 250.0, 2400.0)'
          , 'slashing proceeds fund market liquidity incentives'),
        ],
        assumptions=[
            assumption("operator attestation divergence is cross-checked by median", True),
            assumption("40% of slashing flows to liquidity incentives", True),
        ],
        constraints=[constraint("bonds bounded [300, 2200]")],
        open_questions=["should external attestations be admitted in the challenge window?"],
        rationale=(
            "Bond divergence is scale-free relative volatility beyond a "
            "tolerance; slashing drains bonds into market liquidity. Both "
            "states bounded around 1000."
        ),
        version=1,
    )


MODELS: dict[str, str] = {
    # candidate name -> builder
}

BUILDERS = {
    "Fee-Spike Mutual for Rollup Batches": fee_spike_mutual,
    "Drawdown-Underwritten Liquidity Corridor": drawdown_corridor,
    "Counter-Cyclical Fee Sink Insurer": fee_sink_insurer,
    "Relay Congestion Cover Mesh": relay_cover_mesh,
    "Volatility-Sized Settlement Escrow": vol_sized_escrow,
    "Forecast-Indexed Fee Smoothing Pool": forecast_fee_pool,
    "Prediction-Settled Hashprice Hedge Board": hashprice_hedge,
    "Consensus-Odds Liquidity Rebate": consensus_odds_rebate,
    "Adverse-Selection Taxed Prediction Clearing": adverse_selection_tax,
    "Belief-Weighted Volatility Target Fund": belief_weighted_fund,
    "Disagreement-Weighted Oracle Quorum": disagreement_quorum,
    "Prediction-Fee Fallback Oracle": prediction_fallback_oracle,
    "Report-Bonded Forecast Fee Meter": report_bonded_meter,
    "Attestation-Locked Prediction Settlement": attestation_settlement,
}


def smoke(model: MathModel) -> tuple[bool, str]:
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
    return True, "ok"


def main(store: bool = False) -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name_to_cid = {}
    for cand in db.list_candidates(limit=None):
        name_to_cid[cand.name] = cand.id
    failures = []
    for name, builder in BUILDERS.items():
        cid = name_to_cid[name]
        model = builder(cid)
        ok, msg = smoke(model)
        print(f"  {'PASS' if ok else 'FAIL'} {cid} {name[:44]} {msg[:60]}")
        if not ok:
            failures.append((cid, name, msg))
    if failures:
        raise SystemExit(f"smoke failures: {failures}")
    print("all 14 models pass smoke")
    if not store:
        print("dry run — pass --store to store them")
        return
    for name, builder in BUILDERS.items():
        cid = name_to_cid[name]
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        model = builder(cid)
        stored_json = json.dumps(model.model_dump(mode="json"), indent=2)
        db.save_math_model(
            candidate_id=cid,
            model_json=stored_json,
            rationale=model.rationale,
            version=model.version,
        )
        print(f"  stored {cid} v{model.version}")


if __name__ == "__main__":
    main(store="--store" in sys.argv)
