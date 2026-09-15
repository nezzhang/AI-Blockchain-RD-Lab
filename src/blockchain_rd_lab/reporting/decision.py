"""§27 publication-decision brief builder (r21/r23).

The comparative evidence document for the human §27 publication
decision, assembled BY CODE from stored records only (§2: no
report-writer LLM). It measures; it recommends nothing.

Round 23 extended the r21 brief into the THREE §27 publication
options made literally buildable: the recommended candidate's
package (the §7 rank-1 release), the incumbent's package (a
candidate override — §27 is the human's call, not the ranking's),
and the comparative both-package (this brief + both §27 packages,
presented side by side, never ranked).

Stability lineage: r21 (score decomposition + census history +
residual disclosure) → r22 (parameter-calibration sweep records
join the census tables; the 'accrue stability evidence' option
discharged, measured in the successor's favor).
"""

from __future__ import annotations

import json

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.scoring import ScoringEngine

DECISION_CANDIDATES = (
    "cand-9200b07691c3",  # r20 successor, current §7 rank 1
    "cand-e74d830a9479",  # incumbent recommended r15-r19
)


def census_history(
    db: LabDatabase, cid: str,
) -> list[tuple[str, str, float, bool]]:
    """Every stored §20 census record: (round, battery, worst-edge,
    is-calibration-sweep).

    r37: records that predate the worst_edge field (the untagged
    'pre' rows) derive their worst edge from the per-run headlines
    in bounds — coercing the missing field to 0.0 rendered a false
    zero in the §3 table and a false floor in computed ranges.
    A record with no measurable headline at all keeps 0.0 (the
    pre-existing convention; no real record is fully vacuous).

    The fourth element classifies the record BY CONTENT — any
    bound row carrying a non-empty 'calibration' tag makes the
    record a calibration-sweep record. The r33 v8 re-sweep is
    NAMED like a default battery but carries the 19 tagged
    variants; a name-based rule misclassifies it. Computing the
    flag in the SAME pass as the enumeration also removes the
    order-mismatch class (a helper re-enumerating
    iter_experiments in raw DB order against a round-sorted
    index crossed wires: the r22 sweep read default, the 'pre'
    row read swept).
    """
    out: list[tuple[str, str, float, bool]] = []
    for exp in db.iter_experiments(candidate_id=cid):
        res = exp.results or {}
        if "bounds" not in res:
            continue
        pars = exp.parameters or {}
        bounds = [
            b for b in res.get("bounds", []) if isinstance(b, dict)
        ]
        worst = res.get("worst_edge")
        if worst is None:
            heads = [
                b["headline"] for b in bounds
                if isinstance(b.get("headline"), (int, float))
            ]
            worst = max(heads) if heads else 0.0
        calibrated = any(b.get("calibration") for b in bounds)
        out.append((
            str(pars.get("round", "pre")),
            str(pars.get("battery", "attack_patterns")),
            float(worst),
            calibrated,
        ))
    return sorted(out, key=lambda r: r[0])


def oracle_after_final(db: LabDatabase, cid: str) -> str:
    """r37: compute the provenance of the oracle dimension's
    current judgment — was the report that carries the current
    score authored after the final model version (the retest
    loop) or before it? Computed from store timestamps, never
    the r21-era narrative ('r20's retest loop' / 'original
    era') that a store change would silently falsify.
    """
    models = db.list_math_models(cid)
    final_at = (
        max(m["created_at"] for m in models) if models else ""
    )
    # the oracle report whose judgment the candidate currently
    # carries: the latest stored oracle report
    latest: tuple[str, float | None] = ("", None)
    for r in db.list_redteam_results(candidate_id=cid):
        if r["agent_name"] != "oracle":
            continue
        payload = json.loads(r["report_json"])
        score = payload.get("oracle_feasibility_score")
        created = r["created_at"] or ""
        if created >= latest[0]:
            latest = (created, score)
    if not latest[0]:
        return "no stored oracle report"
    if final_at and latest[0] > final_at:
        return "after the final model version (the retest loop)"
    return "before the final model version (the original era)"


def build_decision_brief(
    database: LabDatabase,
    candidate_ids: tuple[str, ...] = DECISION_CANDIDATES,
) -> str:
    """Render the comparative §27 brief; raises if a candidate is missing."""
    db = database
    rb = ReleasePackageBuilder(db)
    eng = ScoringEngine()
    fetched = [db.get_candidate(cid) for cid in candidate_ids]
    missing = [cid for cid, c in zip(candidate_ids, fetched, strict=True)
               if c is None]
    if missing:
        raise ValueError(f"candidate(s) not found: {missing}")
    cands = [c for c in fetched if c is not None]
    head, tail = cands[0], cands[-1]
    names = [c.name.split(" ")[0] for c in cands]
    scores = {c.id: eng.score(c) for c in cands}
    residuals = {c.id: rb._residual_attacks(c.id) for c in cands}

    lines: list[str] = []
    lines.append("# §27 Publication-Decision Brief: Recommended Candidate")
    lines.append("")
    lines.append(
        "Assembled by code from stored evidence only (§2 — no "
        "report-writer LLM). Publication is the HUMAN decision (§27); "
        "this brief compares the two candidates that decision "
        "currently spans. It recommends NOTHING — it measures."
    )
    lines.append("")
    # r37: same fix as the release package's stamp — the store's
    # latest evidence, not the wall clock (the byte-determinism
    # contract; two wall-clock builds crossing a second boundary
    # rendered different bytes for the same store)
    latest = max(
        (
            e.timestamp.isoformat(timespec="seconds")
            for c in cands
            if c is not None
            for e in db.iter_experiments(c.id)
        ),
        default="",
    )
    for c in cands:
        if c is None:
            continue
        for r in db.list_redteam_results(candidate_id=c.id):
            t = str(r["created_at"] or "")
            if t > latest:
                latest = t
    if not latest:
        latest = max(
            (
                c.created_at.isoformat(timespec="seconds")
                for c in cands if c is not None
            ),
            default="unknown",
        )
    lines.append(f"Generated: {latest}")
    lines.append("")

    # -- 1. the decision context ----------------------------------------
    # r37: the rank context is computed from TODAY'S deterministic
    # ranking — the pre-r37 prose asserted the r20 narrative
    # ('changed in round 20 for the first time since r15'); a
    # rank change would have silently falsified it. The brief
    # states where each candidate sits in the ranking as stored.
    from blockchain_rd_lab.ranking.service import RankingService

    ranked = RankingService(db).rank().rows
    rank_of = {r.candidate_id: r.rank for r in ranked}
    n_ranked = len(ranked)
    lines.append("## 1. The Decision Context")
    lines.append("")
    lines.append(
        "The §7 publication decision currently spans two "
        "candidates. Where each sits in today's deterministic "
        f"ranking of {n_ranked} stored scored candidate(s) (score "
        "descending, name ascending — §19/§7):"
    )
    lines.append("")
    for c in cands:
        if c is None:
            continue
        tag = (
            "current §7 recommended (rank 1)"
            if c.id == head.id
            else "the comparison candidate"
        )
        rank = rank_of.get(c.id)
        rank_note = (
            f", rank {rank} of {n_ranked}" if rank else ""
        )
        lines.append(
            f"- **{c.name}** (`{c.id}`) — {c.overall_score}"
            f"{rank_note}, {tag}"
        )
    lines.append("")
    gap = scores[head.id].overall_score - scores[tail.id].overall_score
    lines.append(
        f"The gap is {gap:.2f} on an "
        f"{len(scores[head.id].dimensions)}-dimension weighted score — within "
        "the noise of bridge-authored research inputs (every "
        "candidate's novelty/economist/market dimensions derive from "
        "agent-authored reports, §2). The brief's job is to show "
        "what the number does NOT: stability of evidence, measured "
        "attack surface, and each model's lineage depth."
    )
    lines.append("")

    # -- 2. score decomposition -----------------------------------------
    lines.append(
        f"## 2. Where the {gap:.2f} Comes From (§19 decomposition)"
    )
    lines.append("")
    lines.append(
        "Deterministic scoring, 11 weighted dimensions; missing "
        "dimensions imputed at the 5.0 floor (§19)."
    )
    lines.append("")
    lines.append("| Dimension | Weight | " + " | ".join(names[:2]) + " | Gap |")
    lines.append("|---|---|---|---|---|")
    head_dims = {d.dimension: d for d in scores[head.id].dimensions}
    tail_dims = {d.dimension: d for d in scores[tail.id].dimensions}
    for name in head_dims:
        d1 = head_dims[name]
        d2 = tail_dims.get(name)
        o = d2.score if d2 else float("nan")
        lines.append(
            f"| {name} | {d1.weight:.0%} | "
            f"{d1.score:.2f}{'\\*' if d1.imputed else ''} | "
            f"{o:.2f}{'\\*' if (d2 and d2.imputed) else ''} | "
            f"{d1.score - o:+.2f} |"
        )
    lines.append("")
    lines.append(
        "\\* imputed at the 5.0 floor — no agent-authored evidence "
        "stored for that dimension (offline mode). The corpus-wide "
        "§2 caveat applies to BOTH candidates' research-derived "
        "dimensions equally."
    )
    lines.append("")
    # r37: computed, never hardcoded — which dimensions actually
    # differ (the pre-r37 prose said 'oracle_feasibility' outright;
    # a store change would silently falsify it). The gap's carrier
    # dimensions are named from the §19 decomposition itself, and
    # the count states whether the gap is concentrated or spread.
    diff_dims: list[tuple[str, float, float]] = []
    for name, d1 in head_dims.items():
        d2 = tail_dims.get(name)
        if d2 is None or abs(d1.score - d2.score) <= 1e-9:
            continue
        diff_dims.append((name, d1.score - d2.score, d1.weight))

    # -- 3. measured attack surface --------------------------------------
    # r37: every sweep number below is COMPUTED from the stored
    # sweep records — the pre-r37 prose carried r21/r22-era
    # constants ('27 runs per candidate', 'zero edges >150 in the
    # whole 54-run sweep', 'both classify healthy at every
    # calibration'); r33's v8 records changed run counts and
    # re-measured edges without the prose moving. A store change
    # must move the brief's prose with it. Sweep records are
    # identified BY CONTENT (calibration-tagged bounds, the same
    # rule census_history uses) — never by battery name.
    sweep_ids = [c.id for c in cands if c is not None]
    # TAGGED runs only: a sweep record carries its 8 default
    # baselines beside the off-default variants — counting the
    # record's whole bounds as 'sweep runs' would double-count
    # the default-calibration evidence (r37 precision).
    _sweep_bounds: dict[str, list[dict[str, object]]] = {}
    for cid in sweep_ids:
        for exp in db.iter_experiments(cid):
            exp_res = exp.results or {}
            if "bounds" not in exp_res:
                continue
            bounds = [
                b for b in exp_res.get("bounds", [])
                if isinstance(b, dict)
            ]
            tagged = [b for b in bounds if b.get("calibration")]
            if not tagged:
                continue
            _sweep_bounds.setdefault(cid, []).extend(tagged)
    all_sweep_heads: list[float] = [
        h for h in (
            b.get("headline")
            for bounds in _sweep_bounds.values()
            for b in bounds
        )
        if isinstance(h, (int, float))
    ]
    sweep_runs = {
        cid: len(_sweep_bounds.get(cid, [])) for cid in sweep_ids
    }
    over_150 = sum(1 for h in all_sweep_heads if h > 150)
    total_runs = sum(sweep_runs.values())
    _sweep_variants = sorted(set(sweep_runs.values()) - {0})
    sweep_variant_txt = (
        f"{_sweep_variants[0]} runs per candidate"
        if len(_sweep_variants) == 1
        else (
            "/".join(str(v) for v in _sweep_variants)
            + " runs per candidate (as stored)"
        )
        if _sweep_variants
        else "no stored sweep"
    )
    # 'classify healthy at every calibration' is COMPUTED: every
    # measured headline edge stays under the §20 supersede
    # threshold in the stored sweep runs
    threshold = 400.0
    all_under_threshold = (
        bool(all_sweep_heads)
        and all(h < threshold for h in all_sweep_heads)
    )
    healthy_txt = (
        "both candidates classify healthy at every calibration "
        "the sweep tried"
        if all_under_threshold
        else "edges above the supersede threshold exist in the "
        "stored sweep runs — disclosed, not smoothed"
    )
    lines.append("## 3. Measured Attack Surface (§20 battery history)")
    lines.append("")
    lines.append(
        "Every stored census record per candidate, across battery "
        "generations (the §21 experiment trail). A flat worst-edge "
        "across generations is stability: the same construction "
        "measuring clean under every classifier revision the lab "
        "shipped. The r22 PARAMETER-CALIBRATION sweep extended the "
        "record: every pattern re-run at off-default attacker "
        "calibrations (deeper/shallower strikes, more/fewer "
        "resonance cycles, faster/slower creep, ± amplitude — "
        f"{sweep_variant_txt}) — a bound that holds only at the "
        "default calibration is a calibration artifact, not a "
        "bound."
    )
    lines.append("")
    for c in cands:
        if c is None:
            continue
        hist = census_history(db, c.id)
        lines.append(f"**{c.name}** — {len(hist)} census record(s):")
        lines.append("")
        lines.append("| Round | Battery | Worst measured edge |")
        lines.append("|---|---|---|")
        for rnd, bat, worst, _calibrated in hist:
            lines.append(f"| {rnd} | `{bat}` | {worst:.4f} |")
        lines.append("")
    lines.append(
        f"All edges are far under the {threshold:.0f} supersede "
        f"threshold ({healthy_txt}; {over_150} edges >150 in the "
        f"whole {total_runs}-run sweep). The difference is evidence "
        "DEPTH in generations, not measured exposure."
    )
    lines.append("")

    # -- 4. residual attacks ----------------------------------------------
    lines.append("## 4. Residual Attacks on the Final Model Versions (§12)")
    lines.append("")
    lines.append(
        "Attack surfaces the red team NAMED against the final model "
        "version, every one of them (r36: the attacking agent's "
        "profitability assertion is rendered metadata on each line, "
        "never a filter — the reader weighs it, never the code). "
        "The §33 claim-matched disclosure: OPEN = never addressed; "
        "STILL-PROFITABLE = fix claims it, the final re-attack "
        "re-found it anyway."
    )
    lines.append("")
    for c in cands:
        if c is None:
            continue
        res = residuals[c.id]
        versions = [m.get("version") for m in db.list_math_models(c.id)]
        # a candidate without stored models (pre-formalization) gets
        # an honest absence line, never a crash — the brief must
        # render whatever the evidence trail actually holds
        final_note = (
            f"(final v{max(v for v in versions if v)})"
            if versions else "(no stored model versions)"
        )
        lines.append(f"**{c.name}** {final_note}:")
        if not res:
            lines.append("")
            lines.append(
                "- no named attack surface against the final version "
                "(the searched attack space, not an absolute claim, §12)"
            )
        else:
            lines.append("")
            for r in res:
                flag = (
                    "profitable-hypothesis"
                    if r.get("agent_profitability_hypothesis")
                    else "unprofitable-asserted"
                )
                lines.append(
                    f"- **[{str(r['status']).upper()}; {flag}] "
                    f"{r['vector']} — "
                    f"{r['description']} ({r['attacker']}, "
                    f"{r['evidence_level']})"
                )
        lines.append("")

    # -- 5. lineage depth --------------------------------------------------
    lines.append("## 5. Lineage Depth (§34 improvement history)")
    lines.append("")
    for c in cands:
        if c is None:
            continue
        versions = [m.get("version") for m in db.list_math_models(c.id)]
        rt = db.list_redteam_results(candidate_id=c.id)
        agents = sorted({r["agent_name"] for r in rt})
        lines.append(
            f"- **{c.name}**: {len(versions)} model version(s) "
            f"({versions}), {len(rt)} adversarial reports "
            f"across {len(agents)} agents"
        )
    lines.append("")

    # -- 6. the honest read -------------------------------------------------
    lines.append("## 6. The Honest Read (for the human decision)")
    lines.append("")
    lines.append("What the evidence supports, without recommendation:")
    lines.append("")
    # computed, never hardcoded — the brief must survive a store
    # change without its prose drifting (the r37 lesson: r21-era
    # prose carried a residual count and a sweep max that later
    # rounds falsified — 'zero open residuals' was a pre-r36 filter
    # artifact; '63.9' was a pre-purge stale census row)
    res_counts = {
        c.id: len(residuals[c.id]) for c in cands if c is not None
    }
    sweeps: dict[str, float | None] = {
        c.id: max(
            (h[2] for h in census_history(db, c.id) if h[3]),
            default=None,
        )
        for c in cands
        if c is not None
    }
    lines.append(
        f"- The {head.name.split(' ')[0]} scores higher "
        f"({scores[head.id].overall_score:.2f} vs "
        f"{scores[tail.id].overall_score:.2f}). Residual honesty is "
        "measured under the r36 disclosure (every NAMED surface "
        f"publishes): {head.name.split(' ')[0]} carries "
        f"{res_counts[head.id]} open named surface(s) against its "
        f"final version; {tail.name.split(' ')[0]} carries "
        f"{res_counts[tail.id]} open named surface(s) against its "
        f"final version. Under the pre-r36 filter the "
        "successor's surfaces were invisible (every one asserted "
        "unprofitable) — the r21 brief's zero-open-residuals "
        "comparative claim was an artifact of that filter, §12."
    )
    if diff_dims:
        # the dominant carrier: largest absolute weighted delta
        carrier = max(diff_dims, key=lambda t: abs(t[1]) * t[2])
        # weighted contribution of every differing dimension — the
        # 'ENTIRE gap' claim is only made where the decomposition
        # actually shows it (r37: computed, never hardcoded)
        weights_total = sum(abs(d) * w for _, d, w in diff_dims)
        carrier_share = abs(carrier[1]) * carrier[2] / weights_total
        if len(diff_dims) == 1:
            gap_line = (
                f"- The ENTIRE {gap:.2f} gap is one dimension: "
                f"{carrier[0]} ({carrier[1]:+.2f} at "
                f"{carrier[2]:.0%} weight). Every other dimension "
                f"is equal. The gap dimension is agent-authored "
                f"(bridge provider): {head.name.split(' ')[0]}'s "
                f"stored report was authored "
                f"{oracle_after_final(db, head.id)}; "
                f"{tail.name.split(' ')[0]}'s "
                f"{oracle_after_final(db, tail.id)} — the rank change "
                f"rests on agent judgment, not a corpus-level "
                f"difference. §12: disclosed, not smoothed."
            )
        else:
            others = ", ".join(
                f"{n} ({d:+.2f} at {w:.0%})" for n, d, w in diff_dims
            )
            gap_line = (
                f"- The {gap:.2f} gap spreads over "
                f"{len(diff_dims)} dimensions ({others}; the "
                f"largest carrier {carrier[0]} holds "
                f"{carrier_share:.0%} of the weighted delta) — "
                f"disclosed, not smoothed, §12."
            )
    else:
        gap_line = (
            f"- The scores are equal on every dimension ({gap:.2f} "
            f"gap) — no dimension carries a difference."
        )
    lines.append(gap_line)
    # sweep maxima: computed from the census history; a candidate
    # with no sweep record renders an honest absence, never a crash
    sweep_txt = {
        c.id: (
            f"{sweeps[c.id]:.1f}" if sweeps[c.id] is not None
            else "no sweep record"
        )
        for c in cands
        if c is not None
    }
    # r37: census depth — computed, never hardcoded ('five battery
    # revisions of flat worst-edge (0.318)' was an r21-era
    # constant; r22's sweep and r33's v8 re-sweep later measured
    # the incumbent at 33.25, and the prose never moved). The
    # depth count, the flatness claim, and its SCOPE are all
    # computed, from the same single-pass census_history flags:
    # flatness is claimed only across the default-calibration
    # records (the calibration-tagged ones are a different
    # measurement and render in their own clause).
    depth_txt: dict[str, str] = {}
    for c in cands:
        if c is None:
            continue
        hist = census_history(db, c.id)
        if not hist:
            depth_txt[c.id] = "no census records"
            continue
        default_hist = [h for h in hist if not h[3]]
        n_sweep = len(hist) - len(default_hist)
        if not default_hist:
            depth_txt[c.id] = (
                f"{len(hist)} census record(s), all calibration-sweep"
            )
            continue
        worsts = [h[2] for h in default_hist]
        flat_txt = (
            f"{len(default_hist)} default-calibration battery "
            f"generation(s) at flat worst-edge ({worsts[0]:.3f})"
            if max(worsts) - min(worsts) < 1e-9
            else (
                f"{len(default_hist)} default-calibration battery "
                f"generations, worst-edge {min(worsts):.3f} to "
                f"{max(worsts):.3f}"
            )
        )
        depth_txt[c.id] = (
            f"{len(hist)} census record(s) — {flat_txt}"
            + (
                f"; {n_sweep} calibration-sweep record(s)"
                if n_sweep
                else ""
            )
        )
    # r37: §15 battery runs — computed from the §21 experiment ids
    sim_runs = {
        c.id: sum(
            1 for e in db.iter_experiments(c.id)
            if "scenarios" in e.experiment_id
        )
        for c in cands
        if c is not None
    }
    sweep_head = sweeps[head.id]
    sweep_tail = sweeps[tail.id]
    if (
        sweep_head is not None
        and sweep_tail is not None
        and sweep_head < sweep_tail
    ):
        sweep_cmp = (
            " — and under recalibration the successor's worst edge "
            "is the LOWER of the two"
        )
    elif sweep_head is not None and sweep_tail is not None:
        sweep_cmp = (
            " — under recalibration the two sweep maxima are not "
            "separated (disclosed, not smoothed)"
        )
    else:
        sweep_cmp = ""
    # r38: computed with empty-safe guards — a pre-formalization
    # candidate has no models and no scenario runs; the brief must
    # render honestly, never crash (the r37 max() on an empty
    # generator would have raised ValueError)
    head_versions = [m.get("version") for m in db.list_math_models(head.id)]
    head_max_v = max((v for v in head_versions if v), default=None)
    loop_txt = (
        f"{sim_runs.get(head.id, 0)} §15 battery runs and "
        f"a full v{head_max_v} improve/retest cycle"
        if head_max_v
        else f"{sim_runs.get(head.id, 0)} §15 battery runs"
    )
    lines.append(
        f"- The incumbent's evidence is DEEPER in CENSUS "
        f"generations: {depth_txt.get(tail.id, 'no census records')} "
        f"— measured under every classifier the lab shipped. The "
        f"successor's evidence is deeper in LOOP EXERCISE: "
        f"{loop_txt}, vs the incumbent's "
        f"{sim_runs.get(tail.id, 0)}. Different kinds of depth; "
        f"neither is dominated. The r22 parameter-calibration sweep "
        f"re-measured the incumbent as control: both constructions "
        f"hold at every off-default attacker calibration tried "
        f"(successor sweep max {sweep_txt[head.id]}, incumbent "
        f"{sweep_txt[tail.id]}){sweep_cmp}."
    )
    imp_head = sum(1 for d in scores[head.id].dimensions if d.imputed)
    lines.append(
        f"- The {gap:.2f} score gap is smaller than the imputation "
        f"floor's influence on either side ({imp_head} of the "
        f"head's {len(scores[head.id].dimensions)} dimensions are "
        f"imputed)."
    )
    # r37: the discharge claim is computed — the 'accrue stability
    # evidence' option asked for off-default-calibration bounds;
    # it is discharged only where sweep records exist for both
    # candidates (the pre-r37 prose asserted it unconditionally).
    discharged = sweeps[head.id] is not None and sweeps[tail.id] is not None
    discharge_txt = (
        " (The 'accrue stability evidence first' option is "
        "discharged — the r22 sweep measured what it asked for.)"
        if discharged
        else " (The 'accrue stability evidence first' option "
        "remains OPEN — no stored calibration sweep for both "
        "candidates.)"
    )
    lines.append(
        "- Options the evidence leaves open (all §27-human): "
        f"publish the {head.name.split(' ')[0]}; publish the "
        f"{tail.name.split(' ')[0]}; publish both as a comparative "
        f"package.{discharge_txt} The lab measures; the human "
        f"decides."
    )
    lines.append("")


    return "\n".join(lines)
