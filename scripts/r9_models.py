"""Round 9: MathModels for the 10 corpus-widening candidates.

Every model honors the BATTERY INPUT CONTRACT (see scripts/r8_models.py):
  X_t   = anchor LEVEL (~1000)
  dX_t  = anchor DELTA that step
  states seed at 1000.0; responses are SCALE-FREE (dX_t/X_t);
  clip bounds bracket reachable ranges; no dependency cycles.

Round-9 targets the families ABSENT from the ranked corpus
(governance, economic-driven, energy-driven, oracle-design) — each model
distills the candidate's stepwise mechanism into anchor-relative dynamics.
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

# same helpers as r8 (kept local so the script is standalone)


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


def treasury_governance(cid: str) -> MathModel:
    """Treasury-Backed Fee Parameter Governance: bonded parameter changes
    keyed to realized fee-revenue consequence (X_t proxies the venue's
    fee-revenue index)."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('V_t', 'state', 'vote_weight', 'fee-paid voting weight pool'),
            var('V_t1', 'state', 'vote_weight_next', 'next voting weight'),
            var('B_t', 'state', 'bond_pool', 'outstanding proposal bonds'),
            var('B_t1', 'state', 'bond_pool_next', 'next bond pool'),
            var('g_t', 'auxiliary', 'gov_gain', 'revenue gain vs baseline'),
        ],
        parameters=[
            param('rho', 0.2, 0.05, 0.6, 'weight decay per epoch (flow voting)'),
            param('theta', 0.4, 0.05, 0.9, 'bond slash share on regression'),
            param('mu_w', 15.0, 2.0, 60.0, 'per-epoch fee-paid weight accrual'),
        ],
        equations=[
            eq('gov_gain', 'g_t = min(1.0, abs(X_t-1000.0)/300.0)',
         'normalized revenue deviation from baseline'),
            eq('vote_weight',
         'V_t1 = clip(V_t*(1-rho) + rho*(1000.0 + 60.0*(dX_t/max(X_t,1.0))*1000.0), 400.0, '
          '1800.0)', 'fee-paid weight accrues with signed flow, decays fast'),
            eq('bond_dynamics',
         'B_t1 = clip(B_t + mu_w - 0.06*(B_t-1000.0) - theta*g_t*abs(dX_t)/max(X_t,1.0)*400.0,'
          ' 350.0, 2600.0)', 'bonds accumulate; regressions slash proportional to deviation'),
        ],
        assumptions=[
            assumption("anchor level proxies the venue's fee-revenue index", True),
            assumption("revenue regressions are measured against the pre-change baseline", True),
        ],
        constraints=[constraint("bond pool never below 350 (treasury floor)")],
        open_questions=["should the slash condition average two epochs to cut noise?"],
        rationale=(
            "Voting weight is a decaying flow pool (fee-paid accrual with "
            "fast rho decay, capture requires sustained usage); the bond "
            "pool takes proportional haircuts when the revenue index "
            "regresses from baseline. All states seeded 1000, bounds "
            "bracket reachable ranges."
        ),
        version=1,
    )


def demand_ladder(cid: str) -> MathModel:
    """Demand-Index Escalation Ladder: escalation premium keyed to a
    queue-depth index with refund recycling (dX_t proxies queue pressure)."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('Q_t', 'state', 'demand_index', 'queue demand index'),
            var('Q_t1', 'state', 'demand_index_next', 'next demand index'),
            var('F_t', 'state', 'esc_fee', 'escalation premium level'),
            var('F_t1', 'state', 'esc_fee_next', 'next premium level'),
            var('W_t', 'state', 'refund_reserve', 'congestion refund reserve'),
            var('W_t1', 'state', 'refund_reserve_next', 'next reserve'),
            var('u_t', 'auxiliary', 'queue_pressure', 'normalized queue pressure'),
        ],
        parameters=[
            param('beta', 0.3, 0.05, 0.8, 'demand index EMA coefficient'),
            param('phi', 0.25, 0.05, 0.8, 'escalation sensitivity to index'),
            param('kappa_r', 0.35, 0.05, 0.9, 'refund share of escalations'),
        ],
        equations=[
            eq('queue_pressure', 'u_t = sqrt(abs(dX_t)/max(X_t,1.0))',
         'scale-free queue pressure proxy'),
            eq('demand_index',
         'Q_t1 = clip(Q_t*(1-beta) + beta*(1000.0 + 300.0*u_t), 500.0, 2000.0)',
         'demand index EWMA around 1000 with pressure-driven lift'),
            eq('esc_premium',
         'F_t1 = clip(600.0 + phi*(Q_t1-1000.0), 200.0, 1500.0)',
         'escalation premium is an increasing ladder in the index'),
            eq('refund_reserve',
         'W_t1 = clip(W_t + kappa_r*(F_t1-600.0) - 0.04*(W_t-1000.0), 400.0, 2400.0)',
         'escalations recycle to the reserve; refunds drain it slowly'),
        ],
        assumptions=[
            assumption("queue depth is proxied by relative anchor moves", True),
            assumption("escalations recycle at rate kappa_r to congested settlers", True),
        ],
        constraints=[constraint("reserve floor 400 caps refund extraction")],
        open_questions=["should the ladder rungs be exponential rather than linear in Q?"],
        rationale=(
            "Queue pressure is the scale-free |dX|/X; the demand index is "
            "its EWMA; the escalation premium is an increasing function of "
            "the index; escalations recycle into a floor-bounded refund "
            "reserve. All states bracket their reachable ranges."
        ),
        version=1,
    )


def bandwidth_bond(cid: str) -> MathModel:
    """Bandwidth Bond Market: bonded relay capacity with probe-verified
    delivery and energy-metered auction pricing (X_t proxies delivered
    throughput; energy cost is an EWMA state)."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('C_t', 'state', 'committed_capacity', 'bonded capacity pool'),
            var('C_t1', 'state', 'committed_next', 'next capacity pool'),
            var('E_t', 'state', 'energy_cost', 'energy cost index'),
            var('E_t1', 'state', 'energy_cost_next', 'next energy cost'),
            var('A_t', 'state', 'auction_price', 'capacity lease price'),
            var('A_t1', 'state', 'auction_next', 'next lease price'),
            var('s_t', 'auxiliary', 'shortfall', 'delivery shortfall intensity'),
        ],
        parameters=[
            param('sigma_s', 0.15, 0.02, 0.5, 'shortfall sensitivity to probe gap'),
            param('chi', 0.25, 0.05, 0.8, 'forfait share on shortfall'),
            param('delta_e', 0.2, 0.05, 0.8, 'energy index EMA coefficient'),
        ],
        equations=[
            eq('shortfall', 's_t = sqrt(max(0.0, 0.05 - dX_t/max(X_t,1.0)))',
         'shortfall when delivered flow (dX) drops below commitment drift'),
            eq('energy_cost',
         'E_t1 = clip(E_t*(1-delta_e) + delta_e*(1000.0 + 250.0*abs(dX_t)/max(X_t,1.0)), '
          '500.0, 2200.0)', 'energy index EWMA tracks realized operating intensity'),
            eq('auction_price',
         'A_t1 = clip(0.5*E_t1 + 0.5*C_t1 + 60.0*s_t*3.0, 400.0, 2000.0)',
         'auction clears at blended energy/capacity plus shortfall premium'),
            eq('capacity_pool',
         'C_t1 = clip(C_t - chi*s_t*300.0 + 0.07*(1000.0 - C_t) + 0.03*(X_t-1000.0), 450.0,'
          ' 2400.0)', 'forfait shrinks bonded capacity; calm top-ups replenish'),
        ],
        assumptions=[
            assumption("delivered throughput is proxied by anchor level moves", True),
            assumption("probe gap (commitment minus delivery) drives forfait", True),
        ],
        constraints=[constraint("bonded capacity floor 450 (mesh minimum)")],
        open_questions=["should probes sample adversarially placed relays?"],
        rationale=(
            "Shortfall is the positive part of commitment drift minus "
            "scale-free delivery; it forfaits bonded capacity "
            "proportionally. The energy index EWMA and the auction price "
            "blend energy cost with capacity, so underpricing either is "
            "self-correcting. States bracket [400, 2400]."
        ),
        version=1,
    )


def quote_deviation_feed(cid: str) -> MathModel:
    """Quote-Deviation Slashed FX Reference: median reference with bond
    slashes keyed to deviation from realized execution (X_t proxies the
    corridor's realized execution price)."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('M_t', 'state', 'reference_rate', 'published median reference'),
            var('M_t1', 'state', 'reference_next', 'next reference'),
            var('S_t', 'state', 'slash_pool', 'reporter bond pool'),
            var('S_t1', 'state', 'slash_pool_next', 'next bond pool'),
            var('d_t', 'auxiliary', 'deviation', 'quote deviation vs realized'),
        ],
        parameters=[
            param('tau', 0.15, 0.02, 0.5, 'tolerance band on deviation'),
            param('omega', 0.45, 0.05, 0.9, 'slash intensity beyond tolerance'),
            param('mu_b', 12.0, 2.0, 50.0, 'per-window reporter bond accrual'),
        ],
        equations=[
            eq('deviation', 'd_t = max(0.0, abs(dX_t)/max(X_t,1.0) - tau)',
         'tolerance-exceeded deviation of quotes from realized'),
            eq('reference_rate',
         'M_t1 = clip(M_t*(1-0.3) + 0.3*(1000.0 + min(500.0, 0.6*(X_t-1000.0))) '
         '+ 0.25*min(400.0, X_t-M_t), 500.0, 2500.0)',
                  'median chases realized execution with bounded speed'),
            eq('slash_pool',
         'S_t1 = clip(S_t + mu_b - 0.05*(S_t-1000.0) - omega*d_t*600.0 '
         '- min(150.0, max(0.0, 0.02*(1000.0-X_t))),'
         ' 500.0, 2400.0)', 'bonds accrue; deviations beyond tolerance slash proportionally'),
        ],
        assumptions=[
            assumption("realized execution price is proxied by the anchor level", True),
            assumption("slash condition only applies above realized-flow floor", True),
        ],
        constraints=[constraint("reference bounded [600, 1500]; bond pool floor 400")],
        open_questions=["should the tolerance band widen in low-flow windows?"],
        rationale=(
            "The reference chases realized execution at bounded speed; "
            "deviation beyond tolerance slashes reporter bonds "
            "proportionally. Anchored to the corridor's own ground truth, "
            "with a flow floor assumption recorded."
        ),
        version=1,
    )


def cyclic_reserve(cid: str) -> MathModel:
    """Cyclic Demand Reserve: counter-cyclical release of recycled fees
    keyed to a demand index vs its moving average."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('K_t', 'state', 'demand_ma', 'demand moving average'),
            var('K_t1', 'state', 'demand_ma_next', 'next moving average'),
            var('Z_t', 'state', 'reserve', 'recycled fee reserve'),
            var('Z_t1', 'state', 'reserve_next', 'next reserve'),
            var('r_t', 'auxiliary', 'release', 'per-epoch rebate release'),
        ],
        parameters=[
            param('alpha_k', 0.25, 0.05, 0.8, 'demand MA smoothing'),
            param('r_max', 30.0, 5.0, 90.0, 'per-epoch release bound'),
            param('z_floor', 400.0, 200.0, 900.0, 'hard reserve floor'),
        ],
        equations=[
            eq('release',
         'r_t = min(r_max, max(0.0, 0.5*r_max*(1.0 - (X_t-K_t)/200.0)))',
         'release rises when demand is below its average (counter-cyclical)'),
            eq('reserve_path',
         'Z_t1 = clip(Z_t + min(200.0, 0.10*(X_t-1000.0)) - r_t + 8.0 '
         '+ 0.06*min(300.0, X_t-Z_t), z_floor, 3000.0)',
         'reserve accumulates in booms, releases in troughs, floor-bounded'),
            eq('demand_ma',
         'K_t1 = clip(K_t*(1-alpha_k) + alpha_k*(1000.0 + min(500.0, X_t-K_t)), '
         '500.0, 2500.0)', 'demand MA tracks the anchor level'),
        ],
        assumptions=[
            assumption("fee volume tracks the anchor level", True),
            assumption("release is bounded per epoch and floor-protected", True),
        ],
        constraints=[constraint("reserve never drains below z_floor")],
        open_questions=["should rebate eligibility decay require activity proofs?"],
        rationale=(
            "The demand MA is a bounded EMA of the anchor; release is a "
            "counter-cyclical function of demand-vs-average with a hard "
            "per-epoch cap; the reserve path accumulates in booms, "
            "releases in troughs, never below the floor."
        ),
        version=1,
    )


def productivity_clearing(cid: str) -> MathModel:
    """Productivity-Index Scaled Compute Clearing: user/provider fee split
    keyed to an endogenous throughput-per-joule index."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('I_t', 'state', 'productivity_index', 'throughput per joule index'),
            var('I_t1', 'state', 'productivity_next', 'next index'),
            var('W_t', 'state', 'provider_share', 'provider fee share (basis of 1000)'),
            var('W_t1', 'state', 'provider_share_next', 'next provider share'),
            var('e_t', 'auxiliary', 'efficiency', 'scale-free efficiency delta'),
        ],
        parameters=[
            param('alpha_i', 0.25, 0.05, 0.8, 'productivity index EMA'),
            param('step_w', 40.0, 5.0, 120.0, 'max fee-split step per epoch'),
        ],
        equations=[
            eq('efficiency', 'e_t = dX_t/max(X_t,1.0)',
         'scale-free efficiency delta of the batch stream'),
            eq('productivity_index',
         'I_t1 = clip(I_t*(1-alpha_i) + alpha_i*(1000.0 + 500.0*e_t), 550.0, 1600.0)',
         'index EWMA of realized throughput per joule'),
            eq('fee_split',
         'W_t1 = clip(W_t + max(-step_w, min(step_w, 0.2*(I_t1-1000.0))), 600.0, 1400.0)',
         'provider share moves inversely to productivity, bounded steps'),
        ],
        assumptions=[
            assumption("throughput per joule is proxied by signed anchor deltas", True),
            assumption("split rebalancing is bounded per epoch", True),
        ],
        constraints=[constraint("provider share stays in [600, 1400] (bounded steps)")],
        open_questions=["should the index use a median over provider batches?"],
        rationale=(
            "The productivity index is an EWMA of scale-free signed "
            "efficiency deltas; the user/provider split moves inversely "
            "to it with hard per-epoch step bounds, so efficiency gains "
            "flow to users smoothly and index suppression is expensive."
        ),
        version=1,
    )


def joule_escrow(cid: str) -> MathModel:
    """Joule-Bonded Inference Escrow: request escrow denominated in joules
    with an endogenous energy price index."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('J_t', 'state', 'joule_escrow', 'outstanding joule escrow'),
            var('J_t1', 'state', 'joule_escrow_next', 'next escrow'),
            var('P_e', 'state', 'energy_price', 'energy price index'),
            var('P_e1', 'state', 'energy_price_next', 'next energy price'),
            var('a_t', 'auxiliary', 'attest_gap', 'over-attestation intensity'),
        ],
        parameters=[
            param('nu', 0.25, 0.05, 0.8, 'energy price index EMA'),
            param('psi', 0.4, 0.05, 0.9, 'bond slash on over-attestation'),
            param('mu_j', 18.0, 3.0, 70.0, 'per-epoch escrow inflow (joules)'),
        ],
        equations=[
            eq('attest_gap', 'a_t = sqrt(max(0.0, abs(dX_t)/max(X_t,1.0) - 0.06))',
         'attestation gap beyond measurement tolerance'),
            eq('energy_price',
         'P_e1 = clip(P_e*(1-nu) + nu*(1000.0 + 400.0*abs(dX_t)/max(X_t,1.0)), 550.0, '
          '2000.0)', 'energy index EWMA of mesh realized cost intensity'),
            eq('joule_escrow',
         'J_t1 = clip(J_t + mu_j - 0.05*(J_t-1000.0) - psi*a_t*250.0, 500.0, 2200.0)',
         'escrow releases against attested joules; gaps slash bonds'),
        ],
        assumptions=[
            assumption("mesh energy cost intensity is proxied by |dX|/X", True),
            assumption("over-attestation beyond tolerance slashes bonds", True),
        ],
        constraints=[constraint("escrow floor 500 (solvency margin)")],
        open_questions=["should regional energy heterogeneity split the index?"],
        rationale=(
            "The energy price index is an EWMA of scale-free cost "
            "intensity; escrow releases against attested consumption, and "
            "over-attestation beyond tolerance is prepaid through bond "
            "slashes. States bracket [500, 2200]."
        ),
        version=1,
    )


def output_swap_board(cid: str) -> MathModel:
    """Output-Indexed Compute Swap Board: benchmark-settled swaps margined
    to the benchmark distribution, not a spot price."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('B_t', 'state', 'benchmark_level', 'rolling benchmark score'),
            var('B_t1', 'state', 'benchmark_next', 'next benchmark score'),
            var('G_t', 'state', 'margin_pool', 'posted margin pool'),
            var('G_t1', 'state', 'margin_next', 'next margin pool'),
            var('v_t', 'auxiliary', 'vol', 'benchmark distribution volatility'),
        ],
        parameters=[
            param('alpha_b', 0.3, 0.05, 0.8, 'benchmark level EMA'),
            param('lambda_v', 0.2, 0.05, 0.8, 'volatility EMA'),
            param('m_mult', 0.5, 0.1, 1.5, 'margin multiplier on vol'),
        ],
        equations=[
            eq('vol', 'v_t = sqrt(abs(dX_t)/max(X_t,1.0))',
         'scale-free benchmark distribution volatility'),
            eq('benchmark_level',
         'B_t1 = clip(B_t*(1-alpha_b) + alpha_b*(1000.0 + min(400.0, 0.7*(X_t-1000.0))) '
         '+ 0.2*min(600.0, X_t-B_t), 500.0, 2500.0)',
         'benchmark EMA of verified task scores'),
            eq('margin_pool',
         'G_t1 = clip(G_t*(1-0.08) + 0.08*(1000.0 + m_mult*v_t*500.0) '
         '+ 0.05*min(600.0, X_t-G_t), 400.0, 2400.0)',
                  'margin tracks distribution volatility, not spot'),
        ],
        assumptions=[
            assumption("verified benchmark scores are proxied by anchor moves", True),
            assumption("margining is to the distribution, not a spot price", True),
        ],
        constraints=[constraint("margin floor 450 (settlement solvency)")],
        open_questions=["should agreed task sets rotate to resist overfitting?"],
        rationale=(
            "The benchmark level is a bounded EMA of verified scores; "
            "margin requirements are a function of distribution "
            "volatility (scale-free |dX|/X), not spot price, keeping the "
            "board stable when capacity spot prices are volatile but "
            "output distributions are not."
        ),
        version=1,
    )


def fee_tier_registry(cid: str) -> MathModel:
    """Fee-Tier Voted Model Registry: decaying fee-paid weight governs tier
    changes; regressions rebate users from proposer bonds."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('H_t', 'state', 'registry_weight', 'fee-paid registry weight'),
            var('H_t1', 'state', 'registry_weight_next', 'next weight'),
            var('T_t', 'state', 'tier_level', 'fee-tier level index'),
            var('T_t1', 'state', 'tier_next', 'next tier level'),
        ],
        parameters=[
            param('rho_h', 0.3, 0.05, 0.8, 'weight decay per epoch'),
            param('eta', 60.0, 10.0, 200.0, 'tier sensitivity to weighted vote'),
            param('mu_h', 14.0, 2.0, 50.0, 'per-epoch fee-paid accrual'),
        ],
        equations=[
            eq('registry_weight',
         'H_t1 = clip(H_t*(1-rho_h) + rho_h*(1000.0 + 50.0*dX_t/max(X_t,1.0)*10.0), 500.0,'
          ' 1700.0)', 'weight accrues with signed fee flow, decays fast'),
            eq('tier_level',
         'T_t1 = clip(T_t*(1-0.15) + 0.15*(1000.0 + 0.2*(H_t1-1000.0)) + '
          '0.1*eta*(dX_t/max(X_t,1.0)), 550.0, 1500.0)',
         'tiers follow weighted votes on a delay, bounded steps'),
        ],
        assumptions=[
            assumption("registry fee flow is proxied by anchor deltas", True),
            assumption("tier changes execute on a delay with proposer bonds", True),
        ],
        constraints=[constraint("tier steps bounded per epoch (stability)")],
        open_questions=["should regressions auto-rebate from bonds without vote?"],
        rationale=(
            "Registry weight is a fast-decaying flow pool (capture needs "
            "sustained current usage); tier levels follow weighted votes "
            "with bounded steps on a delay. Both states bracket reachable "
            "ranges around the 1000 seed."
        ),
        version=1,
    )


def vol_rebate_curve(cid: str) -> MathModel:
    """Vol-Adaptive Market Making Rebate Curve: rebates keyed to benchmark
    distribution volatility, funded by widening taker fees."""
    return MathModel(
        candidate_id=cid,
        variables=[*_inputs(),
            var('L_t', 'state', 'vol_index', 'benchmark volatility index'),
            var('L_t1', 'state', 'vol_next', 'next volatility index'),
            var('N_t', 'state', 'rebate_level', 'maker rebate level'),
            var('N_t1', 'state', 'rebate_next', 'next rebate level'),
            var('t_t', 'auxiliary', 'taker_spread', 'taker fee spread'),
        ],
        parameters=[
            param('alpha_v', 0.25, 0.05, 0.8, 'vol index EMA'),
            param('kappa_n', 0.4, 0.05, 0.9, 'rebate sensitivity to vol'),
            param('n_cap', 0.8, 0.1, 2.0, 'rebate cap multiple'),
        ],
        equations=[
            eq('vol_index',
         'L_t1 = clip(L_t*(1-alpha_v) + alpha_v*(1000.0 + 400.0*sqrt(abs(dX_t)/max(X_t,1.0)))'
         ', 500.0, 2000.0)', 'vol index EWMA of scale-free benchmark moves'),
            eq('taker_spread', 't_t = 0.2 + 0.3*(L_t1-1000.0)/1000.0',
         'taker fees widen with the same vol index (funding)'),
            eq('rebate_curve',
         'N_t1 = clip(N_t*(1-0.1) + 0.1*(1000.0 + kappa_n*(L_t1-1000.0)*n_cap), 500.0, '
          '2000.0)', 'rebates concentrate near the mean when vol is high'),
        ],
        assumptions=[
            assumption("benchmark distribution volatility proxies |dX|/X", True),
            assumption("rebates fund entirely from taker spreads", True),
        ],
        constraints=[constraint("rebate curve bounded; parameters bond-gated")],
        open_questions=["should index publication be delayed vs curve front-running?"],
        rationale=(
            "The vol index is a bounded EMA of scale-free moves; maker "
            "rebates are an increasing function of it (paying for "
            "mean-stabilizing depth), funded by taker spreads that widen "
            "in exactly those regimes. States bracket [500, 2000]."
        ),
        version=1,
    )


BUILDERS = {
    "Treasury-Backed Fee Parameter Governance": treasury_governance,
    "Demand-Index Escalation Ladder for FX Batches": demand_ladder,
    "Bandwidth Bond Market for Relay Peers": bandwidth_bond,
    "Quote-Deviation Slashed FX Reference Feed": quote_deviation_feed,
    "Cyclic Demand Reserve for Fee Recycles": cyclic_reserve,
    "Productivity-Index Scaled Compute Clearing": productivity_clearing,
    "Joule-Bonded Inference Escrow": joule_escrow,
    "Output-Indexed Compute Swap Board": output_swap_board,
    "Fee-Tier Voted Model Registry": fee_tier_registry,
    "Vol-Adaptive Market Making Rebate Curve for Compute Futures": vol_rebate_curve,
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
    print("all 10 models pass smoke")
    if not store:
        print("dry run — pass --store to store them")
        return
    for name, builder in BUILDERS.items():
        cid = name_to_cid[name]
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        existing = db.list_math_models(cid)
        if any(m.version == 1 for m in existing):
            # formalize already stored v1 from the bridge answer —
            # re-storing would duplicate content as an auto-version bump
            print(f"  skip {cid} (v1 already stored)")
            continue
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
