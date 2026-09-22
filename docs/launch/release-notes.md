# DRAFT — Release Notes: first public research release

> **Status: DRAFT for human review (§41 gate).** Intended for the GitHub
> release that accompanies publication of the rank-1 bundle. Do not publish
> until a human has verified every claim below against the repo.

---

## AI Blockchain R&D Lab — first evidence-backed recommendation

After 49 recorded rounds and 9 build phases, the lab publishes its first
recommendation:

**Separation-Keyed Fee Smoothing Escrow** (`cand-9200b07691c3`)
Deterministic §19 composite: **6.725 / 10** — rank 1 of 10 finalists,
all 11 score dimensions backed by stored evidence (0 imputed).

### What ships

- `reports/release/bundle-cand-9200b07691c3/` — the complete public
  evidence set: 19-section dossier, final MathModel (v3), full red-team
  history (v1→v2→v3, every break and fix measured), §15 scenario and Monte
  Carlo records, §20 adversarial battery census, prior-art trail, and the
  score decomposition.
- `verify.py` — the external verifier. Re-runs the attack battery,
  scenarios, and score arithmetic from the published files alone
  (Python 3.12+ and pydantic; no lab install, no database).
- `lab-runtime/` — the deterministic runtime the claims were measured
  with: the safe equation interpreter and both batteries ship *with* the
  claims.
- `MANIFEST.json` — SHA-256 of every file in the bundle.
- Comparative package for all 10 finalists, with the 9 thin finalists'
  evidence-trail limitation disclosed in plain language.

### Integrity

- 607 tests, `ruff`, and `mypy` enforced by CI on every push.
- The bundle verifier runs in CI against the committed bundle.
- Three rounds of external audit findings and fixes are documented in
  `docs/rounds/` and summarized in `AUDITING.md`.

### Scope and honesty

This is **simulation-stage evidence**: adversarial bounds were measured
against a deterministic equation interpreter under named attack
choreographies — not deployed software, not live attackers. The residual
attacks the final model still carries are disclosed in the release
package. No token, no deployment, no live contract (§27/§28). Publication
is a human decision; the lab recommends, it does not launch.

### Verify in one command

```bash
cd reports/release/bundle-cand-9200b07691c3 && python verify.py .
```
