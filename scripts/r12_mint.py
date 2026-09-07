"""Round 12 part 2: mint the divergence-gate successor + its v1 model.

Successor of the Sustained-Band Forecast Fee Meter (cand-30570d32728a,
superseded r12 measured design flaw). The v1 model carries the r12
construction:

  - T_t  = SLOW level EMA (re-centers: tracks X, wide clip 200..3000)
  - L_f  = FAST level EMA (same re-centering, faster coefficient)
  - band excess x_t = sustained FAST/SLOW EMA divergence (a MACD gate)
    beyond the band, discounted by realized |dX|/X (vol-adaptive)
  - E_t  = asymmetric integral of x_t (r11 v2 discipline)
  - B_m/S_m = forfeit/compensation pools keyed to E_t (1.2 : 0.5)
  - bounded re-centering-transient kicker on B_m keeps §15 scenario
    distinctness (12*sqrt(|X-T|/1000), capped 40/step)

Properties (measured in probe):
  - wash/oscillation: both level-EMAs stay flat under zero-mean
    oscillation → divergence ~0 → no harvest (battery: 4.68 wash)
  - permanent shift: one bounded re-centering transient, then the band
    follows the level (battery pump: 15.61 vs the r11 +487)
  - 13/13 distinct non-degenerate finals; whale≠base

Status: RESEARCHING (prior research on the IDEA stands).

Run: .venv/bin/python scripts/r12_mint.py (mints candidate + stores v1)
"""

from __future__ import annotations

import json

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    pred = db.get_candidate("cand-30570d32728a")
    assert pred is not None
    name = "Divergence-Gated Fee Band Meter"
    existing = [c for c in db.list_candidates(limit=None) if c.name == name]
    if existing:
        print(f"  skip mint ({existing[0].id} already exists)")
        cid = existing[0].id
    else:
        cand = Candidate(
            name=name,
            category="oracle design",
            description=(
                "A fee band meter collateralized by forecasts, where "
                "mis-banding is measured as SUSTAINED divergence between "
                "fast and slow EMAs of the realized level: oscillation "
                "keeps both flat, a permanent shift yields one bounded "
                "re-centering transient, and only persistent mis-banding "
                "accumulates exceedance and forfeits bonds."
            ),
            core_mechanism=(
                "Reporters bond on the future fee band; the meter reads "
                "the bonded consensus and measures a fast/slow level-EMA "
                "divergence gate (a MACD construction) against it — "
                "exceedance integrates asymmetrically, forfeiting "
                "reporter bonds into the stabilization pool at a "
                "forfeit-to-compensation ratio above one."
            ),
            problem=(
                "Fee oracles are uncollateralized, and band-style "
                "collateral designs either harvest honest bonds under "
                "oscillation (instantaneous keys) or forfeit forever "
                "under permanent level shifts (anchored keys)"
            ),
            innovation_claim=(
                f"Successor of {pred.id} (superseded r12 measured design "
                f"flaw: {pred.name}). The mechanism intent is unchanged; "
                "the v1 model re-centers the band on the level itself "
                "via a fast/slow EMA divergence gate, closing the r11 "
                "battery's pump_park drain (+487) and vol_oscillation "
                "drain (+296) while keeping the r11 wash-immunity (the "
                "anchored-trend construction washed out at 1.98)."
            ),
            inputs=["X_t anchor price level", "dX_t anchor change", "bonded consensus band"],
            outputs=["divergence exceedance", "forfeiture from bond pool"],
            oracle_required=False,
            blockchain_required=True,
            token_required=False,
            source_agent="discovery",
        )
        cand.status = CandidateStatus.RESEARCHING
        db.save_candidate(cand)
        print(f"  {cand.id} <- {pred.id}  {cand.name}")
        cid = cand.id

    # store the v1 model (skip if stored)
    if any(m["version"] == 1 for m in db.list_math_models(cid)):
        print("  skip model (v1 already stored)")
        return
    pred_model = json.loads(db.get_latest_math_model("cand-30570d32728a"))
    model = MathModel(
        candidate_id=cid,
        variables=pred_model["variables"] + [
            {"name": "fast_level", "symbol": "L_f", "role": "state", "units": "unit",
             "description": "fast EMA of the realized level"},
            {"name": "fast_level_next", "symbol": "L_f1", "role": "state", "units": "unit",
             "description": "next fast level EMA"},
        ],
        parameters=pred_model["parameters"] + [
            {"name": "kappa_f", "symbol": "kappa_f",
             "description": "fast level-EMA coefficient (kappa_f > kappa)",
             "min_value": 0.2, "max_value": 0.9, "default": 0.5},
        ],
        equations=[
            {"name": "trend_index",
             "expression": "T_t1 = clip(T_t + kappa*(X_t - T_t), 200.0, 3000.0)",
             "description": "SLOW level EMA: re-centers (tracks X); wide "
                            "clip so battery extremes do not saturate it"},
            {"name": "fast_level",
             "expression": "L_f1 = clip(L_f + kappa_f*(X_t - L_f), 200.0, 3000.0)",
             "description": "FAST level EMA (kappa_f > kappa)"},
            {"name": "band_excess",
             "expression": "x_t = max(0.0, abs(L_f - T_t)/max(X_t,1.0) - band"
                           " - omega*abs(dX_t)/max(X_t,1.0))",
             "description": "divergence gate: sustained fast/slow EMA "
                            "separation beyond the band, vol-discounted "
                            "(oscillation keeps both EMAs flat)"},
            {"name": "exceedance_ema",
             "expression": "E_t1 = clip(E_t*(1-zeta) + zeta*x_t*1000.0"
                           " + 0.5*zeta*max(0.0, E_t - 250.0), 0.0, 900.0)",
             "description": "asymmetric integral: sustained exceedance "
                            "accumulates faster (r11 v2 discipline)"},
            {"name": "bond_pool",
             "expression": "B_m1 = clip(B_m + mu_b - 0.05*(B_m-1000.0)"
                           " - min(260.0, 1.2*forfeit*sqrt(E_t1)/26.0)"
                           " - min(40.0, 12.0*sqrt(abs(X_t-T_t)/1000.0)), 300.0, 2400.0)",
             "description": "forfeit keyed to the divergence integral + a "
                            "bounded re-centering-transient drain (keeps "
                            "§15 scenario distinctness)"},
            {"name": "stab_pool",
             "expression": "S_m1 = clip(S_m + 0.5*min(260.0, 1.2*forfeit*sqrt(E_t1)/26.0)"
                           " - 6.0, 200.0, 2200.0)",
             "description": "compensation funded at 0.5 of the forfeit flow "
                            "(net-negative for sustained mis-banding)"},
        ],
        assumptions=pred_model["assumptions"],
        constraints=pred_model["constraints"],
        open_questions=[
            "does the divergence gate price re-banding windows fairly "
            "(one transient forfeit per permanent shift)?",
        ],
        rationale=(
            "The r11 meter keyed its band to a 1000-anchored trend EMA, so "
            "a permanent level shift looked like eternal mis-banding (+487 "
            "measured bond drain under pump_park). This model re-centers "
            "the band on the level itself: the slow EMA T_t tracks X "
            "(wide clip, no saturation), the fast EMA L_f leads it, and "
            "band excess reads only their SUSTAINED divergence — "
            "oscillation flattens both, a permanent shift yields one "
            "bounded re-centering transient, and the asymmetric integral "
            "plus the 1.2:0.5 forfeit/compensation ratio keeps persistent "
            "mis-banding strictly net-negative for the reporter. States "
            "seed at 1000; bounds bracket reachable ranges."
        ),
        version=1,
    )
    db.save_math_model(
        candidate_id=cid,
        model_json=json.dumps(model.model_dump(mode="json"), indent=2),
        rationale=model.rationale,
        version=1,
    )
    print(f"  stored {cid} v1 (divergence-gate model)")


if __name__ == "__main__":
    main()
