"""Round 11 part 6: author red-team attacks on the 4 successor v1 models.

Honest adversarial discipline (§9/§12): the attacks target the trend-EMA
construction's REAL weaknesses — EMA lag, patience extraction, kicker
leakage — not strawmen. Named vectors must be plausibly profitable;
each report also names what would save it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.redteam import (
    AttackVector,
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)

REQ = Path(__file__).resolve().parents[1] / ".bridge" / "requests"
STALE = {"27e6edeb0da116df", "ca2cad10be5038a9"}


def candidate_of(rid: str) -> str:
    req = json.loads((REQ / f"{rid}.json").read_text())
    for msg in req["messages"]:
        m = re.search(r"CANDIDATE: (.+?)\ncategory", msg["content"])
        if m:
            return m.group(1)
    raise AssertionError(f"no candidate in {rid}")


AV = AttackVector


def game(name: str) -> GameTheoryReport:
    return GAME[name]


def security(name: str) -> SecurityReport:
    return SEC[name]


def oracle(name: str) -> OracleReport:
    return ORC[name]


def redteam(name: str) -> RedTeamReport:
    return RED[name]


# -- Trend-Indexed Prediction-Fee Oracle -----------------------------------

GAME = {
    "Trend-Indexed Prediction-Fee Oracle": GameTheoryReport(
        summary=(
            "The trend-EMA index removes the wash-flow extraction the "
            "predecessor carried (+14.75 measured): zero-mean oscillation "
            "washes out of a reverting EMA by construction, and the fee "
            "discount harvest dies with it. The rational attack surface "
            "moves to the EMA's other property: lag. A patient attacker "
            "who moves the anchor by sustained one-directional flow walks "
            "the index ahead of honest degradation and harvests the "
            "fee-ladder discount during the lag window."
        ),
        attack_vectors=[
            AV(
                vector="Trend-front-running the fee ladder",
                description=(
                    "An attacker with market power over the anchor builds "
                    "a sustained directional position over kappa^-1 steps, "
                    "dragging T_t with it; the fee ladder reprices only "
                    "after the index tracks the move, so the attacker "
                    "consumes degraded fallback reads at pre-move fees "
                    "through the lag window."
                ),
                attacker="whale",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
            AV(
                vector="Kicker extraction via repeated single spikes",
                description=(
                    "The open-interest index retains a small instantaneous "
                    "|dX| kicker (30*sqrt term). An attacker who spikes "
                    "vol once per decay window keeps the kicker's "
                    "contribution alive while T stays near 1000 — the "
                    "extraction is bounded by the kicker's clip range but "
                    "nonzero."
                ),
                attacker="arbitrageur",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        equilibria_notes=(
            "Honest senders face a fee ladder that lags real degradation "
            "by ~1/kappa steps; the equilibrium fee is fair only if "
            "degradation persists longer than the lag. Transient "
            "degradation episodes price below cost."
        ),
        death_spiral_risk=3.0,
        game_theory_score=6.8,
    ),
    "Drift-Gap Joule Escrow": GameTheoryReport(
        summary=(
            "Keying the attest gap to sustained divergence closes the "
            "crafted-vol slash (+351.83 measured) — wash oscillation no "
            "longer transfers escrow from honest providers. The residual "
            "attack is patience: a provider consortium that over-attests "
            " joules while slowly walking the energy index away from the "
            "anchor stays under the drift threshold forever, extracting "
            "the spread between real and attested energy."
        ),
        attack_vectors=[
            AV(
                vector="Slow-walk energy divergence under the drift gate",
                description=(
                    "Colluding providers nudge the energy index by less "
                    "than the drift threshold per epoch while "
                    "over-attesting delivered joules by the same margin; "
                    "the gap measure never crosses the slash trigger and "
                    "the over-attestation spread accrues indefinitely."
                ),
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            ),
            AV(
                vector="Whale-step escrow insurance harvest",
                description=(
                    "The escrow carries an instantaneous sqrt(|dX|/X) "
                    "release kicker (the whale-trace term). An attacker "
                    "who can time single large anchor moves triggers "
                    "kicker-priced releases without ever moving the trend "
                    "index — extracting per-crash release value at "
                    "oscillation cost."
                ),
                attacker="whale",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        equilibria_notes=(
            "The drift gate sets a tolerance band; honest providers "
            "inside it earn the attestation spread, and the mechanism "
            "only punishes divergence beyond persistence thresholds — "
            "which is exactly the trade the patch accepted."
        ),
        death_spiral_risk=3.5,
        game_theory_score=6.5,
    ),
    "Sustained-Band Forecast Fee Meter": GameTheoryReport(
        summary=(
            "Integrated exceedance closes the per-spike forfeiture "
            "harvest (+700 measured): transient band misses decay in the "
            "EMA and honest bonds survive isolated misses. The residual "
            "attack is the mirror of the fix: an attacker who sustains "
            "mis-banding JUST above the integration threshold drains "
            "bonds at the integrated rate — the mechanism now pays "
            "compensation from the stabilization pool for the same "
            "sustained mis-banding."
        ),
        attack_vectors=[
            AV(
                vector="Threshold-hugging sustained mis-banding",
                description=(
                    "A reporter stays just outside the band every step — "
                    "small enough to keep forecasting credibility, "
                    "sustained enough that the exceedance EMA integrates "
                    "upward — harvesting stabilization-pool compensation "
                    "while the bond forfeiture is capped by the min() "
                    "bound."
                ),
                attacker="oracle_provider",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        equilibria_notes=(
            "Forfeiture and compensation both key to the integrated "
            "measure; their ratio (0.8 forfeit vs 0.5 comp coefficient) "
            "decides whether sustained mis-banding is net-negative. If "
            "compensation ever exceeds forfeiture the meter becomes a "
            "farm."
        ),
        death_spiral_risk=3.0,
        game_theory_score=6.7,
    ),
    "Trend-Drawdown Liquidity Corridor": GameTheoryReport(
        summary=(
            "Trend-keyed drawdown closes the shock-spike capacity drain "
            "(+784.99 measured): oscillation cannot pump the drawdown "
            "state. The residual attack exploits the accepted trade — "
            "crash-window lag: a fast real crash outruns the EMA, and "
            "underwriters keep selling capacity at pre-crash premiums "
            "into the crash window."
        ),
        attack_vectors=[
            AV(
                vector="Fast-crash capacity lag exploitation",
                description=(
                    "An attacker times corridor usage into a crash "
                    "faster than kappa^-1 steps: the drawdown state has "
                    "not yet integrated the crash, so tranche capacity "
                    "and premiums still price pre-crash risk — the "
                    "attacker buys tail cover below crash-fair price."
                ),
                attacker="arbitrageur",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        equilibria_notes=(
            "Underwriters bear basis risk between EMA-priced premiums "
            "and realized fast drawdowns; the tranche floor (200) is the "
            "capital that absorbs it."
        ),
        death_spiral_risk=4.0,
        game_theory_score=6.4,
    ),
}

SEC = {
    "Trend-Indexed Prediction-Fee Oracle": SecurityReport(
        summary=(
            "The reverting trend EMA is a standard low-pass filter — "
            "simple, auditable, no overflow paths. The clip bounds "
            "(200..1800) bracket reachable anchor paths; index and fee "
            "clips prevent runaway. The instantaneous kicker on the "
            "index reintroduces a small |dX| dependence that an "
            "oscillation attacker can address, but its 30*sqrt scale "
            "bounds the leak."
        ),
        attack_vectors=[
            AV(
                vector="Anchor-feed manipulation across the EMA window",
                description=(
                    "A compromised anchor feed that alternates small "
                    "biases (not zero-mean) accumulates drift in T_t "
                    "without triggering instantaneous checks; the fee "
                    "ladder prices a phantom trend."
                ),
                attacker="oracle_provider",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            ),
        ],
        hardest_attack_to_defend=(
            "Sustained biased drift in the anchor feed: it is "
            "statistically indistinguishable from a genuine trend, so "
            "the EMA faithfully prices it — the defense is feed "
            "diversification, not the filter."
        ),
        security_score=7.0,
    ),
    "Drift-Gap Joule Escrow": SecurityReport(
        summary=(
            "Escrow release and slash are separated cleanly: the slash "
            "gates on drift (sustained), the release kicker gates on "
            "instantaneous |dX|. Clip floors protect delivery "
            "continuity. The residual security issue is index "
            "independence: if the energy index is attested by the same "
            "providers it disciplines, the drift gate is self-referential."
        ),
        attack_vectors=[
            AV(
                vector="Self-attested energy index capture",
                description=(
                    "Providers who both attest joules and feed the energy "
                    "index can coordinate the two series to keep the drift "
                    "gap artificially small while over-attesting — the "
                    "gate measures their own divergence from themselves."
                ),
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            ),
        ],
        hardest_attack_to_defend=(
            "Index capture: the drift gate needs an energy index sourced "
            "independently of the slashed providers, or it degenerates "
            "into self-grading."
        ),
        security_score=6.5,
    ),
    "Sustained-Band Forecast Fee Meter": SecurityReport(
        summary=(
            "The integrated exceedance is bounded (0..900 clip) and the "
            "forfeit transfer capped by min() — no unbounded drainage "
            "path. Bond and stabilization floors survive worst-case "
            "sustained mis-banding. The residual risk is calibration: "
            "a fixed band width mis-prices honest reporting under "
            "vol-regime changes."
        ),
        attack_vectors=[
            AV(
                vector="Vol-regime band mis-calibration",
                description=(
                    "When realized vol triples (regime shift), the fixed "
                    "band makes EVERY honest reporter exceed it "
                    "persistently; the integrated measure forfeits the "
                    "whole honest bond pool — an attacker only needs to "
                    "trigger the regime change."
                ),
                attacker="attacker",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        hardest_attack_to_defend=(
            "Regime-shift calibration: a band that adapts to realized vol "
            "preserves the sustained-mis-banding semantics; a fixed band "
            "converts regime shifts into honest-bond forfeiture."
        ),
        security_score=6.6,
    ),
    "Trend-Drawdown Liquidity Corridor": SecurityReport(
        summary=(
            "The drawdown state is bounded (0..900) and keys only to "
            "sustained downtrend; the capacity release term is capped "
            "(min 700). No wash path into the drawdown state exists — "
            "the r10 choreographies are structurally closed. The "
            "residual is the crash-window exposure the lag creates."
        ),
        attack_vectors=[
            AV(
                vector="Flash-crash drawdown outrun",
                description=(
                    "A single-step crash of 40%+ moves X faster than the "
                    "EMA's kappa tracking; the corridor sells capacity "
                    "at pre-crash prices through the window — repeated "
                    "engineered crashes farm the lag spread."
                ),
                attacker="whale",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        hardest_attack_to_defend=(
            "Crash-window lag: only a spot-vol floor on capacity release "
            "(an instantaneous circuit the EMA overrides) closes it — "
            "which reintroduces some |dX| sensitivity."
        ),
        security_score=6.4,
    ),
}

ORC = {
    "Trend-Indexed Prediction-Fee Oracle": OracleReport(
        summary=(
            "The mechanism consumes its own prediction-book index rather "
            "than an external feed for degradation pricing — the oracle "
            "risk concentrates in the anchor series feeding the trend "
            "EMA. A biased-but-sustained anchor drift prices as honest "
            "trend; the filter cannot distinguish drift origin."
        ),
        data_source_assessment=(
            "Anchor level X_t is the sole exogenous input; its "
            "manipulation resistance bounds the whole construction. "
            "Feed diversification (median-of-anchors) would harden the "
            "trend index without changing its semantics."
        ),
        manipulation_vectors=[
            AV(
                vector="Sustained anchor bias trend injection",
                description=(
                    "An anchor provider holding majority weight biases "
                    "the level by a small consistent amount; the EMA "
                    "integrates the bias as trend and the ladder prices "
                    "phantom degradation, transferring fees from senders "
                    "to the insurance pool the provider can drain via "
                    "compromised senders."
                ),
                attacker="oracle_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        oracle_feasibility_score=6.8,
    ),
    "Drift-Gap Joule Escrow": OracleReport(
        summary=(
            "Two series (anchor, energy index) feed a drift gate; the "
            "construction is honest only if they are independently "
            "sourced. With independent attestation the drift measure is "
            "a clean basis-risk price; without it, self-referential."
        ),
        data_source_assessment=(
            "Energy index needs off-chain energy market data (wholesale "
            "prices) attested by parties outside the provider set being "
            "slashed — an institutional-data problem more than a "
            "cryptographic one."
        ),
        manipulation_vectors=[
            AV(
                vector="Coordinated index-anchor co-movement",
                description=(
                    "Providers push the anchor and the energy index in "
                    "the same direction by coordinated amounts so their "
                    "divergence (the slash trigger) stays under "
                    "threshold while both series drift away from truth."
                ),
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        oracle_feasibility_score=6.2,
    ),
    "Sustained-Band Forecast Fee Meter": OracleReport(
        summary=(
            "The meter prices its own output band — the oracle risk is "
            "the band's calibration data, not an external feed. "
            "Integrated exceedance is robust to single-report "
            "manipulation: one biased report decays in the EMA."
        ),
        data_source_assessment=(
            "Band calibration should track realized fee vol regimes; a "
            "frozen band converts regime shifts into systematic "
            "forfeiture of honest reporters."
        ),
        manipulation_vectors=[
            AV(
                vector="Regime-shift band exhaustion",
                description=(
                    "An attacker engineers a fee-vol regime shift (e.g. "
                    "congestion spike) that pushes realized movement "
                    "outside the fixed band; honest reporters integrate "
                    "exceedance and forfeit while the attacker's own "
                    "reports sit at the band edge."
                ),
                attacker="attacker",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        oracle_feasibility_score=6.5,
    ),
    "Trend-Drawdown Liquidity Corridor": OracleReport(
        summary=(
            "Drawdown is computed from the anchor series alone — no "
            "external oracle dependency for the core state. The "
            "corridor's capacity and premium schedules are "
            "self-contained; oracle risk reduces to anchor integrity."
        ),
        data_source_assessment=(
            "Anchor level X_t feeds both the trend EMA and the capacity "
            "level term; median-of-anchor-feeds hardens both without "
            "changing the drawdown semantics."
        ),
        manipulation_vectors=[
            AV(
                vector="Anchor crash engineering in the lag window",
                description=(
                    "An attacker with anchor influence engineers a fast "
                    "down-move (or reports one), consumes corridor "
                    "capacity at pre-crash premiums inside the EMA lag "
                    "window, then lets the anchor recover."
                ),
                attacker="oracle_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        oracle_feasibility_score=6.6,
    ),
}

RED = {
    "Trend-Indexed Prediction-Fee Oracle": RedTeamReport(
        verdict="vulnerable",
        strongest_attack=(
            "Trend-front-running the fee ladder: sustained directional "
            "anchor moves drag the trend index ahead of honest "
            "degradation, and the attacker consumes fallback reads at "
            "lagged (pre-move) fees through every kappa^-1 window."
        ),
        strongest_attack_is_profitable=True,
        attack_vectors=[
            AV(
                vector="Trend-front-running the fee ladder",
                description=(
                    "Sustained one-directional flow moves T_t; fees "
                    "reprice only after the lag; the spread between "
                    "honest degradation cost and lagged fees is the "
                    "extraction."
                ),
                attacker="whale",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
            AV(
                vector="Kicker extraction via repeated single spikes",
                description=(
                    "The 30*sqrt instantaneous kicker on the index "
                    "leaks bounded extraction under repeated isolated "
                    "spikes timed to the gamma decay."
                ),
                attacker="arbitrageur",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        what_would_save_it=(
            "Two-sided lag discipline: compute fees from a FASTER EMA "
            "than the index (asymmetric kappa) so fees reprice ahead of "
            "harvestable index drift, and shrink the instantaneous "
            "kicker's clip share."
        ),
    ),
    "Drift-Gap Joule Escrow": RedTeamReport(
        verdict="vulnerable",
        strongest_attack=(
            "Slow-walk energy divergence: a provider consortium keeps "
            "index-anchor drift just under the slash threshold while "
            "over-attesting joules — the spread accrues indefinitely "
            "inside the tolerance band the patch itself created."
        ),
        strongest_attack_is_profitable=True,
        attack_vectors=[
            AV(
                vector="Slow-walk energy divergence under the drift gate",
                description=(
                    "Coordinated sub-threshold drift plus over-attestation "
                    "extracts the attested-vs-real energy spread forever."
                ),
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        what_would_save_it=(
            "An independent energy index (sourced outside the slashed "
            "set) plus a drift threshold that ratchets down as cumulative "
            "escrow release rises — tolerance shrinks with extraction."
        ),
    ),
    "Sustained-Band Forecast Fee Meter": RedTeamReport(
        verdict="vulnerable",
        strongest_attack=(
            "Threshold-hugging sustained mis-banding: staying just "
            "outside the band forever integrates exceedance up while "
            "forfeiture stays capped — compensation can outpace "
            "forfeiture and the meter becomes a compensation farm."
        ),
        strongest_attack_is_profitable=True,
        attack_vectors=[
            AV(
                vector="Threshold-hugging sustained mis-banding",
                description=(
                    "Persistent small exceedance harvests stabilization "
                    "compensation against capped forfeiture."
                ),
                attacker="oracle_provider",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
            AV(
                vector="Vol-regime band mis-calibration",
                description=(
                    "A fixed band under a vol-regime shift forfeits "
                    "honest reporters' bonds; an attacker only triggers "
                    "the shift."
                ),
                attacker="attacker",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        what_would_save_it=(
            "Vol-adaptive band width (realized-vol-indexed) and a "
            "forfeiture-to-compensation ratio strictly above 1 for "
            "sustained exceedance."
        ),
    ),
    "Trend-Drawdown Liquidity Corridor": RedTeamReport(
        verdict="vulnerable",
        strongest_attack=(
            "Fast-crash capacity lag: a single-step crash outruns the "
            "trend EMA, and the attacker buys tail cover at pre-crash "
            "capacity prices through the lag window — the exact trade "
            "the patch accepted when it removed instantaneous "
            "sensitivity."
        ),
        strongest_attack_is_profitable=True,
        attack_vectors=[
            AV(
                vector="Fast-crash capacity lag exploitation",
                description=(
                    "Crash faster than kappa^-1, consume corridor "
                    "capacity at lagged premiums, exit before the EMA "
                    "reprices."
                ),
                attacker="arbitrageur",
                profitable_for_attacker=True,
                evidence_level="HYPOTHESIS",
            ),
        ],
        what_would_save_it=(
            "An instantaneous floor on capacity release during "
            "single-step moves beyond a crash threshold — a spot-vol "
            "circuit that the trend EMA overrides in sustained regimes, "
            "restoring fast-crash pricing without reopening wash flow."
        ),
    ),
}


def main() -> None:
    provider = AgentBridgeProvider()
    installed = 0
    for p in sorted(REQ.glob("*.json")):
        if p.name.endswith(".template.json"):
            continue
        req = json.loads(p.read_text())
        if req["status"] != "pending":
            continue
        rid = p.name.replace(".json", "")
        if rid in STALE:
            continue
        name = candidate_of(rid)
        schema = req["schema"]
        if schema == "GameTheoryReport":
            answer = GAME[name]
        elif schema == "SecurityReport":
            answer = SEC[name]
        elif schema == "OracleReport":
            answer = ORC[name]
        elif schema == "RedTeamReport":
            answer = RED[name]
        else:
            print(f"  skip {rid} {schema} — not red-team")
            continue
        provider.install_answer(rid, answer.model_dump(mode="json"))
        installed += 1
        print(f"  {rid} {schema} <- {name[:36]}")
    print(f"{installed} red-team answers installed")


if __name__ == "__main__":
    main()
