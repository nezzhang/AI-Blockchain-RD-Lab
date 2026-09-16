"""§17/§25 deterministic token economics report renderer.

Renders a code-only report (no LLM, §2) that answers every §25
question for each ranked token design. The report is byte-deterministic:
same store state → same bytes.

This is RESEARCH OUTPUT (§28). No real token issuance logic is produced.
The report measures structural properties and discloses limitations.

r39: initial implementation.
"""

from __future__ import annotations

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.tokenomics.combinator import (
    TokenDesign,
    combine_all_registered,
)
from blockchain_rd_lab.tokenomics.scoring import (
    TokenScore,
    rank_designs,
    rank_designs_with_dynamics,
)
from blockchain_rd_lab.tokenomics.stock import (
    SCENARIOS,
    run_stock_scenario,
)
from blockchain_rd_lab.tokenomics.supply_drivers import SupplyDriver


def _answer_what_token_represents(design: TokenDesign) -> str:
    """§25: What does 1 token represent?"""
    cat = design.driver.category.value
    tags = sorted(design.driver.compatibility_tags)
    return (
        f"1 token represents one unit of {cat} supply signal "
        f"for the {design.mechanism_name} mechanism. "
        f"Compatibility scope: {', '.join(tags) if tags else 'none'}."
    )


def _answer_why_value(score: TokenScore, driver: SupplyDriver) -> str:
    """§25: Why should the token have value?"""
    parts: list[str] = []
    if score.dilution_resistance >= 5.0:
        parts.append("structural dilution resistance (bounded supply function)")
    if score.death_spiral_resistance >= 5.0:
        parts.append("death-spiral defense (bidirectional mint/burn)")
    if score.game_theory_stability >= 5.0:
        parts.append("game-theoretic stability (Nash-bounded incentives)")
    if not parts:
        return (
            "Under offline analysis, no structural value proposition "
            "was identified. This driver requires live market data to "
            "evaluate value accrual (§2 caveat: simulation-stage only)."
        )
    return "Value derives from: " + "; ".join(parts) + "."


def _answer_dilution_risk(score: TokenScore, driver: SupplyDriver) -> str:
    """§25: Does supply growth create dilution?"""
    if score.dilution_resistance >= 8.0:
        return (
            "LOW RISK. The supply function is bounded [-1, 1] and "
            "includes a burn path. Runaway minting is structurally impossible."
        )
    if score.dilution_resistance >= 5.0:
        return (
            "MODERATE RISK. The supply function is bounded but lacks "
            "a demonstrated burn path under all tested states. Dilution "
            "is contained but not eliminated."
        )
    return (
        "HIGH RISK. The supply function may be unbounded or lacks a "
        "burn mechanism. Supply growth could dilute holders without "
        "structural limit."
    )


def _answer_death_spiral(score: TokenScore) -> str:
    """§25: Can supply reduction create a death spiral?"""
    if score.death_spiral_resistance >= 8.0:
        return (
            "LOW RISK. The supply function includes both mint and burn "
            "paths within bounded limits. Demand drops trigger mint "
            "pressure, preventing deflationary cascades."
        )
    if score.death_spiral_resistance >= 5.0:
        return (
            "MODERATE RISK. Bounded supply prevents infinite contraction "
            "but the mint response to demand drops is limited."
        )
    return (
        "HIGH RISK. The supply function lacks a demonstrated mint "
        "response to demand contraction. A deflationary cascade is "
        "structurally possible."
    )


def _answer_manipulation(driver: SupplyDriver) -> str:
    """§25: Can the system be gamed? / Can data be manipulated?"""
    vectors = driver.manipulation_vectors
    if not vectors:
        return "No known manipulation vectors identified in offline analysis."
    lines = [f"{len(vectors)} known manipulation vector(s):"]
    for v in vectors:
        lines.append(f"  - {v}")
    if not driver.offline_scoreable:
        lines.append(
            "  NOTE: this driver requires live oracle data; manipulation "
            "risk increases when oracle feeds are adversarial."
        )
    return "\n".join(lines)


def _answer_demographic_collapse(driver: SupplyDriver) -> str:
    """§25: What happens during demographic collapse?"""
    tags = driver.compatibility_tags
    if "population" in tags or "demographic" in tags:
        return (
            "APPLICABLE. This driver's supply signal depends on population "
            "data. Demographic collapse would reduce mint pressure. If the "
            "supply function lacks a floor, prolonged population decline "
            "creates sustained deflationary pressure. The bounded clamp "
            "prevents catastrophic values but not persistent mild deflation."
        )
    return "NOT DIRECTLY APPLICABLE. This driver does not use demographic signals."


def _answer_data_revision(driver: SupplyDriver) -> str:
    """§25: What happens if data is revised? / sources disagree?"""
    if not driver.offline_scoreable:
        return (
            "LIVE ORACLE DEPENDENCY. Data revisions propagate through "
            "the supply function on the next epoch. If two oracle sources "
            "disagree, the mechanism must specify a resolution policy "
            "(median, most-recent, quorum). This is NOT modeled in the "
            "offline laboratory — disclosed, not smoothed (§12)."
        )
    return (
        "OFFLINE-SCOREABLE. This driver uses on-chain verifiable data. "
        "External data revision does not affect the supply function."
    )


def build_token_report(
    db: LabDatabase,
    candidate_id: str,
) -> str:
    """Render the full §25 token economics report for one candidate.

    Returns markdown text. Deterministic: same DB state → same bytes.
    Raises ValueError if candidate not found.
    """
    cand = db.get_candidate(candidate_id)
    if cand is None:
        raise ValueError(f"candidate not found: {candidate_id}")

    description = cand.description or ""
    designs = combine_all_registered(candidate_id, cand.name, description)
    ranked = rank_designs(designs)

    lines: list[str] = []
    lines.append(f"# §17/§25 Token Economics Report: {cand.name}")
    lines.append("")
    lines.append(
        f"Candidate: `{candidate_id}` | Mechanism: {cand.name} | "
        f"Overall score: {cand.overall_score}"
    )
    lines.append("")
    lines.append(
        "RESEARCH ONLY (§28). No real token issuance logic is produced. "
        "This report measures structural properties of hypothetical "
        "token supply designs paired with the stored mechanism. All "
        "scores are computed deterministically from the supply driver "
        "registry — no LLM, no randomness."
    )
    lines.append("")

    # Compatibility summary
    from blockchain_rd_lab.tokenomics.combinator import extract_mechanism_tags
    tags = extract_mechanism_tags(description)
    lines.append("## Mechanism Tag Extraction")
    lines.append("")
    if tags:
        lines.append(f"Extracted tags: {', '.join(sorted(tags))}")
    else:
        lines.append(
            "No mechanism tags extracted from description. The combinator "
            "cannot match any supply drivers without semantic overlap. "
            "This is an honest absence, not a failure."
        )
    lines.append("")
    lines.append(f"Compatible designs found: {len(ranked)}")
    lines.append("")

    if not ranked:
        lines.append(
            "No compatible supply drivers were found for this mechanism. "
            "The §17 combinator requires semantic tag overlap between the "
            "mechanism description and driver compatibility tags. Without "
            "overlap, no pairing is produced (§18: no random combinations)."
        )
        lines.append("")
        return "\n".join(lines)

    # Ranked designs table
    # r40 (the lab's own audit, F5): the column previously rendered
    # raw oracle_manipulability (a BADNESS score) beside three
    # higher-better columns with no direction marker — a reader
    # naturally parsed "Oracle Manip. 10.0" as good in this table.
    # Every column now reads higher = better; the raw vector count
    # stays in the §25 prose section where it is disclosed honestly.
    lines.append("## Ranked Token Designs")
    lines.append("")
    lines.append(
        "| Rank | Design ID | Driver Category | Compatibility | "
        "Dilution | Death Spiral | Oracle Resistance | "
        "GT Stability | Overall |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|"
    )
    for i, (design, score) in enumerate(ranked, 1):
        lines.append(
            f"| {i} | `{score.design_id}` | {design.driver.category.value} | "
            f"{design.compatibility_score:.2f} | "
            f"{score.dilution_resistance:.1f} | "
            f"{score.death_spiral_resistance:.1f} | "
            f"{10.0 - score.oracle_manipulability:.1f} | "
            f"{score.game_theory_stability:.1f} | "
            f"{score.overall_display:.4f} |"
        )
    lines.append("")

    # Dynamics-informed scores (r42): the SAME dimensions and weights,
    # with the r41 battery's MEASURED edges as dimension inputs —
    # published BESIDE the structural ranking, never instead of it.
    # A rank flip between the two tables is disclosed explicitly
    # (the r42 contract: visible, never silent).
    dyn_ranked = rank_designs_with_dynamics(designs)
    lines.append("## Dynamics-Informed Scores (r42)")
    lines.append("")
    lines.append(
        "The table above scores STRUCTURAL properties (boundedness, "
        "path existence). This table scores the same four dimensions "
        "under the same weights (0.30/0.25/0.25/0.20) with the r41 "
        "supply-dynamics battery's MEASURED edges as inputs: dilution "
        "resistance consumes the mint-extraction surface "
        "(max(wash_mint, creep)/steps), death-spiral resistance "
        "consumes the measured drain depth (burn_park/steps), "
        "game-theory stability consumes the measured ratchet ratio "
        "(resonance / (cycles x round_trip); 1.0 = linear, the "
        "measured no-ratchet result). Oracle manipulability stays "
        "structural in both tables (self-reported vector counts — "
        "the battery has no oracle-analogue choreography, disclosed). "
        "A driver with no attack surface for a direction scores that "
        "direction 10.0 (nothing can be forged where no path "
        "exists); vacuous patterns are listed per design."
    )
    lines.append("")
    lines.append(
        "| Rank | Design ID | Structural | Dynamics | Delta | "
        "Mint Extraction | Drain Depth | Ratchet |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    struct_overall = {s.design_id: s.overall for _, s in ranked}
    for i, (_design, dscore, ev) in enumerate(dyn_ranked, 1):
        s_overall = struct_overall.get(dscore.design_id, 0.0)
        delta = dscore.overall - s_overall
        mint_txt = (
            f"{ev.mint_extraction:.2f}"
            if ev.mint_extraction is not None
            else "none (vacuous)"
        )
        drain_txt = (
            f"{ev.drain_fraction:.2f}"
            if ev.drain_fraction is not None
            else "none (vacuous)"
        )
        ratchet_txt = (
            f"{ev.ratchet_ratio:.2f}"
            if ev.ratchet_ratio is not None
            else "unmeasured"
        )
        lines.append(
            f"| {i} | `{dscore.design_id}` | {s_overall:.4f} | "
            f"{dscore.overall:.4f} | {delta:+.4f} | "
            f"{mint_txt} | {drain_txt} | {ratchet_txt} |"
        )
    lines.append("")

    # Rank-flip disclosure: the two orderings, compared by design_id
    struct_order = [s.design_id for _, s in ranked]
    dyn_order = [ds.design_id for _, ds, _ in dyn_ranked]
    if struct_order == dyn_order:
        lines.append(
            "Rank order is IDENTICAL under structural and dynamics-"
            "informed scoring."
        )
    else:
        flips = [
            (a, b)
            for a, b in zip(struct_order, dyn_order, strict=True)
            if a != b
        ]
        lines.append(
            f"RANK ORDER DIFFERS between the tables ({len(flips)} "
            "position(s) changed) — disclosed, never silent. "
            "Structural order: "
            + " > ".join(f"`{d}`" for d in struct_order)
            + ". Dynamics order: "
            + " > ".join(f"`{d}`" for d in dyn_order)
            + "."
        )
    lines.append("")

    # Stock scenarios (r43): the composed death-spiral dynamics —
    # §25's death-spiral question now cites measured verdicts.
    lines.append("## §17 Stock Scenarios (r43)")
    lines.append("")
    lines.append(
        "The composed supply stock: a demand process drives each "
        "design's own signal axis, rates integrate multiplicatively "
        "into supply, value = demand/supply feeds back into demand "
        "elastically (eta=0.5), and the verdict reads the quiet tail "
        "after each scenario's shock (the r20 discipline). The "
        "death-spiral question below is answered from THIS table."
    )
    lines.append("")
    lines.append(
        "| Design ID | Collapse | Crash | Mis-Mint | Organic S_T/S_0 |"
    )
    lines.append("|---|---|---|---|---|")
    for design, _score in ranked:
        d = design.driver
        cell = {}
        for sc_name in (
            "demand_collapse", "crash", "supply_shock",
            "organic_growth",
        ):
            r = run_stock_scenario(d, SCENARIOS[sc_name])
            if sc_name == "organic_growth":
                cell[sc_name] = (
                    "vacuous" if r.verdict.value == "vacuous"
                    else f"{r.supply_ratio:.3f}"
                )
            else:
                cell[sc_name] = r.verdict.value
        lines.append(
            f"| `{design.design_id}` | {cell['demand_collapse']} | "
            f"{cell['crash']} | {cell['supply_shock']} | "
            f"{cell['organic_growth']} |"
        )
    lines.append("")
    lines.append(
        "Verdicts: stable (value recovered, supply tracked) | "
        "rebased_down/up (value settled at a new level) | "
        "spiral_down/up (still diverging or bleeding under quiet) | "
        "vacuous (one-sided bounded signal index — the composition "
        "declines to map a crisis onto an undeclared domain, the "
        "r40-F1 discipline)."
    )
    lines.append("")

    # §25 questions per design
    lines.append("## §25 Question Analysis")
    lines.append("")
    for i, (design, score) in enumerate(ranked, 1):
        d = design.driver
        lines.append(f"### Design {i}: `{score.design_id}`")
        lines.append("")
        lines.append(f"**Category:** {d.category.value}")
        lines.append(f"**Signal source:** {d.signal_source}")
        offline_txt = 'yes' if d.offline_scoreable else 'NO - requires live oracle'
        lines.append(f'**Offline scoreable:** {offline_txt}')
        lines.append("")

        lines.append("**What does 1 token represent?**")
        lines.append(_answer_what_token_represents(design))
        lines.append("")

        lines.append("**Why should the token have value?**")
        lines.append(_answer_why_value(score, d))
        lines.append("")

        lines.append("**Does supply growth create dilution?**")
        lines.append(_answer_dilution_risk(score, d))
        lines.append("")

        lines.append("**Can supply reduction create a death spiral?**")
        lines.append(_answer_death_spiral(score))
        lines.append("")

        lines.append("**Can the system be gamed? / Can data be manipulated?**")
        lines.append(_answer_manipulation(d))
        lines.append("")

        lines.append("**What happens during demographic collapse?**")
        lines.append(_answer_demographic_collapse(d))
        lines.append("")

        lines.append("**What happens if data is revised or sources disagree?**")
        lines.append(_answer_data_revision(d))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Generated by code from the §17 Token Supply Mechanism Laboratory. "
        "No LLM authored any part of this report (§2). All scores are "
        "deterministic functions of the supply driver registry and the "
        "stored mechanism description.*"
    )
    lines.append("")

    return "\n".join(lines)
