"""§27 release-package assembly: code-built, evidence-only, honest.

Builds the public-release staging document for the §7 recommended
candidate from STORED EVIDENCE ONLY (§2: no report-writer LLM — every
claim in the package traces to a database record). The package exists
to support the §27 human decision: publication is a human call, and
this document hands the human the complete evidence trail — including
the residual attacks the red team found and could NOT fully close.

Structure (deterministic, same DB state → byte-identical output):
  1. Publication readiness: score, versions, simulation battery verdict
  2. The mechanism: description + core causal chain (from the record)
  3. Evidence trail: research/simulation/red-team/improvement lineage
  4. RESIDUAL ATTACKS DISCLOSURE: every attack surface the red team
     NAMED against the final model version, profitable-asserted or
     not — the §12 honesty core (r36: the agent's profitability
     assertion is rendered metadata on each line, never a filter).
     A mechanism ships WITH its residuals named, never without.
  5. Build-in-public progression: the §27 ladder with the lab's honest
     position marked (research complete; publication is the next
     HUMAN decision; no token, no deployment — §28).
"""

from __future__ import annotations

import json
from pathlib import Path

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

# §27 progression, verbatim in spirit from the master prompt.
_PROGRESSION = (
    "Idea",
    "Research",
    "Simulation",
    "Open-source publication",
    "Community criticism",
    "Prototype",
    "Testnet",
    "Developer adoption",
    "Token/mainnet consideration",
)


class ReleasePackageBuilder:
    """Assembles the §27 release package for the recommended candidate."""

    def __init__(self, database: LabDatabase) -> None:
        self.database = database

    # -- helpers -------------------------------------------------------------

    def _recommended(self) -> tuple[str, str] | None:
        candidates = self.database.list_candidates(limit=None)
        finalists = [c for c in candidates if c.status is CandidateStatus.FINALIST]
        if not finalists:
            return None
        ranked = sorted(finalists, key=lambda c: (-(c.overall_score or 0.0), c.name))
        top = ranked[0]
        return top.id, top.name

    def _select(self, candidate_id: str | None) -> tuple[str, str] | None:
        """The §27 subject: an explicit candidate, else the §7 rank-1.

        §27 publication is the HUMAN decision — the ranking's
        recommended candidate is the DEFAULT subject, not the only
        one: the human may publish any finalist. An explicit
        candidate_id is the r23 'incumbent option' path.
        """
        if candidate_id is not None:
            cand = self.database.get_candidate(candidate_id)
            if cand is None or cand.status is not CandidateStatus.FINALIST:
                return None
            return cand.id, cand.name
        return self._recommended()

    def _adversarial_bounds(self, candidate_id: str) -> str | None:
        """The latest §20 pattern-battery record for this candidate.

        Renders the MEASURED attacker edges under the four named
        choreographies, with §20 honesty: vacuous (no measurable edge)
        is reported as no-evidence, never as 'bounded by zero'; a
        measured all-nonpositive edge is a genuine measured bound.
        Returns None when no adversarial-patterns record is stored.
        """
        # r29 audit fix (round-2 F1): render from the FULLEST census
        # record, not merely the newest — the store holds BOTH the
        # r20 default battery (8 bounds) and the r22 parameter sweep
        # (27 bounds incl. all 19 calibrations), and "latest wins"
        # silently dropped the 2 pump_unwind sweep variants from §4b
        # (17 of 19 calibration lines rendered; the JSON shipped both
        # records, only the markdown was lossy). A record with MORE
        # measured bounds is the more complete disclosure; ties keep
        # the newest.
        latest = None
        latest_n = -1
        for rec in self.database.iter_experiments(candidate_id=candidate_id):
            results = rec.results
            if not (isinstance(results, dict) and "bounds" in results):
                continue
            # r48 (2026-09-20 follow-up): §4b is the §20 MECHANISM battery's
            # disclosure; it must never render the §17 supply-attack census.
            # Both carry a "bounds" list, and the census (65 rows) outranks the
            # §20 sweeps (27) under "fullest wins". The census is tagged
            # parameters.battery="supply_attack_patterns*". Legacy §20 records
            # may be untagged, so exclude only an EXPLICITLY non-mechanism
            # battery tag — an absent tag stays eligible (the r13/r14-era
            # records the r29 fixtures model carry parameters={}).
            batt = str((rec.parameters or {}).get("battery", ""))
            if batt and not batt.startswith("attack_patterns"):
                continue
            n = len(results["bounds"])
            if n >= latest_n:
                latest = results
                latest_n = n
        if latest is None:
            return None
        out: list[str] = []
        vacuous_n = int(latest.get("vacuous_count", 0))
        # r29 audit fix (round-2 F1, the REAL root cause): the dedupe
        # key was the CALIBRATION TAG ALONE — vol_oscillation and
        # pump_unwind both sweep amplitude=0.02/0.1, so whichever
        # pattern rendered first ADDED the tag and the other pattern's
        # variants were silently skipped (17 of 19 lines rendered).
        # The key must be kind+calibration: the same calibration under
        # two different patterns are two different measurements.
        seen_cals: set[str] = set()
        for b in latest.get("bounds", []):
            kind = str(b.get("kind", "?"))
            cal = b.get("calibration")
            if cal is not None:
                # sweep variants append their calibration so 27 rows
                # read as 8 defaults + N named recalibrations
                tag = f"@{cal}"
                dedupe_key = f"{kind}{tag}"
                if dedupe_key in seen_cals:
                    continue
                seen_cals.add(dedupe_key)
                kind = f"{kind} {tag}"
            vacuous = bool(b.get("vacuous"))
            headline = b.get("headline")
            regime = b.get("regime_tracking") or {}
            transient = b.get("transient_recovered") or {}
            wedges = b.get("drift_wedges") or {}
            heals = b.get("heal_flags") or {}
            if vacuous or headline is None:
                out.append(
                    f"- **{kind}**: no measurable edge (§20 vacuous — the "
                    "battery measured nothing; this is NOT a zero bound)"
                )
            elif float(headline) == 0.0:
                line = (
                    f"- **{kind}**: measured, no positive attacker edge "
                    "(the state(s) drained no further under attack than "
                    "base)"
                )
                if regime:
                    moved = ", ".join(
                        f"`{k.replace('_drawn', '')}` {v:+.1f}" for k, v in regime.items()
                    )
                    line += (
                        f" — {len(regime)} state excursion(s) were "
                        "reclassified as REGIME TRACKING (EMA states "
                        "following the moved level: the design working, "
                        "not extraction): " + moved
                    )
                if transient:
                    rec_txt = ", ".join(
                        f"`{k.replace('_drawn', '')}` recovered "
                        f"to {v:.0%} of peak" for k, v in transient.items()
                    )
                    line += (
                        f"; {len(transient)} excursion(s) reclassified "
                        "as TRANSIENT (recovered under park: the "
                        "crash's own cost, not a standing extraction): "
                        + rec_txt
                    )
                if wedges:
                    wtxt = ", ".join(
                        f"`{k.replace('_wedge', '')}` lags the drifted "
                        f"level by {v:+.1f} more than base"
                        for k, v in wedges.items()
                    )
                    line += (
                        "; drift responsiveness: " + wtxt
                        + " (design lag under a grinding regime, "
                        "disclosed; an attacker edge only where a "
                        "measured consumer response appears above)"
                    )
                transit = b.get("in_transit") or {}
                if transit:
                    ttxt = ", ".join(
                        f"`{k.replace('_drawn', '')}` re-basing "
                        f"({v:+.1f} in motion at window end)"
                        for k, v in transit.items()
                    )
                    line += (
                        "; re-basing in transit (confirmed arriving at "
                        "a doubled window, or resting at its base-run "
                        "offset from its design target): " + ttxt
                    )
                out.append(line)
            else:
                metric = b.get("headline_metric", "?")
                line = (
                    f"- **{kind}**: attacker edge **{float(headline):+.4f}** "
                    f"on `{metric}` vs a matched base run"
                )
                if regime:
                    moved = ", ".join(
                        f"`{k.replace('_drawn', '')}` {v:+.1f}" for k, v in regime.items()
                    )
                    line += (
                        f" (excludes {len(regime)} regime-tracking "
                        "excursion(s): EMA states following the moved "
                        "level — design property, not extraction: " + moved + ")"
                    )
                if transient:
                    rec_txt = ", ".join(
                        f"`{k.replace('_drawn', '')}` at {v:.0%} of peak"
                        for k, v in transient.items()
                    )
                    line += (
                        f"; excludes {len(transient)} transient "
                        "excursion(s) (recovered under park — the "
                        "crash's own cost): " + rec_txt
                    )
                if wedges:
                    wtxt = ", ".join(
                        f"`{k.replace('_wedge', '')}` {v:+.1f}"
                        for k, v in wedges.items()
                    )
                    line += (
                        "; drift responsiveness lag: " + wtxt
                        + " (disclosed design lag, not an extraction)"
                    )
                transit = b.get("in_transit") or {}
                if transit:
                    ttxt = ", ".join(
                        f"`{k.replace('_drawn', '')}` {v:+.1f}"
                        for k, v in transit.items()
                    )
                    line += (
                        "; re-basing in transit (arriving or at design "
                        "offset): " + ttxt
                    )
                out.append(line)
            if heals:
                # the r13 heal disclosure: which protection states heal
                # under park, by how much (fraction of crash-time peak)
                keyed = {k: v for k, v in heals.items() if not k.endswith("1")}
                if keyed:
                    shown = ", ".join(
                        f"`{k}` retains {v:.0%} of peak" for k, v in keyed.items()
                    )
                    out.append(
                        f"  - heal disclosure: after the one-shot move, "
                        f"protection {shown} while the level stays moved"
                    )
        if not out:
            return None
        header = "Deterministic bounds from the §20 attack-pattern battery "
        header += "(60-step window, matched base runs)."
        if vacuous_n:
            header += (
                f" {vacuous_n} of {len(latest.get('bounds', []))} patterns "
                "yielded no measurable edge — those are evidence gaps, not "
                "zero bounds (§20)."
            )
        return header + "\n" + "\n".join(out)

    def _residual_attacks(self, candidate_id: str) -> list[dict[str, object]]:
        """Attack surfaces NAMED against the LATEST model version, honestly.

        Two-layer honesty (§12, §33):
        - An attack vector from ANY red-team report is a candidate
          residual — r36: the profitable_for_attacker assertion is
          rendered metadata on each line, never a filter.
        - The §33 graph's ADDRESSES edges record what each fix CLAIMS to
          address — a claim, not a proof. So each candidate residual is
          matched against the FINAL version's claims:
          * no claim covers it → OPEN residual (never addressed);
          * a claim covers it AND the finding came from a re-attack of the
            final version (the model-wired retest) → STILL-PROFITABLE
            residual: the fix claims it; the red team re-found it anyway;
          * a claim covers it from an OLDER attack only → claimed-closed.
        The package discloses OPEN and STILL-PROFITABLE residuals; only
        claimed-closed ones are left out (they live in the dossier).
        """
        from blockchain_rd_lab.improvement.service import ImprovementService, _matches_any
        from blockchain_rd_lab.redteam import AttackVector

        model_json = self.database.get_latest_math_model(candidate_id)
        if model_json is None:
            return []
        version = int(json.loads(model_json).get("version", 1))
        svc = ImprovementService.__new__(ImprovementService)
        svc.database = self.database
        addressed = svc._addressed_attacks(candidate_id, version)
        # When the final model version was stored (deterministic re-attack
        # boundary: red-team reports created AFTER this saw the final
        # version's parameters in their prompts — §34 model-wired retest).
        versions_meta = {
            m["version"]: m["created_at"] for m in self.database.list_math_models(candidate_id)
        }
        final_stored_at = versions_meta.get(version)

        # Collect every vector occurrence first, then dedup by surface
        # taking the STRONGEST honest status (a surface claimed by v2 AND
        # re-found by the final-version re-attack is still-profitable even
        # if an older report shows the same surface as fixed-claimed).
        # r36 (the r35 principle applied to the disclosure surface): the
        # agent's profitable_for_attacker boolean does NOT filter what is
        # published — the same class as the r33 gate trust-bit and the
        # r35 suppression trigger: an agent asserting profitable=false
        # must not be able to suppress DISCLOSURE either. Every vector
        # from every report enters; the assertion is carried as
        # metadata (agent_profitability_hypothesis) rendered on the
        # line — the reader weighs it, not the code. Corpus census at
        # r36: 341 of 742 vectors (46%) assert profitable=false; every
        # one was invisible in §4 before this.
        order = {"still-profitable": 2, "open": 1, "claimed-closed": 0}
        occurrences: dict[str, dict[str, object]] = {}
        for rec in self.database.list_redteam_results(candidate_id=candidate_id):
            payload = json.loads(rec["report_json"])
            vectors = payload.get("attack_vectors", [])
            for v in vectors:
                try:
                    av = AttackVector.model_validate(v)
                except Exception:
                    continue
                key = av.vector.strip().lower()
                claimed = _matches_any(
                    {"vector": f"{av.vector}: {av.description}"}, addressed
                )
                # Did this vector come from a red team that saw the final
                # version (§34 retest re-attack, model-wired prompt)?
                report_time = rec["created_at"] or ""
                saw_final = final_stored_at is not None and report_time > final_stored_at
                status = (
                    "still-profitable"
                    if (claimed and saw_final)
                    else ("claimed-closed" if claimed else "open")
                )
                prev = occurrences.get(key)
                # Strongest status wins; on a status TIE the strongest
                # profitability assertion wins (true outranks false —
                # the more honest reading stays on the page).
                if prev is None or order[status] > order[str(prev["status"])]:
                    better = True
                elif order[status] == order[str(prev["status"])]:
                    better = av.profitable_for_attacker and not bool(
                        prev["agent_profitability_hypothesis"]
                    )
                else:
                    better = False
                if better:
                    occurrences[key] = {
                        "vector": av.vector,
                        "description": av.description,
                        "attacker": av.attacker,
                        "requires_collusion": av.requires_collusion,
                        "evidence_level": str(av.evidence_level.value)
                            if hasattr(av.evidence_level, "value")
                            else str(av.evidence_level),
                        "found_in_report": rec["agent_name"],
                        "status": status,
                        "agent_profitability_hypothesis": (
                            bool(av.profitable_for_attacker)
                        ),
                    }
        residuals = [
            o
            for o in occurrences.values()
            if o["status"] != "claimed-closed"
        ]
        return residuals

    def _simulation_verdict(self, candidate_id: str) -> dict[str, dict[str, object]]:
        """Latest battery + Monte Carlo outcomes for the evidence trail.

        §15 evidence quality: runs flagged degenerate (states pinned at
        clip bounds — every scenario indistinguishable) count as NEITHER
        clean nor failed: they are vacuous. A battery whose scenarios are
        vacuous cannot support publication, whatever its failure count.
        """
        scenarios: dict[str, object] = {}
        monte_carlo: dict[str, object] = {}
        for exp in self.database.iter_experiments(candidate_id):
            res = exp.results or {}
            if "scenarios" in exp.experiment_id:
                ok = sum(1 for r in res.values() if not r.get("failures"))
                degenerate = sum(1 for r in res.values() if r.get("degenerate"))
                total = len(res)
                scenarios = {
                    "scenarios_total": total,
                    "scenarios_clean": ok,
                    "scenarios_degenerate": degenerate,
                    "all_clean": ok == total and total > 0,
                    "vacuous": degenerate == total and total > 0,
                }
            elif "montecarlo" in exp.experiment_id:
                monte_carlo = {
                    "trials": res.get("trials", 0),
                    "failures": res.get("failures", 0),
                }
        return {"battery": scenarios, "monte_carlo": monte_carlo}

    # -- main ----------------------------------------------------------------

    def _latest_evidence_at(self, cid: str, cand: Candidate) -> str:
        """Latest stored-evidence timestamp for a candidate (r37).

        The package's 'Generated:' stamp — the store, not the wall
        clock, so the byte-determinism contract (same DB state →
        byte-identical package) holds. Falls back to the candidate's
        own creation time when no experiment/red-team/model evidence
        exists yet.
        """
        stamps: list[str] = []
        for exp in self.database.iter_experiments(cid):
            stamps.append(exp.timestamp.isoformat(timespec="seconds"))
        for r in self.database.list_redteam_results(candidate_id=cid):
            stamps.append(str(r["created_at"] or ""))
        for m in self.database.list_math_models(cid):
            stamps.append(str(m.get("created_at") or ""))
        if stamps:
            return max(s for s in stamps if s)
        return (
            cand.created_at.isoformat(timespec="seconds")
            if cand.created_at else "unknown"
        )

    def build(self, candidate_id: str | None = None) -> str | None:
        """Render the §27 release package as markdown; None if no
        finalist. An explicit candidate_id must identify a finalist;
        the human may choose which finalist, not bypass finalist status."""
        top = self._select(candidate_id)
        if top is None:
            return None
        cid, name = top
        cand = self.database.get_candidate(cid)
        assert cand is not None

        lines: list[str] = []
        lines.append(f"# Release Package: {name}")
        lines.append("")
        lines.append(
            "§27 build-in-public staging document — assembled by code from "
            "stored evidence only (§2). Publication is a HUMAN decision "
            "(§27); this package stages the evidence, it does not publish."
        )
        lines.append("")
        # r37: the byte-determinism contract ('same DB state →
        # byte-identical package', pinned by test_deterministic)
        # forbids a wall-clock stamp — two builds crossing a second
        # boundary differed. The stamp is the LATEST STORED
        # EVIDENCE timestamp for this candidate: same store → same
        # bytes, and honest provenance (when the evidence landed,
        # not when the file rendered). An empty trail renders the
        # candidate's own creation time.
        lines.append(
            f"Generated: {self._latest_evidence_at(cid, cand)}"
        )
        subject_note = (
            "§7 recommended, rank 1"
            if candidate_id is None else
            "finalist (explicit §27 subject — the human's selection, "
            "not the ranking's)"
        )
        lines.append(f"Candidate: `{cid}` ({subject_note})")
        lines.append("")

        # 1. readiness
        lines.append("## 1. Publication Readiness")
        lines.append("")
        score = cand.overall_score
        versions = [m.get("version") for m in self.database.list_math_models(cid)]
        sim = self._simulation_verdict(cid)
        lines.append(f"- Deterministic overall score: **{score}** (§19, 11 dimensions)")
        lines.append(f"- Model versions stored: {versions} (append-only, §21)")
        battery = sim.get("battery", {})
        if battery:
            if battery.get("vacuous"):
                lines.append(
                    f"- §15 battery: ⚠️ VACUOUS — {battery.get('scenarios_total')} "
                    "scenarios ran but every trajectory is degenerate "
                    "(states pinned at clip bounds; no dynamics exercised). "
                    "The battery cannot distinguish stress regimes through "
                    "this model; its 'clean' verdicts carry no evidence "
                    "(§2/§29). Re-formalize to the battery input contract."
                )
            else:
                mark = "✅" if battery.get("all_clean") else "❌"
                deg = battery.get("scenarios_degenerate", 0)
                deg_note = (
                    f" ({deg} degenerate — pinned states, no evidence)"
                    if deg
                    else ""
                )
                lines.append(
                    f"- §15 battery: {mark} {battery.get('scenarios_clean')}/"
                    f"{battery.get('scenarios_total')} scenarios clean{deg_note}"
                )
        mc = sim.get("monte_carlo", {})
        if mc:
            lines.append(
                f"- Monte Carlo: {mc.get('failures')} failures / {mc.get('trials')} trials"
            )
        lines.append("")

        # 2. the mechanism
        lines.append("## 2. The Mechanism (as recorded)")
        lines.append("")
        lines.append(f"**Problem.** {cand.problem}")
        lines.append("")
        lines.append(f"**Core causal chain.** {cand.core_mechanism}")
        lines.append("")

        # 3. evidence trail
        lines.append("## 3. Evidence Trail")
        lines.append("")
        pa = self.database.list_prior_art(cid)
        distinct = {r["finding"] for r in pa}
        lines.append(
            f"- Prior-art searches recorded: {len(distinct)} "
            f"({len(pa)} source rows; identical findings merged, §12)")
        redteam = self.database.list_redteam_results(candidate_id=cid)
        agents = sorted({r["agent_name"] for r in redteam})
        lines.append(f"- Adversarial reports: {len(redteam)} across {agents}")
        lines.append(
            "- Improvement cycle: "
            + (
                f"{len(versions) - 1} patched version(s) stored; the final "
                f"version v{max(v for v in versions if v)} was re-attacked "
                "with the patched model in the adversarial prompt (§34 retest)"
                if len(versions) > 1
                else "none (single version)"
            )
        )
        lines.append("")

        # 4. residual attacks — the honesty core
        residuals = self._residual_attacks(cid)
        lines.append("## 4. Residual Attacks Disclosure (§12 honesty)")
        lines.append("")
        if residuals:
            lines.append(
                "This list is the searched attack space, not an absolute "
                "claim about all attacks (§12)."
            )
            lines.append("")
            lines.append(
                f"The red team named **{len(residuals)} attack surface(s)** "
                "the final model version does not fully close (independent "
                "agents often converge on the same surface with different "
                "phrasings — convergence is itself evidence the surface is "
                "real). Publication means shipping the mechanism WITH "
                "these named residuals — every one is recorded here and "
                "in the dossier:"
            )
            lines.append("")
            lines.append(
                "_profitability flag = the attacking agent's own "
                "hypothesis about whether the vector pays; it is recorded "
                "metadata, never a filter — vectors asserted unprofitable "
                "are disclosed here exactly the same way (r36)._"
            )
            lines.append("")
            for r in residuals:
                collusion = " (requires collusion)" if r["requires_collusion"] else ""
                flag = (
                    "profitable-hypothesis"
                    if r["agent_profitability_hypothesis"]
                    else "unprofitable-asserted"
                )
                lines.append(
                    f"- **{r['vector']}** [{r['status']}; {r['attacker']}"
                    f"{collusion}, {r['evidence_level']}; {flag}] — "
                    f"{r['description']}"
                )
        else:
            lines.append(
                "The red team named no attack surface that remains "
                "unaddressed by the final model version. This is a "
                "statement about the searched attack space, not an "
                "absolute claim of security (§12: no absolute claims)."
            )
        # r27 audit fix #7: the model's own open questions belong IN §4,
        # where a reader looks for caveats — not only in the model JSON
        oqs: list[str] = []
        model_json = self.database.get_latest_math_model(cid)
        if model_json:
            try:
                parsed = (
                    json.loads(model_json)
                    if isinstance(model_json, str) else model_json
                )
                oqs = list(parsed.get("open_questions") or [])
            except (json.JSONDecodeError, TypeError):
                oqs = []
            if oqs:
                lines.append("")
                lines.append(
                    "The model's own recorded open questions (§13, "
                    "verbatim):"
                )
                for q in oqs:
                    lines.append(f"- OPEN QUESTION: {q}")
        lines.append("")

        # 4b. quantitative residual bounds (§20 pattern battery) — the
        # measured attacker edge against the FINAL model, from the latest
        # §21 adversarial-patterns experiment record. Claims above are
        # what the fixes ADDRESS; these numbers are what the battery
        # MEASURED under the four named choreographies.
        bounds_block = self._adversarial_bounds(cid)
        if bounds_block is not None:
            lines.append("### 4b. Measured Attack-Pattern Bounds (§20)")
            lines.append("")
            lines.append(bounds_block)
            lines.append("")

        # 5. progression
        lines.append("## 5. Build-in-Public Progression (§27)")
        lines.append("")
        lines.append("```text")
        for step in _PROGRESSION:
            if step in ("Idea", "Research", "Simulation"):
                marker = "[x]"
            elif step == "Open-source publication":
                marker = "[← HUMAN DECISION — this package]"
            else:
                marker = "[ ]"
            lines.append(f"{marker} {step}")
        lines.append("```")
        lines.append("")
        lines.append(
            "The lab is a research system (§28): no token, no contract "
            "deployment, no funds. The next step — open-source publication "
            "of this evidence package — is explicitly a human decision. "
            "Community criticism of the residual attacks above is the "
            "progression's designed next filter: publication invites the "
            "attackers to prove the residual surfaces real or bounded."
        )
        lines.append("")
        return "\n".join(lines)

    def write(
        self, reports_dir: Path, candidate_id: str | None = None,
        filename: str = "release-package-latest.md",
    ) -> Path | None:
        """Write the package to reports/release/; returns the path."""
        content = self.build(candidate_id)
        if content is None:
            return None
        out = reports_dir / "release"
        out.mkdir(parents=True, exist_ok=True)
        path = out / filename
        path.write_text(content, encoding="utf-8")
        return path
