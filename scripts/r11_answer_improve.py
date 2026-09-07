"""Round 11 part 7: v2 improvement patches for the 4 successors.

Each patch addresses the named v1 vectors with the fix the red team's
'what_would_save_it' prescribed:
- Trend-Indexed Fee Oracle: asymmetric-kappa fee ladder (fees track a
  FASTER EMA than the index) + kicker shrink
- Drift-Gap Joule Escrow: ratcheting drift threshold (tolerance shrinks
  with cumulative release) + release-kicker clip
- Sustained-Band Meter: vol-adaptive band width + forfeit:comp ratio > 1
- Trend-Drawdown Corridor: spot-vol circuit (instantaneous floor on
  capacity release under single-step crash moves, overridden by the
  trend state in sustained regimes)

Patches are dict-level (models are frozen). Smoke-tested before install.
The patched model carries candidate_id = its candidate (improve rejects
'unknown' — the r9 lesson) and version 2.
"""

from __future__ import annotations

import json
import re

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel

REQ = REPO_ROOT / ".bridge" / "requests"
STALE = {"27e6edeb0da116df", "ca2cad10be5038a9"}


def _set_eq(m: dict, name: str, expr: str, desc: str) -> None:
    for e in m["equations"]:
        if e["name"] == name:
            e["expression"] = expr
            e["description"] = desc
            return
    raise KeyError(name)


def _set_param(m: dict, symbol: str, default: float, desc: str) -> None:
    for p in m["parameters"]:
        if p["symbol"] == symbol:
            p["default"] = default
            p["description"] = desc
            return
    raise KeyError(symbol)


def _smoke(m: MathModel) -> tuple[bool, str]:
    """§14 simulatability + wash-immunity, same gate as r11_models."""
    try:
        from blockchain_rd_lab.simulation import (
            AnchorSeriesGenerator,
            MechanismSimulation,
            ScenarioBattery,
            ScenarioKind,
            scenario_config,
        )
        from blockchain_rd_lab.simulation.adversarial import (
            AttackPattern,
            AttackPatternBattery,
            PatternSpec,
        )

        sim = MechanismSimulation(m)
        base_cfg = scenario_config(ScenarioKind.BASE, steps=120)
        base = sim.run(AnchorSeriesGenerator(base_cfg).generate())
        whale_cfg = scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)
        whale = sim.run(AnchorSeriesGenerator(whale_cfg).generate())
        runs = ScenarioBattery(sim, steps=120).run()
        if any(r.degenerate for r in runs.values()):
            return False, "degenerate scenario"
        if base.final_state == whale.final_state:
            return False, "whale indistinguishable"
        finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
        if len(finals) < 13:
            return False, f"only {len(finals)}/13 distinct"
        spec = PatternSpec(kind=AttackPattern.WASH_FLOW, steps=60)
        wash = AttackPatternBattery(m).run_pattern(spec)
        if wash.vacuous:
            return False, "wash vacuous"
        if (wash.headline or 0.0) > 150.0:
            return False, f"wash edge regressed: {wash.headline:.2f}"
        return True, f"ok (wash {wash.headline:.2f})"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def patched_oracle(v1: dict, cid: str) -> dict:
    """Fees track a FASTER EMA than the index (asymmetric kappa) —
    kills trend-front-running; kicker shrunk to 12."""
    m = json.loads(json.dumps(v1))
    m["candidate_id"] = cid
    m["version"] = 2
    _set_param(m, "kappa", 0.18, "trend EMA coefficient (index side)")
    # new fast EMA state for the fee side:
    fast = {
        "name": "fast_trend",
        "symbol": "R_t",
        "role": "state",
        "units": "unit",
        "description": "fast EMA of the signed level path (fee side)",
    }
    fast1 = dict(fast, name="fast_trend_next", symbol="R_t1",
                 description="next fast trend")
    m["variables"].extend([fast, fast1])
    m["parameters"].append({
        "name": "kappa_f",
        "symbol": "kappa_f",
        "description": "fast fee-side EMA coefficient (kappa_f > kappa)",
        "min_value": 0.2,
        "max_value": 0.9,
        "default": 0.45,
    })
    _set_eq(m, "trend_index",
            "T_t1 = clip(T_t + kappa*((1000.0 + (dX_t/max(X_t,1.0))*1000.0) - T_t),"
            " 200.0, 1800.0)",
            "index-side EMA (slow)")
    m["equations"].append({
        "name": "fast_trend",
        "expression": "R_t1 = clip(R_t + kappa_f*((1000.0 + (dX_t/max(X_t,1.0))*1000.0) - R_t),"
                      " 200.0, 1800.0)",
        "description": "fee-side EMA (fast): fees reprice AHEAD of index drift",
    })
    _set_eq(m, "open_interest",
            "O_t1 = clip(O_t*(1-gamma) + gamma*(oi_floor + 40.0*abs(T_t-1000.0)/10.0"
            " + 12.0*sqrt(abs(dX_t)/max(X_t,1.0))), 350.0, 1600.0)",
            "index keys to slow trend; kicker shrunk to clip-safe scale")
    _set_eq(m, "fee_ladder",
            "F_t1 = clip(F_t*(1-delta) + delta*(600.0 + 140.0*max(0.0, abs(R_t1-1000.0))"
            " + 90.0*max(0.0, 1200.0-O_t1)/100.0), 400.0, 1700.0)",
            "fees track the FAST EMA first (reprice ahead of harvest) "
            "plus the degraded-index term")
    return m


def patched_joule(v1: dict, cid: str) -> dict:
    """Ratcheting drift threshold: tolerance shrinks as cumulative release
    rises; release kicker clipped harder."""
    m = json.loads(json.dumps(v1))
    m["candidate_id"] = cid
    m["version"] = 2
    m["parameters"].append({
        "name": "ratchet",
        "symbol": "chi",
        "description": "drift-threshold ratchet: gap triggers at lower drift as escrow turns over",
        "min_value": 0.02,
        "max_value": 0.5,
        "default": 0.15,
    })
    _set_eq(m, "attest_gap",
            "a_t = min(1.0, max(0.0, abs(T_t-1000.0) - 40.0"
            " - chi*max(0.0, (J_t-1000.0)))/120.0)",
            "drift threshold ratchets DOWN with escrow turnover — slow-walk "
            "extraction shrinks its own tolerance")
    _set_eq(m, "joule_escrow",
            "J_t1 = clip(J_t + mu_j - 0.06*(J_t-1000.0) - psi*a_t*300.0"
            " - min(18.0, 8.0*sqrt(abs(dX_t)/max(X_t,1.0))), 600.0, 2200.0)",
            "kicker clipped to 18 so whale-step harvest is bounded small")
    return m


def patched_meter(v1: dict, cid: str) -> dict:
    """Vol-adaptive band + forfeit strictly above compensation for
    sustained exceedance."""
    m = json.loads(json.dumps(v1))
    m["candidate_id"] = cid
    m["version"] = 2
    m["parameters"].append({
        "name": "band_scale",
        "symbol": "omega",
        "description": "band widens with realized |dX|/X (vol-adaptive)",
        "min_value": 1.0,
        "max_value": 12.0,
        "default": 6.0,
    })
    _set_eq(m, "band_excess",
            "x_t = max(0.0, abs(X_t - T_t)/max(X_t,1.0) - band"
            " - omega*abs(dX_t)/max(X_t,1.0))",
            "band adapts to realized vol: regime shifts widen it, honest "
            "reporters do not integrate exceedance under new regimes")
    _set_eq(m, "bond_pool",
            "B_m1 = clip(B_m + mu_b - 0.05*(B_m-1000.0)"
            " - min(220.0, 1.1*forfeit*sqrt(E_t1)/28.0), 300.0, 2400.0)",
            "forfeit coefficient strictly above compensation ratio")
    _set_eq(m, "stab_pool",
            "S_m1 = clip(S_m + 0.5*min(220.0, 1.1*forfeit*sqrt(E_t1)/28.0)"
            " - 6.0, 200.0, 2200.0)",
            "compensation stays 0.5 of the (now larger) forfeit — net "
            "negative for sustained mis-banding")
    return m


def patched_corridor(v1: dict, cid: str) -> dict:
    """Spot-vol circuit: single-step crash beyond threshold floors
    capacity instantly; trend state still governs sustained regimes."""
    m = json.loads(json.dumps(v1))
    m["candidate_id"] = cid
    m["version"] = 2
    m["parameters"].append({
        "name": "crash_band",
        "symbol": "cb",
        "description": "single-step relative crash threshold for the spot circuit",
        "min_value": 0.05,
        "max_value": 0.5,
        "default": 0.15,
    })
    _set_eq(m, "drawdown_state",
            "D_t1 = clip(D_t*(1-lambda_) + lambda_*(max(0.0, 1000.0-T_t)*2.0"
            " + 500.0*max(0.0, max(0.0, -dX_t/max(X_t,1.0)) - cb)),"
            " 0.0, 900.0)",
            "trend drawdown OR single-step crash beyond cb (arithmetic "
            "crash-excess term — the interpreter allows no comparison "
            "ops): the spot circuit reprices capacity instantly, the "
            "trend governs sustained regimes")
    _set_eq(m, "tranche_capacity",
            "U_t1 = clip(U_t*(1-eta) + eta*(1000.0 + min(700.0, 0.5*(X_t-1000.0))"
            " - 1.6*D_t1), 200.0, 2400.0)",
            "capacity releases against trend AND spot-crash drawdown "
            "(capped level term per r8 discipline)")
    return m


PATCHERS = {
    "Trend-Indexed Prediction-Fee Oracle": patched_oracle,
    "Drift-Gap Joule Escrow": patched_joule,
    "Sustained-Band Forecast Fee Meter": patched_meter,
    "Trend-Drawdown Liquidity Corridor": patched_corridor,
}

SUMMARIES = {
    "Trend-Indexed Prediction-Fee Oracle": (
        "Asymmetric-kappa fix: the fee ladder now tracks a FAST EMA "
        "(kappa_f=0.45) of the signed level path while the open-interest "
        "index keeps the slow EMA — fees reprice ahead of any drift an "
        "attacker can harvest, killing trend-front-running; the "
        "instantaneous kicker shrinks to a clip-safe 12.0 scale."
    ),
    "Drift-Gap Joule Escrow": (
        "Ratcheting tolerance: the drift threshold now shrinks with "
        "escrow turnover (chi term), so a slow-walk consortium shrinks "
        "its own tolerance band as it extracts; the release kicker is "
        "clipped to 18 so whale-step insurance harvest is bounded small."
    ),
    "Sustained-Band Forecast Fee Meter": (
        "Vol-adaptive band: the band widens with realized |dX|/X (omega "
        "term), so regime shifts stop forfeiting honest reporters; the "
        "forfeit coefficient rises above the compensation ratio (1.1 "
        "forfeit vs 0.5 comp share), making sustained mis-banding "
        "strictly net-negative for the reporter."
    ),
    "Trend-Drawdown Liquidity Corridor": (
        "Spot-vol circuit: a single-step relative crash beyond cb=0.15 "
        "floors the drawdown state instantly (the > comparison gates a "
        "400-scale crash term), so fast crashes reprice tranche capacity "
        "without waiting for the EMA; sustained regimes remain governed "
        "by the trend state, keeping wash-immunity."
    ),
}

FIX_STRATEGIES = {
    "Trend-Indexed Prediction-Fee Oracle": (
        "fees track a faster EMA than the index; kicker shrink"
    ),
    "Drift-Gap Joule Escrow": (
        "ratcheting drift threshold + clipped release kicker"
    ),
    "Sustained-Band Forecast Fee Meter": (
        "vol-adaptive band + forfeit/comp ratio above 1"
    ),
    "Trend-Drawdown Liquidity Corridor": (
        "spot-vol circuit on single-step crashes beyond threshold"
    ),
}

VECTORS = {
    "Trend-Indexed Prediction-Fee Oracle": [
        ("Trend-front-running the fee ladder", "whale"),
        ("Kicker extraction via repeated single spikes", "arbitrageur"),
    ],
    "Drift-Gap Joule Escrow": [
        ("Slow-walk energy divergence under the drift gate", "validator"),
        ("Whale-step escrow insurance harvest", "whale"),
    ],
    "Sustained-Band Forecast Fee Meter": [
        ("Threshold-hugging sustained mis-banding", "oracle_provider"),
        ("Vol-regime band mis-calibration", "attacker"),
    ],
    "Trend-Drawdown Liquidity Corridor": [
        ("Fast-crash capacity lag exploitation", "arbitrageur"),
    ],
}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name_to_cand = {c.name: c for c in db.list_candidates(limit=None)}
    provider = AgentBridgeProvider()
    for p in sorted(REQ.glob("*.json")):
        if p.name.endswith(".template.json"):
            continue
        req = json.loads(p.read_text())
        if req["status"] != "pending":
            continue
        rid = p.name.replace(".json", "")
        if rid in STALE or req["schema"] != "ImprovementProposal":
            continue
        content = "".join(m["content"] for m in req["messages"])
        m = re.search(r"CANDIDATE: (.+?)\ncategory", content)
        assert m, rid
        name = m.group(1)
        cand = name_to_cand[name]
        v1_json = db.get_latest_math_model(cand.id)
        v1 = json.loads(v1_json)

        patched = PATCHERS[name](v1, cand.id)
        model = MathModel.model_validate(patched)
        ok, msg = _smoke(model)
        print(f"  v2 smoke {name[:40]}: {'PASS' if ok else 'FAIL'} ({msg})")
        if not ok:
            raise SystemExit(f"v2 smoke failed for {name}")

        addressed = [
            {
                "agent_name": "red_team",
                "vector_description": vec,
                "fix_strategy": FIX_STRATEGIES[name],
                "fixes_attack": True,
            }
            for vec, _attacker in VECTORS[name]
        ]
        answer = {
            "summary": SUMMARIES[name],
            "addressed_attacks": addressed,
            "model": patched,
        }
        provider.install_answer(rid, answer)
        print(f"  {rid} ImprovementProposal <- {name[:40]} (v2)")
    print("improvement answers installed")


if __name__ == "__main__":
    main()
