"""Curriculum guard (§42 profile, SimSkill-inspired): anti-reward-hacking.

SimSkill (arXiv 2609.03753, §3.1) names the system-level analogue of
reward hacking: an agent can obtain repeated positive verdicts by
exploiting a narrow family of easy tasks while failing to expand real
competence. The lab's round-7 correction exposed exactly this failure
mode: a family of models (§13-convention bridge answers) repeatedly
"passed" the §15 battery with a 13/13-clean verdict that was vacuous —
the battery could not distinguish saturated trajectories, so the
family kept farming positive verdicts on non-evidence.

This module measures, deterministically, whether the candidate corpus
is degenerating into such farming. It computes a COVERAGE PROFILE over
the current gates:

  - family coverage: how many distinct §17 mechanism-family vocabularies
    the non-terminal corpus actually spans (name+description tokens,
    mapped through the combinator's family vocabulary).
  - trivial-pass concentration: the share of one family among candidates
    that scored/passed, weighted by whether the current audit says
    their evidence is real (healthy) or vacuous.

Verdict (per SimSkill's curriculum criteria — novelty, diversity, gap
coverage):
  ok            family diversity is healthy and evidence is real
  warn          one family dominates scoring (>50%) — likely farming
  degenerate    dominant family's evidence is vacuous/uninterpretable
                under today's gates — positive verdicts are non-evidence
  starving      <3 families present at all — curriculum starvation

The guard MEASURES (§2); it never mutates candidates or gates. The
pipeline/report surfaces it; the operator decides.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from blockchain_rd_lab.combinator import FAMILY_VOCAB
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

#: statuses whose verdicts the guard treats as "positive verdicts"
_RANKED_STATUSES = (CandidateStatus.SCORED, CandidateStatus.FINALIST)

#: statuses whose candidates count toward coverage (non-terminal, advanced)
_COVERAGE_STATUSES = (
    CandidateStatus.RESEARCHING,
    CandidateStatus.PRIOR_ART_CHECKED,
    CandidateStatus.FORMALIZED,
    CandidateStatus.SIMULATING,
    CandidateStatus.RED_TEAM,
    CandidateStatus.IMPROVEMENT,
    CandidateStatus.RETEST,
    CandidateStatus.SCORED,
    CandidateStatus.FINALIST,
)


class CurriculumVerdict(BaseModel):
    """The guard's deterministic assessment (evidence, §21 spirit)."""

    verdict: str = Field(pattern="^(ok|warn|degenerate|starving)$")
    families_present: int = 0
    dominant_family: str | None = None
    dominant_share: float = 0.0
    ranked_total: int = 0
    dominant_healthy: bool = True
    reasons: list[str] = Field(default_factory=list)


@dataclass
class _Tally:
    ranked_by_family: Counter[str] = field(default_factory=Counter)
    coverage_by_family: Counter[str] = field(default_factory=Counter)
    healthy_families: set[str] = field(default_factory=set)
    vacuous_families: set[str] = field(default_factory=set)
    uninterpretable_families: set[str] = field(default_factory=set)


class CurriculumGuard:
    """Deterministic anti-farming coverage profile over the corpus."""

    DOMINANCE_THRESHOLD = 0.5
    STARVATION_FLOOR = 3

    def __init__(self, database: LabDatabase, health: dict[str, str] | None = None) -> None:
        """
        `health` maps candidate_id -> 'healthy' | 'vacuous' |
        'uninterpretable' as produced by the evidence-quality audit
        (`lab audit`). When omitted, ranked candidates are assumed
        healthy unless a stored model is uninterpretable (compile
        failure) — the guard degrades gracefully without the audit map.
        """
        self.database = database
        self.health = dict(health or {})

    # -- family classification (deterministic, vocabulary-based) ------

    def family_of(self, name: str, description: str) -> str:
        """Map a candidate's text onto a §17 mechanism family label."""
        tokens = set((name + " " + description).lower().split())
        best_label = "uncategorized"
        best_hits = 0
        for label, vocab in FAMILY_VOCAB.items():
            hits = len(tokens & vocab)
            if hits > best_hits:
                best_hits = hits
                best_label = label
        return best_label if best_hits > 0 else "uncategorized"

    # -- the profile ---------------------------------------------------

    def assess(self) -> CurriculumVerdict:
        tally = _Tally()
        for cand in self.database.list_candidates(limit=None):
            fam = self.family_of(cand.name, cand.description)
            if cand.status in _COVERAGE_STATUSES:
                tally.coverage_by_family[fam] += 1
            if cand.status in _RANKED_STATUSES:
                tally.ranked_by_family[fam] += 1
                state = self.health.get(cand.id, "healthy")
                if state == "vacuous":
                    tally.vacuous_families.add(fam)
                elif state == "uninterpretable":
                    tally.uninterpretable_families.add(fam)
                else:
                    tally.healthy_families.add(fam)

        reasons: list[str] = []
        ranked_total = sum(tally.ranked_by_family.values())
        families_present = len(
            [f for f, n in tally.coverage_by_family.items() if n > 0]
        )

        if families_present < self.STARVATION_FLOOR:
            verdict = "starving"
            reasons.append(
                f"only {families_present} mechanism famil"
                f"{'y' if families_present == 1 else 'ies'} present in the "
                "non-terminal corpus — curriculum starvation (novelty gap)"
            )
            return CurriculumVerdict(
                verdict=verdict,
                families_present=families_present,
                ranked_total=ranked_total,
                reasons=reasons,
            )

        dominant_family: str | None = None
        dominant_share = 0.0
        if ranked_total:
            dominant_family, count = tally.ranked_by_family.most_common(1)[0]
            dominant_share = count / ranked_total
        else:
            reasons.append("no ranked candidates yet — coverage only")

        if dominant_family is None:
            return CurriculumVerdict(
                verdict="ok",
                families_present=families_present,
                ranked_total=0,
                reasons=reasons,
            )

        if dominant_share > self.DOMINANCE_THRESHOLD:
            bad = dominant_family in tally.vacuous_families or (
                dominant_family in tally.uninterpretable_families
                and dominant_family not in tally.healthy_families
            )
            if bad:
                verdict = "degenerate"
                reasons.append(
                    f"family '{dominant_family}' holds {dominant_share:.0%} "
                    "of ranked candidates and its evidence is "
                    "vacuous/uninterpretable under today's gates — positive "
                    "verdicts are being farmed on non-evidence "
                    "(SimSkill system-level reward-hacking analogue)"
                )
            else:
                verdict = "warn"
                reasons.append(
                    f"family '{dominant_family}' holds {dominant_share:.0%} "
                    "of ranked candidates — concentration risk; favor "
                    "novel/gap-covering discovery (curriculum criteria)"
                )
        else:
            verdict = "ok"

        return CurriculumVerdict(
            verdict=verdict,
            families_present=families_present,
            dominant_family=dominant_family,
            dominant_share=round(dominant_share, 4),
            ranked_total=ranked_total,
            dominant_healthy=dominant_family in tally.healthy_families,
            reasons=reasons,
        )
