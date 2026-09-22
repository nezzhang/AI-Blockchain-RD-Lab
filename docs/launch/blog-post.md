# DRAFT — "An AI research lab that has to prove everything it says"

> **Status: DRAFT for human review.** Not published anywhere. The §41
> publication gate applies: a human reads this, checks every claim against
> the repo, and decides. Nothing here may be posted until that happens.
> Every number below is sourced from the repository at commit `38e8c01`.

---

I built an autonomous research lab that hunts for novel blockchain economic
mechanisms — and then refuses to let you take its word for anything.

The lab's job: take 100 raw mechanism ideas across 20 domains, kill the bad
ones with math, simulation, and adversarial attack, and hand me one
recommendation with a complete evidence trail. No token. No deployment. No
"trust the AI." The output is a *verifiable claim*, not a pitch.

## The funnel

100 mechanisms → 20 survive prior-art screening → math models → 13
simulation scenarios → 8 attack choreographies → 10 finalists → **1
recommended**: a mechanism I'm calling the *Separation-Keyed Fee Smoothing
Escrow* — a fee-smoothing escrow whose retention keys the *signed
separation* between a fast pressure EMA and a slow regime EMA, with a
sign-persistence counter that discounts saw-tooth manipulation without
touching genuine pressure.

Its composite score is **6.725/10**, and every one of the 11 score
dimensions is backed by stored evidence. Zero imputed.

## Why you don't have to believe me

The lab runs on one rule: **LLMs propose, code tests, evidence decides.**

- Agents can only emit structured JSON that passes a Pydantic schema gate.
  No schema, no storage.
- Every verdict — fatal flaw, score, ranking — is computed by deterministic
  code from stored records. There is no report-writer LLM anywhere in the
  system.
- A fatal flaw is *measured*, never averaged away. If the strongest attack
  is profitable, the mechanism is rejected, full stop. Rejected ideas are
  kept as research assets, not deleted.
- The release bundle ships its own verifier. `python verify.py .` re-runs
  the attack battery, the scenarios, and the score arithmetic against the
  published model — using only the files in the bundle. It exits 0 or the
  claims don't stand.

The final mechanism went through three model versions. v1 had a measured
ratchet flaw (retention grew linearly under resonance: 285 → 1321 → 2143 →
6479, unbounded). v2 fixed it but left two attack surfaces. v3 closed both
with the sign-persistence counter — and the verifier re-measures all of it.

## The part I'm proudest of: it admits what it doesn't know

The dossier lists residual attacks the final model *still* carries. The
audit log lists the weaknesses three external audits found and what was
fixed. Nine of the ten finalists have thinner evidence trails than the
winner (a store rebuild cost their records), and the reports say so,
in plain language, instead of papering over it.

A research tool that hides its failures is a marketing tool. This one
publishes them.

## Where this is on the ladder

Idea → Research → Simulation → **📢 Publication (human decision)** →
community criticism → prototype → testnet → adoption → *only then* anything
live.

The first three rungs are done and reproducible. The fourth is a human
decision — mine, not the lab's.

## Verify it yourself

```bash
git clone https://github.com/nezzhang/AI-Blockchain-RD-Lab.git
cd AI-Blockchain-RD-Lab/reports/release/bundle-cand-9200b07691c3
python verify.py .   # needs only Python 3.12+ and pydantic
```

Everything is MIT licensed. The rejected mechanisms are in
`ideas/rejected/`. The full methodology is in `MASTER BUILD PROMPT.md`.

If you find a flaw the red team missed, that finding is the most valuable
contribution this project can receive — the system is built to absorb it.

---

*Review notes for the human publisher: check every number against the repo
before posting; confirm the tone matches your voice; decide the venue
(blog, Show HN, research forum). Suggested venues: personal blog first,
then a link post — the verifier is the strongest hook.*
