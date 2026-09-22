# Publication Checklist (§41 human gate)

The lab recommends; a human decides. Work through this in order. Every
verification step is self-service — none of it requires trusting the lab's
own output.

## 1. Verify the evidence (≈15 min)

- [ ] `cd reports/release/bundle-cand-9200b07691c3 && python verify.py .`
      → exit 0, zero `[!]` warnings, reproduced score == 6.7250
- [ ] Check file integrity: the README's generated `sha256sum` command
      against `MANIFEST.json`
- [ ] Read `score-decomposition.json` → confirm 11/11 dimensions carry
      evidence, 0 imputed, per-dimension provenance present
- [ ] Skim `redteam-history.json` → the v1 ratchet (285→6479) and the v2
      flaws are disclosed unfiltered
- [ ] Read `release-package.md` §4 → residual attacks the final model
      still carries are listed; you are comfortable publishing them

## 2. Review the claims surface (≈15 min)

- [ ] `README.md` — numbers match the bundle (6.725, 100/20/10/1 funnel)
- [ ] `AUDITING.md` — open weaknesses are ones you can defend in public
- [ ] `reports/release/comparative-package.md` — the 9 thin finalists'
      limitation is disclosed prominently enough for your standards
- [ ] `ideas/rejected/index.md` — rejected mechanisms read as research
      assets, not embarrassments
- [ ] Search the repo for anything you would not want public
      (`git grep -in "api.key\|secret\|password" -- . ':!docs/rounds'`)

## 3. Review the launch drafts (≈15 min)

- [ ] `docs/launch/blog-post.md` — every number checks against the repo;
      rewrite the voice until it sounds like you
- [ ] `docs/launch/release-notes.md` — same check
- [ ] Confirm the blog post makes **no novelty claim** ("no substantially
      similar implementation was identified in the searched sources" is
      the strongest permitted phrasing, §29)
- [ ] Confirm nothing reads as investment advice or a token promise

## 4. Decide and execute (human only)

- [ ] **Decision: publish / hold / revise** — record it in
      `docs/rounds/` as the r50 round doc
- [ ] If publish: tag the release (`git tag -a v1.0-research -m ...`),
      create the GitHub release from `release-notes.md`
- [ ] Post the blog article; link the repo and the verifier command
- [ ] Pin the repo / update your public profiles as you see fit

## 5. After publication

- [ ] Watch for community criticism — the system is built to absorb it:
      new attacks become §20 battery entries, and the improvement loop
      re-runs
- [ ] Optional: re-run the red-team stage for the 9 thin finalists to
      rebuild their evidence trails (bridge provider, operator-authored)
- [ ] Optional: begin a fresh discovery round only after the current one
      has had time in public

---

*Prepared by the lab as a recommendation. The checkboxes are yours.*
