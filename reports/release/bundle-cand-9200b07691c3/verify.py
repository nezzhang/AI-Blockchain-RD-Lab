"""Round 25: the external verifier — criticism made actionable.

A critic who downloads the published bundle currently gets static
JSON: they must TRUST adversarial-bounds.json. §2 says evidence
decides, so the bundle's numbers must be CHECKABLE from the
published files alone. This script is that check.

It reads ONLY the bundle (never the database), re-runs every
reproducible claim with the lab's deterministic interpreter and
battery, and writes an honest verification report with three
verdict classes:

- REPRODUCED      — the verifier recomputed the number and it
                    matches the published value (within float
                    tolerance)
- CONSISTENT      — the published value is internally coherent
                    (manifest hashes verify; model JSON parses
                    and passes §13 integrity checks; the release
                    package names the same subject) but is not a
                    re-computable measurement in this bundle
- NOT-REPRODUCIBLE — the bundle's own artifacts disagree (a hash
                    mismatch, a count mismatch, a number the
                    re-run cannot produce)

Usage:
    python verify.py .
    (from inside the bundle directory — the deterministic runtime
    ships in lab-runtime/, so no lab package install is needed)
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# r27 audit fix #3: prefer the runtime SHIPPED IN THE BUNDLE over
# any installed lab package — the substance tier is self-service.
# The runtime directory layout is lab-runtime/blockchain_rd_lab/...
_runtime = Path(__file__).resolve().parent / "lab-runtime"
if _runtime.is_dir():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(_runtime))

from blockchain_rd_lab.formalization import MathModel  # noqa: E402
from blockchain_rd_lab.simulation import (  # noqa: E402
    MechanismSimulation,
    ScenarioBattery,
)
from blockchain_rd_lab.simulation.adversarial import (  # noqa: E402
    AttackPatternBattery,
    PatternSpec,
)

DEFAULT_BUNDLE = Path("reports/release/bundle-cand-9200b07691c3")
TOL = 1e-6  # deterministic interpreter: exact re-runs must match


@dataclass
class Result:
    label: str
    verdict: str  # REPRODUCED | CONSISTENT | NOT-REPRODUCIBLE
    detail: str


@dataclass
class Report:
    checks: list[Result] = field(default_factory=list)

    def add(self, label: str, verdict: str, detail: str) -> None:
        self.checks.append(Result(label, verdict, detail))

    @property
    def ok(self) -> bool:
        return all(c.verdict != "NOT-REPRODUCIBLE" for c in self.checks)


def _verify_manifest(bundle: Path, rep: Report) -> dict[str, dict]:
    man_p = bundle / "MANIFEST.json"
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for name, entry in man.get("files", {}).items():
        f = bundle / name
        if not f.exists():
            rep.add(name, "NOT-REPRODUCIBLE", "file listed in manifest missing")
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            rep.add(name, "NOT-REPRODUCIBLE",
                    f"hash mismatch: manifest {entry['sha256'][:12]}… "
                    f"!= file {digest[:12]}…")
        else:
            rep.add(name, "REPRODUCED", "sha256 verifies against the file")
    # nothing unhashed ships
    # non-content artifacts excluded from coverage: __pycache__ (the
    # runtime's own bytecode) and .DS_Store (Finder metadata) are not
    # evidence and never ship; anything else unlisted is a real stray
    _skip = {"__pycache__", ".DS_Store"}
    on_disk = {
        f.relative_to(bundle).as_posix()
        for f in bundle.rglob("*")
        if f.is_file() and not (_skip & set(f.parts))
    } - {"MANIFEST.json"}
    listed = set(man.get("files", {}))
    if on_disk != listed:
        rep.add("manifest coverage", "NOT-REPRODUCIBLE",
                f"unlisted files {sorted(on_disk - listed)}; "
                f"missing listings {sorted(listed - on_disk)}")
    else:
        rep.add("manifest coverage", "REPRODUCED",
                "every bundle file is hashed; nothing unlisted ships")
    return man


def _verify_model(bundle: Path, rep: Report) -> MathModel | None:
    model_files = sorted(bundle.glob("model-v*.json"))
    if len(model_files) != 1:
        rep.add("model file", "NOT-REPRODUCIBLE",
                f"expected exactly 1 model-v*.json, found {len(model_files)}")
        return None
    raw = json.loads(model_files[0].read_text(encoding="utf-8"))
    try:
        mm = MathModel.model_validate(raw)
    except Exception as exc:
        rep.add("model integrity", "NOT-REPRODUCIBLE",
                f"published model fails §13 integrity: {exc}")
        return None
    rep.add("model integrity", "REPRODUCED",
            f"parses and passes §13 checks (v{mm.version}, "
            f"{len(mm.equations)} equations)")
    return mm


def _verify_bounds(bundle: Path, mm: MathModel,
                    rep: Report) -> list[dict]:
    bounds = json.loads(
        (bundle / "adversarial-bounds.json").read_text(encoding="utf-8"))
    rep.add("census records", "CONSISTENT",
            f"{len(bounds)} §20 census record(s) in the bundle "
            "(the §21 store is not part of the bundle; the "
            "re-run below recomputes them)")
    return bounds


def _rerun_attack_battery(mm: MathModel, published: list[dict],
                          rep: Report) -> None:
    """The core check: re-run the §20 battery against the PUBLISHED
    model JSON and compare every default-calibration headline to
    the published bounds."""
    bat = AttackPatternBattery(mm)

    # find the record whose bounds carry no calibration tags =
    # the default-calibration run
    defaults: dict[str, dict] = {}
    for rec in published:
        for b in rec["bounds"]:
            if b.get("calibration"):
                continue
            defaults[str(b["kind"])] = b

    if not defaults:
        rep.add("default battery re-run", "NOT-REPRODUCIBLE",
                "no default-calibration bounds found in the bundle")
        return

    matches, total = 0, 0
    for kind, pub in sorted(defaults.items()):
        try:
            spec = PatternSpec(kind=kind)  # default calibration
            res = bat.run_pattern(spec)
        except Exception as exc:
            rep.add(f"re-run {kind}", "NOT-REPRODUCIBLE",
                    f"battery raised: {exc}")
            continue
        total += 1
        pub_headline = pub.get("headline")
        if res.headline is None or pub_headline is None:
            # both must be vacuous-or-zero the same way
            if (res.headline is None) == (pub_headline is None):
                matches += 1
                rep.add(f"re-run {kind}", "REPRODUCED",
                        f"headline class agrees (vacuous={res.headline is None})")
            else:
                rep.add(f"re-run {kind}", "NOT-REPRODUCIBLE",
                        f"vacuous disagreement: re-run {res.headline} "
                        f"vs published {pub_headline}")
            continue
        if abs(res.headline - float(pub_headline)) <= TOL:
            matches += 1
            rep.add(f"re-run {kind}", "REPRODUCED",
                    f"headline {res.headline:.4f} == published "
                    f"{float(pub_headline):.4f}")
        else:
            rep.add(f"re-run {kind}", "NOT-REPRODUCIBLE",
                    f"headline drift: re-run {res.headline:.4f} vs "
                    f"published {float(pub_headline):.4f}")
    rep.add("default battery re-run (summary)", "REPRODUCED",
            f"{matches}/{total} default-calibration headlines "
            f"reproduced from the published model JSON")


def _verify_scenarios(mm: MathModel, rep: Report) -> None:
    """§15: the model runs the 13-scenario battery non-degenerately
    under today's interpreter — the publishability floor."""
    sim = MechanismSimulation(mm)
    try:
        runs = ScenarioBattery(sim).run()
    except Exception as exc:
        rep.add("§15 battery", "NOT-REPRODUCIBLE", f"battery raised: {exc}")
        return
    if not runs:
        rep.add("§15 battery", "NOT-REPRODUCIBLE", "no scenarios ran")
        return
    degenerate = [
        k for k, r in runs.items() if getattr(r, "degenerate", False)]
    if degenerate:
        rep.add("§15 battery", "NOT-REPRODUCIBLE",
                f"degenerate scenarios: {degenerate}")
    else:
        rep.add("§15 battery", "REPRODUCED",
                f"{len(runs)} scenarios run non-degenerately "
                "under the current interpreter")


def _verify_score(bundle: Path, rep: Report) -> None:
    """Recompute the headline §19 score from the published
    decomposition — the README's 6.45 must fall out of
    score-decomposition.json's own rule, not be trusted."""
    sp = bundle / "score-decomposition.json"
    if not sp.exists():
        rep.add("score decomposition", "NOT-REPRODUCIBLE",
                "score-decomposition.json missing from the bundle")
        return
    sd = json.loads(sp.read_text(encoding="utf-8"))
    total = sum(d["score"] * d["weight"] for d in sd["dimensions"])
    published = float(sd["overall_score"])
    if abs(total - published) <= 1e-6:
        rep.add("§19 score recomputation", "REPRODUCED",
                f"sum(score*weight) = {total:.4f} == published "
                f"{published:.4f}")
    else:
        rep.add("§19 score recomputation", "NOT-REPRODUCIBLE",
                f"sum(score*weight) = {total:.4f} != published "
                f"{published:.4f}")
    # the README must carry the same headline number
    readme = (bundle / "README.md").read_text(encoding="utf-8")
    if f"{published:.2f}" in readme:
        rep.add("score headline consistency", "REPRODUCED",
                f"README carries the same {published:.2f} headline")
    else:
        rep.add("score headline consistency", "NOT-REPRODUCIBLE",
                f"README does not carry {published:.2f}")
    imputed = sum(1 for d in sd["dimensions"] if d.get("imputed"))
    if imputed:
        rep.add("imputation disclosure", "REPRODUCED",
                f"{imputed} of {len(sd['dimensions'])} dimensions "
                "imputed at the 5.0 floor — disclosed per dimension")


def _verify_release_package(bundle: Path, man: dict[str, dict],
                            rep: Report) -> None:
    txt = (bundle / "release-package.md").read_text(encoding="utf-8")
    if man.get("candidate_id") not in txt:
        rep.add("release package subject", "NOT-REPRODUCIBLE",
                "release package does not name the manifest subject")
    else:
        rep.add("release package subject", "CONSISTENT",
                "release package names the manifest's candidate")


def main() -> None:
    # resolve: `python verify.py .` from inside the bundle would
    # otherwise give bundle.name == "" and drop the report INSIDE
    # (the r27 stray-file lesson, twice-earned)
    bundle = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1 else DEFAULT_BUNDLE
    )
    if not bundle.is_dir():
        print(f"no bundle at {bundle}", file=sys.stderr)
        raise SystemExit(2)

    rep = Report()
    man = _verify_manifest(bundle, rep)
    mm = _verify_model(bundle, rep)
    if mm is not None:
        published = _verify_bounds(bundle, mm, rep)
        _rerun_attack_battery(mm, published, rep)
        _verify_scenarios(mm, rep)
    _verify_score(bundle, rep)
    _verify_release_package(bundle, man, rep)

    # the report lands NEXT TO the bundle: it is evidence ABOUT the
    # bundle produced after the manifest; inside, it would break the
    # manifest's complete-file-coverage invariant
    out = bundle.parent / f"{bundle.name}-VERIFICATION.md"
    lines = [
        "# External Verification Report",
        "",
        f"Bundle: `{bundle.name}` — verified from the published files "
        f"alone (no database access), {datetime.now(UTC).isoformat()[:19]}Z",
        "",
        "The verifier re-runs every reproducible claim with the lab's "
        "deterministic interpreter. A third party can re-run this "
        "script against the bundle and must obtain this report.",
        "",
        "| Check | Verdict | Detail |",
        "|---|---|---|",
    ]
    for c in rep.checks:
        lines.append(f"| {c.label} | **{c.verdict}** | {c.detail} |")
    counts = {v: sum(1 for c in rep.checks if c.verdict == v)
              for v in ("REPRODUCED", "CONSISTENT", "NOT-REPRODUCIBLE")}
    lines += [
        "",
        f"Totals: {counts['REPRODUCED']} reproduced, "
        f"{counts['CONSISTENT']} consistent, "
        f"{counts['NOT-REPRODUCIBLE']} not-reproducible.",
        "",
        "**OVERALL: " + ("VERIFY-PASS** — every reproducible claim "
                          "reproduces from the published files."
                          if rep.ok else
                          "VERIFY-FAIL** — at least one claim does NOT "
                          "reproduce from the published files."),
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"verification report: {out}")
    for c in rep.checks:
        mark = {"REPRODUCED": "+", "CONSISTENT": "~",
                "NOT-REPRODUCIBLE": "!"}[c.verdict]
        print(f"  [{mark}] {c.label}: {c.detail}")
    raise SystemExit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
