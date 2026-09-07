"""Round 11 part 2: mint the 4 successor candidates (lineage recorded).

Each successor carries the ORIGINAL mechanism intent with the r11
correction: the v1 model keys its adversarially-sensitive state to
DIRECTIONAL-SUSTAINED measures (EMA of signed relative moves) instead
of instantaneous |dX|, so zero-mean crafted oscillation cannot pump
escrow slash gaps, bond forfeiture, drawdown states, or open-interest
indices — while sustained organic stress still triggers the response.

Status: RESEARCHING (prior research on the IDEA stands; the research
stage replays it free from stored bridge answers).

Run: .venv/bin/python scripts/r11_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

SUCCESSORS: list[dict[str, str | list[str]]] = [
    {
        "name": "Trend-Indexed Prediction-Fee Oracle",
        "category": "oracle design",
        "predecessor": "cand-cab81fc40bbf",
        "problem": (
            "Oracle failure becomes a halt or an unpriced risk; degraded "
            "data keeps being consumed at the same price as honest data"
        ),
        "core_mechanism": (
            "Oracle failure is a priced service level: a fee ladder makes "
            "degraded data expensive to use and funds sender insurance. "
            "The r11 correction: the ladder's open-interest index reads a "
            "directional-sustained EMA of SIGNED relative moves, not "
            "instantaneous volatility, so crafted zero-mean oscillation "
            "cannot inflate the index and harvest fee discounts"
        ),
        "description": (
            "A prediction-book open-interest index is computed as an EMA of "
            "signed relative anchor moves (trend), feeding a fee ladder "
            "that prices fallback oracle reads; oscillation washes out of "
            "the index, sustained drift moves fees."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "fee ladder schedule"],
        "outputs": ["trend open-interest index", "priced fallback fee"],
    },
    {
        "name": "Drift-Gap Joule Escrow",
        "category": "energy economics",
        "predecessor": "cand-e98e5859f3f5",
        "problem": (
            "AI inference pricing ignores the energy cost of compute; "
            "over-attestation of delivered joules is cheap to attempt"
        ),
        "core_mechanism": (
            "Escrow, fees, and bonds are denominated in joules with an "
            "endogenous energy price index. The r11 correction: the "
            "attestation gap reads directional-sustained divergence "
            "between the anchor level and the energy index (an EMA of "
            "signed relative moves), not instantaneous |dX| spikes, so "
            "crafted vol cannot slash honest providers' escrow"
        ),
        "description": (
            "An attestation gap measure integrates signed relative "
            "divergence between anchor and energy index; the escrow "
            "releases per attested joule and slashes only on sustained "
            "divergence, so wash-flow oscillation fails to extract."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "energy price index"],
        "outputs": ["drift-gap attestation measure", "released fees per attested joule"],
    },
    {
        "name": "Sustained-Band Forecast Fee Meter",
        "category": "oracle design",
        "predecessor": "cand-52eeaf35607b",
        "problem": (
            "Fee oracles are uncollateralized: a bad reading costs the "
            "reader, not the reporter"
        ),
        "core_mechanism": (
            "The fee oracle is collateralized by forecasts of its own "
            "output: reporters bond on the future band and forfeit on "
            "mis-banding. The r11 correction: forfeiture keys to the "
            "INTEGRATED mis-band excess (EMA of band exceedance), not "
            "per-step |dX|, so single crafted vol spikes cannot "
            "forfeit honest bonds — only sustained mis-banding drains"
        ),
        "description": (
            "A meter reads the bonded consensus band; an EMA of band "
            "exceedance converts into forfeiture from the bond pool and "
            "compensation from the stabilization pool, so wash-flow "
            "oscillation cannot harvest collateral one spike at a time."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "bonded consensus band"],
        "outputs": ["integrated mis-band excess", "forfeiture from bond pool"],
    },
    {
        "name": "Trend-Drawdown Liquidity Corridor",
        "category": "two-sided market",
        "predecessor": "cand-f8fc37dce6a1",
        "problem": (
            "Cross-corridor drawdown insurance is priced exogenously and "
            "rarely matches the corridor's realized risk"
        ),
        "core_mechanism": (
            "The corridor's own realized drawdown series prices underwriter "
            "premiums and recruits capacity. The r11 correction: the "
            "drawdown state keys to a directional-sustained EMA of SIGNED "
            "relative moves, not sqrt(|dX|) spikes, so crafted oscillation "
            "cannot pump the drawdown state and drain tranche capacity"
        ),
        "description": (
            "An EMA of signed relative moves feeds the drawdown state; "
            "tranche capacity responds to sustained drawdown trends, and "
            "underwriter premiums reprice on the trend drawdown, not on "
            "wash-flow spikes."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "underwriter opt-in schedule"],
        "outputs": ["trend drawdown state", "tranche capacity adjustment"],
    },
]


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for spec in SUCCESSORS:
        pred = db.get_candidate(str(spec["predecessor"]))
        assert pred is not None, f"predecessor {spec['predecessor']} missing"
        cand = Candidate(
            name=str(spec["name"]),
            category=str(spec["category"]),
            description=str(spec["description"]),
            core_mechanism=str(spec["core_mechanism"]),
            problem=str(spec["problem"]),
            innovation_claim=(
                f"Successor of {pred.id} (superseded r11 measured "
                f"adversarial residual: {pred.name}). The mechanism intent "
                "is unchanged; this candidate re-enters the funnel with a "
                "model whose adversarially-sensitive states key to "
                "directional-sustained EMA measures of signed relative "
                "moves, closing the r10 §20 pattern-battery edges "
                "(fee-ladder discount manipulation, escrow slash via "
                "crafted vol, bond forfeiture via vol spikes, drawdown "
                "pumping via oscillation)."
            ),
            inputs=list(spec["inputs"]),  # type: ignore[arg-type]
            outputs=list(spec["outputs"]),  # type: ignore[arg-type]
            oracle_required=False,
            blockchain_required=True,
            token_required=False,
            source_agent="discovery",
        )
        cand.status = CandidateStatus.RESEARCHING
        db.save_candidate(cand)
        print(f"  {cand.id} <- {pred.id}  {cand.name[:46]}")


if __name__ == "__main__":
    main()
