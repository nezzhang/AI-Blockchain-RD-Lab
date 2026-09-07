"""§12 prior-art record: SimSkill (arXiv 2609.03753).

Source evaluated for methodological overlap with the lab's design
(§2 verification asymmetry, §15 evidence quality, §26 archive,
§32/§33 reuse). Recorded per §12 discipline: search queries, source,
date, findings with FACT/INFERENCE/HYPOTHESIS prefixes, novelty
classification — no absolute claims.
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase

# The lab's stage this source informs (recorded against the §7
# recommended candidate — methodology-level, not candidate-specific):
TARGET_CANDIDATE = "cand-cd39d95ea572"

SOURCE_URL = "https://arxiv.org/abs/2609.03753"
SOURCE_TITLE = (
    "SimSkill: A Lifelong Learning AI Agent for Autonomous Mastery of "
    "Traffic Simulation (arXiv 2609.03753)"
)

# Queries that led to / would surface this source (§12: record queries).
FINDINGS = [
    (
        "self-evolving LLM agent simulation verification memory",
        "FACT: SimSkill's stated conceptual foundation 'verification "
        "asymmetry' — constructing a valid solution is open-ended while "
        "evaluating a candidate decomposes into simpler checks — is the "
        "academic formulation of this lab's §2 prime directive "
        "(LLM proposes. Code tests. Evidence decides.). The paper's "
        "artifact-based independent critic and its requirement that "
        "reports correspond to executed artifacts mirror the lab's "
        "deterministic gates and claim-based §33 ADDRESSES edges.",
    ),
    (
        "LLM proposes code tests evidence decides agent design",
        "FACT: SimSkill's experience-consolidation policy states that a "
        "failed task may still update memory with a discovered "
        "limitation while a successful task that repeats known "
        "procedures need not — the same epistemic stance as the lab's "
        "§26 archive (failed experiments as a research asset) and the "
        "round-7 correction (success-shaped non-evidence — the vacuous "
        "13/13 'clean' battery — was identified and purged rather than "
        "counted).",
    ),
    (
        "verification asymmetry LLM agent artifact evaluation",
        "FACT: SimSkill reports backbone-dependent gains (improvements "
        "for DeepSeek-V4-Pro and Qwen3.7-Max; none for GLM-5.2) and "
        "honest accuracy-cost trade-offs (median inference cost ROSE "
        "59-78% for its biggest winner; memory does not uniformly reduce "
        "cost). The paper itself demonstrates the failure mode of "
        "natural-language control logic: a weaker orchestrator "
        "sometimes accepted a polished success report as completion, "
        "skipping critic evaluation and memory ingestion.",
    ),
    (
        "self-evolving agent memory taxonomy episodic procedural semantic",
        "INFERENCE: SimSkill's architecture (natural-language system "
        "skills as control flow, ~80h autonomous operation, episodic/"
        "procedural/semantic memory over the SUMO simulator) is "
        "methodologically ADJACENT to this lab (same verification "
        "philosophy; different substrate: the lab keeps all control "
        "logic in deterministic Python/Pydantic so its evidence is "
        "reproducible by construction, and its 'memory' is the §21 "
        "append-only database + §33 derived graph, not LLM-retrieved "
        "text). The lab should adopt SimSkill's CONCEPTS — memory "
        "taxonomy, anti-reward-hacking curriculum guard, verification-"
        "asymmetry citation — not its architecture.",
    ),
    (
        "curriculum novelty coverage anti reward hacking agent",
        "HYPOTHESIS: a curriculum-style novelty/coverage guard over the "
        "lab's discovery+combinator stages (penalizing candidate "
        "families the current gates pass trivially, per SimSkill's "
        "system-level reward-hacking analogue) would reduce recurrence "
        "of degenerate-evidence candidates like the round-7 vacuum. "
        "Not yet implemented or measured.",
    ),
]

# Novelty impact: methodology source, not a competing mechanism —
# the lab's MECHANISMS remain unchallenged by it; the overlap is in
# epistemics. Class C (adjacent_mechanism) records this honestly.
SIMILARITY_CLASS = "adjacent_mechanism"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    sid = db.save_source(SOURCE_TITLE, SOURCE_URL, source_type="arxiv")
    for query, finding in FINDINGS:
        db.save_prior_art(
            candidate_id=TARGET_CANDIDATE,
            query=query,
            finding=finding,
            similarity_class=SIMILARITY_CLASS,
            source_id=sid,
        )
    rows = db.list_prior_art(candidate_id=TARGET_CANDIDATE)
    print(f"source id {sid}: {SOURCE_URL}")
    print(f"{len(rows)} prior-art rows recorded for {TARGET_CANDIDATE}")


if __name__ == "__main__":
    main()
