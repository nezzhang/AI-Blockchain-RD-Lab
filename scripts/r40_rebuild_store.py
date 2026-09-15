"""r40: rebuild the corpus store from committed artifacts (Option 2).

CONTEXT (§35: the database is the checkpoint; the checkpoint was lost):
`database/lab.db` was emptied at 2026-09-15 19:24 while the venv was
being rebuilt under Python 3.14 (Homebrew upgrade). The store was never
git-tracked (operator session state, §41); the bridge cache
`.bridge/` was likewise empty. Time Machine holds a backup but reads
require Full Disk Access that this session does not have (Option 1,
blocked — manual `tmutil` restore remains available to the operator).

This script rebuilds the store from artifacts that ARE committed and
verified, pinning ORIGINAL candidate ids wherever they are recorded,
so every cross-reference (bundle candidate_id, §21 records, lineage
chains) resolves again.

SOURCES (all git-committed):
  1. reports/lab-latest.md          — post-r20 funnel: 100 candidates,
                                      statuses, the full 26-row ranking
                                      table (ids, names, overall scores)
  2. reports/graph-latest.json      — 96 idea nodes (id, name, category,
                                      status) — corpus-wide lineage
  3. scripts/r*_mint.py             — structured candidate content
                                      (description, problem, mechanism,
                                      lineage) for every scripted round
  4. reports/finalists/*.md         — §23 dossiers: the 11 dimension
                                      sub-scores per ranked candidate
                                      (verified: they reproduce the
                                      published 6.45/6.40 ranking
                                      bit-exactly under config/scoring.yaml)
  5. bundle adversarial-bounds.json — the published battery headlines
                                      (the verification baseline this
                                      rebuild must reproduce)
  6. bundle model-v3.json           — the successor's final MathModel

WHAT IS HONESTLY NOT REBUILDABLE (disclosed, not hidden):
  - the 82 pre-r7 discovery candidates' full descriptions (graph nodes
    carry id/name/category/status only) — they enter as lineage rows
    with empty descriptions (the curriculum guard classifies families
    from name tokens in that case);
  - per-experiment §21 records for historical rounds (their content
    lives in the dossiers' prose and the bundle; the two decision
    candidates get FRESH re-measured evidence via scripts/r33's
    battery pattern, verified against the published headlines);
  - the r1-r9 bridge request/answer pairs (.bridge/ was session state).

VERIFICATION STANDARD (the r33 pattern): after the rebuild, the
deterministic §20 battery re-measures both decision candidates and
the headlines are compared against the PUBLISHED bundle JSON — the
rebuilt store must reproduce the published numbers from the rebuilt
models alone. Ranking must reproduce the published 26-row order.

Idempotent: re-running skips already-present candidates/models.

Run: .venv/bin/python scripts/r40_rebuild_store.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from blockchain_rd_lab.config import REPO_ROOT, load_config  # noqa: E402
from blockchain_rd_lab.database import LabDatabase  # noqa: E402
from blockchain_rd_lab.schemas import (  # noqa: E402
    Candidate,
    CandidateStatus,
    ScoreBreakdown,
)

# ----------------------------------------------------------------------
# 1. The published ranking (authoritative, post-r20)
# ----------------------------------------------------------------------

RANKING_RE = re.compile(
    r"\| (\d+) \| (cand-[0-9a-f]{12}) \| (.+?) \| ([\d.]+) \|"
)
FUNNEL_RE = re.compile(r"- \*\*(\w+):\*\* (\d+)")

DIM_LINE_RE = re.compile(
    r"^- \*\*([a-z_]+)\*\*: ([\d.]+) \((FACT|INFERENCE|HYPOTHESIS)"
    r"(?:; confidence ([\d.]+))?\)"
)

#: statuses in the funnel report -> CandidateStatus values
_STATUS_MAP = {
    "failed": CandidateStatus.FAILED,
    "rejected": CandidateStatus.REJECTED,
    "superseded": CandidateStatus.SUPERSEDED,
    "scored": CandidateStatus.SCORED,
    "finalist": CandidateStatus.FINALIST,
}


def _read_ranking() -> list[tuple[str, str, float]]:
    text = (REPO / "reports" / "lab-latest.md").read_text()
    rows = []
    for m in RANKING_RE.finditer(text):
        rows.append((m.group(2), m.group(3).strip(), float(m.group(4))))
    return rows


def _read_funnel() -> dict[str, int]:
    text = (REPO / "reports" / "lab-latest.md").read_text()
    return {m.group(1): int(m.group(2)) for m in FUNNEL_RE.finditer(text)}


def _read_graph_ideas() -> list[dict]:
    g = json.loads((REPO / "reports" / "graph-latest.json").read_text())
    return [n for n in g["nodes"] if n["kind"] == "idea"]


def _read_dossier_dims(cid: str) -> dict[str, ScoreBreakdown]:
    """Authored (non-imputed) dimension sub-scores from a §23 dossier."""
    path = REPO / "reports" / "finalists" / f"{cid}.md"
    if not path.exists():
        return {}
    dims: dict[str, ScoreBreakdown] = {}
    in_model_section = False
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            in_model_section = line in (
                "## Economic Analysis",
                "## Game Theory",
                "## Security Analysis",
                "## Oracle Analysis",
                "## Market",
            )
            continue
        if not in_model_section:
            continue
        m = DIM_LINE_RE.match(line)
        if m:
            dims[m.group(1)] = ScoreBreakdown(
                dimension=m.group(1),
                score=float(m.group(2)),
                evidence_level=m.group(3),
                confidence=float(m.group(4) or 1.0),
            )
    return dims


# ----------------------------------------------------------------------
# 2. Mint-script content extraction (structured, verbatim)
# ----------------------------------------------------------------------

MINT_FILES = [
    "scripts/r7_mint.py",
    "scripts/r8_answer_batch0.py",
    "scripts/r8_answer_batch1.py",
    "scripts/r8_answer_batch2.py",
    "scripts/r9_answer_batch0.py",
    "scripts/r9_answer_batch1.py",
    "scripts/r11_mint.py",
    "scripts/r12_mint.py",
    "scripts/r13_mint.py",
    "scripts/r15_mint.py",
    "scripts/r16_mint.py",
    "scripts/r18_mint.py",
    "scripts/r19_mint.py",
    "scripts/r20_mint.py",
]


def _mint_content() -> dict[str, dict]:
    """name -> {category, description, problem, core_mechanism, ...}.

    AST-parses the mint scripts' Candidate(...) constructor calls and
    SUCCESSORS dict literals — deterministic extraction, no regex
    fragility. Joined string constants (implicit concatenation across
    lines) are handled by flattening JoinedStr/binop-add of constants.
    """
    import ast

    def lit(node: ast.AST) -> object:
        """Best-effort literal evaluation (str/list/dict/bool only)."""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                # FormattedValue (computed interpolation) -> not a
                # static literal; the field is skipped by the caller
                if not isinstance(v, ast.Constant):
                    return None
                parts.append(v.value)
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = lit(node.left), lit(node.right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            return None
        if isinstance(node, ast.List):
            vals = [lit(e) for e in node.elts]
            return None if any(v is None for v in vals) else vals
        if isinstance(node, ast.Dict):
            out = {}
            for k, v in zip(node.keys, node.values, strict=False):
                if k is None:
                    continue
                lk, lv = lit(k), lit(v)
                if lk is None or lv is None:
                    continue
                out[lk] = lv
            return out
        return None

    content: dict[str, dict] = {}
    fields = (
        "category",
        "description",
        "problem",
        "core_mechanism",
        "innovation_claim",
        "inputs",
        "outputs",
    )
    for rel in MINT_FILES:
        path = REPO / rel
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        # local constant assignments (name = "...", desc = (...), ...)
        locals_map: dict[str, object] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                v = lit(node.value)
                if v is not None:
                    locals_map[node.targets[0].id] = v

        def resolve(node: ast.AST, _lm=locals_map) -> object:
            """Literal or resolvable local-variable reference."""
            if isinstance(node, ast.Name) and node.id in _lm:
                return _lm[node.id]
            return lit(node)

        for node in ast.walk(tree):
            entries: list[dict] = []
            # shape A: any kw call whose first kw is a literal name and
            # which carries category+description-ish kwargs — covers
            # both Candidate(name=...) and _mint(name=..., desc=...)
            if isinstance(node, ast.Call):
                kw: dict[str, object] = {}
                for k in node.keywords:
                    if k.arg is None:
                        continue
                    v = resolve(k.value)
                    if v is not None:
                        kw[k.arg] = v
                nm = kw.get("name")
                if isinstance(nm, str) and (
                    isinstance(kw.get("category"), str)
                    and (
                        isinstance(kw.get("description"), str)
                        or isinstance(kw.get("desc"), str)
                    )
                ):
                    if "desc" in kw and "description" not in kw:
                        kw["description"] = kw.pop("desc")
                    entries.append(kw)
            # shape B: top-level list-of-dicts whose elements carry
            # name+category+description — SUCCESSORS/IDEAS/CANDS/MINTS
            # (AnnAssign or plain Assign)
            elif (
                (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                )
                or (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                )
            ) and isinstance(node.value, ast.List):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Dict):
                        d = {
                            lit(k): lit(v)
                            for k, v in zip(elt.keys, elt.values, strict=False)
                            if k is not None
                        }
                        # lenient collection: name + description; the
                        # category/mechanism fallbacks live below in
                        # the entry loop (r13 SPECS carries category
                        # only at the mint call site)
                        if (
                            isinstance(d.get("name"), str)
                            and isinstance(d.get("description"), str)
                        ):
                            entries.append(d)
            for kw in entries:
                entry = {
                    f: kw[f] for f in fields if isinstance(kw.get(f), str)
                }
                # r13's SPECS shape: "mechanism" instead of
                # "core_mechanism"; category inherited at mint time
                if "core_mechanism" not in entry and isinstance(
                    kw.get("mechanism"), str
                ):
                    entry["core_mechanism"] = kw["mechanism"]
                # r18's _mint shape: mech/problem-shorthand kwargs
                if "core_mechanism" not in entry and isinstance(
                    kw.get("mech"), str
                ):
                    entry["core_mechanism"] = kw["mech"]
                if "problem" not in entry and isinstance(
                    kw.get("problem"), str
                ):
                    entry["problem"] = kw["problem"]
                if "category" not in entry and isinstance(
                    kw.get("domain"), str
                ):
                    entry["category"] = kw["domain"]
                # r13's SPECS shape: category is a constant at the
                # mint call site ("oracle design") — both its entries
                # are oracle-design successors; disclosed here rather
                # than silently dropped
                if "category" not in entry and isinstance(
                    kw.get("pred"), str
                ):
                    entry["category"] = "oracle design"
                # core_mechanism floor: the description carries the
                # mechanism intent for discovery-artifact rows
                if not entry.get("core_mechanism") and entry.get(
                    "description"
                ):
                    entry["core_mechanism"] = entry["description"]
                if entry.get("description") and entry.get("category"):
                    name = kw.get("name")
                    if isinstance(name, str):
                        content.setdefault(name, entry)
    return content


def _idea_artifact_content() -> dict[str, dict]:
    """Discovery-run JSON artifacts: stored_ideas carry the full
    description/category (the r5-r9 discovery generation)."""
    content: dict[str, dict] = {}
    for path in sorted((REPO / "ideas").glob("*/discovery-run-*.json")):
        try:
            d = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for idea in d.get("stored_ideas", []):
            name = idea.get("name")
            desc = idea.get("description", "")
            if isinstance(name, str) and isinstance(desc, str) and desc:
                content[name] = {
                    "category": idea.get("category", "uncategorized"),
                    "description": desc,
                    "problem": "",
                    "core_mechanism": "",
                }
    return content

#: decision candidates: original ids are pinned everywhere; their final
#: models + evidence come from the bundle and the r9/r20 model scripts.
SUCCESSOR = "cand-9200b07691c3"
INCUMBENT = "cand-e74d830a9479"


def rebuild_candidates(db: LabDatabase) -> dict[str, str]:
    """Restore corpus rows. Returns name->cid map for the ranked set."""
    ranking = _read_ranking()
    funnel = _read_funnel()
    graph = _read_graph_ideas()
    mint = _mint_content()
    # discovery artifacts supplement: names absent from mint scripts
    # (the discovery-run generation) gain their committed descriptions
    mint.update(
        {k: v for k, v in _idea_artifact_content().items() if k not in mint}
    )
    existing = {c.id for c in db.list_candidates(limit=None)}

    # (a) the ranked decision corpus — pinned ids, dossier dimensions
    name_to_cid: dict[str, str] = {}
    for cid, name, overall in ranking:
        name_to_cid[name] = cid
        if cid in existing:
            continue
        entry = mint.get(name, {})
        status = (
            CandidateStatus.FINALIST
            if name in _finalist_names()
            else CandidateStatus.SCORED
        )
        cand = Candidate(
            id=cid,
            name=name,
            category=entry.get("category", "uncategorized"),
            description=entry.get("description", ""),
            problem=entry.get("problem", ""),
            core_mechanism=entry.get("core_mechanism")
            or entry.get("description", "")
            or "(r40 rebuild) not recoverable",
            innovation_claim=entry.get("innovation_claim", ""),
            inputs=[],
            outputs=[],
            source_agent="rebuild-r40",
        )
        cand.status = status
        cand.overall_score = overall
        for dim, bd in _read_dossier_dims(cid).items():
            cand.scores[dim] = bd
        db.save_candidate(cand)
        print(f"  ranked {cid} {name[:44]} <- {status.value} {overall}")
        existing.add(cid)

    # (b) corpus-wide lineage from the graph (96 ideas, statuses pinned;
    #     descriptions honestly unavailable — placeholder, disclosed).
    #     The graph snapshot predates the r16-r20 supersede waves, so a
    #     graph finalist/scored row NOT in the report's ranked set was
    #     superseded after the snapshot — the report funnel (10 finalist
    #     + 16 scored) is the authoritative final state.
    ranked_ids = {cid for cid, _, _ in ranking}
    for node in graph:
        cid = node["id"]
        if cid in existing:
            continue
        meta = node["meta"]
        status = _STATUS_MAP.get(meta.get("status", "superseded"))
        if status is None:
            continue
        if (
            status in (CandidateStatus.SCORED, CandidateStatus.FINALIST)
            and cid not in ranked_ids
        ):
            # e.g. cand-cd39d95ea572 and cand-1acbaa9de0b0: FINALIST in
            # the graph, SUPERSEDED by scripts/r20_supersede.py after it
            status = CandidateStatus.SUPERSEDED
        cand = Candidate(
            id=cid,
            name=node["label"],
            category=meta.get("category", "uncategorized"),
            # honest disclosure, not reconstructed content: the pre-r7
            # discovery corpus' full text lived only in the lost store;
            # this row preserves id/name/category/status lineage. The
            # family classifier falls back to name tokens.
            description=(
                "(r40 rebuild) lineage row: original description lived "
                "only in the lost store; id/name/category/status "
                "restored from reports/graph-latest.json."
            ),
            core_mechanism="(r40 rebuild) not recoverable",
            source_agent="rebuild-r40",
        )
        cand.status = status
        db.save_candidate(cand)
        existing.add(cid)
    print(
        f"  lineage: {len(existing)} candidates present "
        f"(funnel target: {funnel.get('Total', '?')})"
    )
    return name_to_cid


def _finalist_names() -> set[str]:
    """The §7 finalist names — the ranking table plus the report's
    Finalists section (a finalist is a ranked candidate the §7 cut
    selected; statuses must match the published funnel)."""
    text = (REPO / "reports" / "lab-latest.md").read_text()
    m = re.search(r"## Finalists\n\n([^\n]+)", text)
    if not m:
        return set()
    finalist_ids = set(re.findall(r"cand-[0-9a-f]{12}", m.group(1)))
    names = set()
    for cid, name, _score in _read_ranking():
        if cid in finalist_ids:
            names.add(name)
    return names


def rebuild_models(db: LabDatabase, name_to_cid: dict[str, str]) -> None:
    """Final MathModels for the decision candidates.

    Successor: bundle model-v3.json (the authoritative published final).
    Incumbent: r9 v1 builder + the v2 refund-cap patch (its final
    stored version — verified against its dossier's equations).
    """
    existing = {c.id for c in db.list_candidates(limit=None)}

    # -- successor v3 from the bundle --------------------------------
    bundle_model = (
        REPO / "reports" / "release" / f"bundle-{SUCCESSOR}"
        / "model-v3.json"
    )
    if (
        SUCCESSOR in existing
        and bundle_model.exists()
        and not db.list_math_models(SUCCESSOR)
    ):
            db.save_math_model(
                candidate_id=SUCCESSOR,
                model_json=json.dumps(
                    json.loads(bundle_model.read_text()), indent=2
                ),
                rationale="r40 rebuild: bundle model-v3.json (published final)",
                version=3,
            )
            print(f"  model {SUCCESSOR} v3 <- bundle")

    # -- incumbent: v1 (r9 builder) then v2 (refund-cap patch) -------
    if INCUMBENT in existing:
        from r9_answer_improve import ladder_v2
        from r9_models import demand_ladder

        if not db.list_math_models(INCUMBENT):
            v1 = demand_ladder(INCUMBENT)
            db.save_math_model(
                candidate_id=INCUMBENT,
                model_json=json.dumps(v1.model_dump(mode="json"), indent=2),
                rationale=v1.rationale,
                version=1,
            )
            print(f"  model {INCUMBENT} v1 <- r9 builder")
        if len(db.list_math_models(INCUMBENT)) < 2:
            v2 = ladder_v2(INCUMBENT)
            mm = json.dumps(v2, indent=2)
            db.save_math_model(
                candidate_id=INCUMBENT,
                model_json=mm,
                rationale=v2.get("rationale", ""),
                version=2,
            )
            print(f"  model {INCUMBENT} v2 <- r9 v2 patch")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    db.create_all()
    print("== rebuilding candidates ==")
    name_to_cid = rebuild_candidates(db)
    print("== rebuilding models ==")
    rebuild_models(db, name_to_cid)
    print("== done ==")
    counts: dict[str, int] = {}
    for c in db.list_candidates(limit=None):
        counts[c.status.value] = counts.get(c.status.value, 0) + 1
    print("status counts:", dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
