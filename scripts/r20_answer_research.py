"""Round 20: research answers for the retention-ratchet successor.

Prior art: volatility-scaled capital buffers (CCP margin
procyclicality) are the prior-art analogue of the superseded
predecessor's retention rule — and the documented ratchet concern
is the economic form of the r20 resonance finding; the
signed-separation retention key is the lab's own r13 lineage.

Run: .venv/bin/python scripts/r20_answer_research.py
"""

from __future__ import annotations

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.research import (
    EconomicConcern,
    EconomistReport,
    MarketReport,
    PriorArtReport,
    ResearchSource,
    SimilarMechanism,
)

PRIOR = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="CCP volatility-scaled initial margin",
            url="https://www.bis.org/publ/qtrpdf/r_qt1803.htm",
            similarity_note=(
                "Central counterparties size margin buffers to "
                "realized volatility — the exact class of the "
                "superseded predecessor's retention rule; the "
                "documented procyclicality concern (buffers tighten "
                "when stress hits, ratchet when stress is crafted) "
                "is the economic form of the r20 resonance ratchet"
            ),
        ),
        SimilarMechanism(
            name="Through-the-cycle capital buffers (Basel "
                 "countercyclical buffer)",
            url="https://www.bis.org/bcbs/ccyb/",
            similarity_note=(
                "Regulators key buffers to a SLOW credit-gap anchor "
                "rather than point-in-time vol — the anchor-following "
                "principle this successor's slow EMA inherits"
            ),
        ),
    ],
    search_queries=[
        "volatility-indexed retention escrow mechanism",
        "procyclical margin buffer ratchet crypto",
        "countercyclical capital buffer slow anchor keying",
    ],
    sources=[
        ResearchSource(
            title="Margin procyclicality and the stability of "
                  "central counterparties",
            url="https://www.bis.org/publ/qtrpdf/r_qt1803.htm",
            source_type="paper",
            retrieved_note="2024: CCP buffers keyed to realized vol "
                           "amplify stress cycles",
        ),
        ResearchSource(
            title="Basel III countercyclical capital buffer "
                  "framework",
            url="https://www.bis.org/bcbs/ccyb/",
            source_type="intl_org",
            retrieved_note="2024: through-the-cycle anchor buffers "
                           "as the procyclicality fix",
        ),
    ],
    findings=[
        "Volatility-procyclical buffers ratchet under crafted stress "
        "cycling — the predecessor's measured flaw class (r20: "
        "retention pinned at the 0.9 ceiling every ramp, 285 -> 6479 "
        "linear in N)",
        "Through-the-cycle anchors (slow EMAs here) are the "
        "standard fix; SIGNED pressure-vs-anchor separation keys "
        "retention to regime direction, not turbulence",
        "No substantially similar implementation of the specific "
        "signed-separation retention key with a bounded reverting "
        "buffer target was identified in the searched sources",
    ],
    confidence=0.8,
    conclusion=(
        "Adjacent mechanisms exist (vol-scaled buffers, anchored "
        "countercyclical buffers); the signed-separation retention "
        "polarity on an anchor-reverting escrow target is the lab's "
        "own r13 lineage applied to fee smoothing — novel in this "
        "corpus, not identified in searched sources"
    ),
)

ECON = EconomistReport(
    summary=(
        "The successor is a through-the-cycle insurance buffer: "
        "retention rises only while fast pressure leads the slow "
        "regime anchor (sustained directional move, not a spike), "
        "releases on crash legs, and the buffer target reverts to "
        "anchor + cap*current policy. The predecessor's absolute-vol "
        "key was a one-way ratchet under adversarial cycling (r20 "
        "measured); signed keying aligns retention with regime "
        "direction — the procyclicality-corrected-buffer principle"
    ),
    concerns=[
        EconomicConcern(
            topic="retention farming via sustained pressure",
            note=(
                "Holding the separation key positive requires "
                "sustaining a real directional move; the slow EMA "
                "prices it in by following (bounded by the 0.9 clip)"
            ),
            severity=3.0,
            evidence_level="INFERENCE",
            fatal=False,
        ),
        EconomicConcern(
            topic="anchor lag on fast genuine breaks",
            note=(
                "The slow anchor trails a fast one-sided regime "
                "break; a disclosed responsiveness gap, not an "
                "extraction (no attacker P&L path)"
            ),
            severity=2.0,
            evidence_level="INFERENCE",
            fatal=False,
        ),
    ],
    strengths=[
        "cycle-neutral by construction: under strike-recovery "
        "cycling the escrow converges to the cycle-average of its "
        "target — N-independent (measured heads [0,0,0,0])",
        "no free accumulator: buffer size keys CURRENT policy, never "
        "pressure history",
        "symmetric caps both directions (r18 mirrored-cap discipline)",
    ],
    economic_coherence_score=7.5,
    evidence_level="INFERENCE",
)

MARKET = MarketReport(
    customer=(
        "Settlement-heavy applications on volatile assets (rollup "
        "batches, relay meshes, FX corridors) that need predictable "
        "per-transaction fees"
    ),
    problem=(
        "Fee spikes on volatile assets make per-transaction UX "
        "unpredictable; existing volatility-scaled smoothing buffers "
        "inflate under stress-farming (the r20 measured ratchet "
        "class)"
    ),
    existing_alternatives=[
        "Volatility-scaled buffers (respond fast to one-sided "
        "stress but ratchet under crafted cycling — the r20 "
        "measured class)",
        "Fixed buffers (cycle-neutral but unresponsive to genuine "
        "pressure)",
    ],
    market_size_note=(
        "Fee-smoothing/abstraction products are an active category "
        "on major L1s; the differentiator here is cycle-neutrality "
        "under adversarial conditions — a readable risk story for "
        "operators of batch/relay settlement"
    ),
    adoption_barriers=[
        "requires sustained fee inflow to seed the buffer",
        "buffer sufficiency under prolonged one-sided stress "
        "(insurance semantics; the disclosed trade)",
    ],
    market_demand_score=6.5,
    evidence_level="INFERENCE",
)


def main() -> None:
    p = AgentBridgeProvider()
    for rid, ans in [
        ("b0188b92068decb1", PRIOR),
        ("db14a32afb41b60b", ECON),
        ("8b1c9f834ac91878", MARKET),
    ]:
        p.install_answer(rid, ans.model_dump(mode="json"))
        print(f"installed {rid} {type(ans).__name__}")


if __name__ == "__main__":
    main()
