# Fix List — `cand-9200b07691c3` Publication Bundle

**Source:** independent audit of the 10-file bundle (`MANIFEST.json`, `README.md`,
`dossier.md`, `release-package.md`, `model-v3.json`, `score-decomposition.json`,
`adversarial-bounds.json`, `redteam-history.json`, `prior-art.json`, `verify.py`).

**Method:** SHA-256 of every file recomputed and diffed against `MANIFEST.json`;
`score-decomposition.json` arithmetic recomputed by hand; `verify.py` actually
executed against the bundle; every numeric claim in `release-package.md` §4b
traced back to `adversarial-bounds.json`; `redteam-history.json` sorted by
`created_at` and cross-checked against `dossier.md`'s prose and against
`model-v3.json`'s actual equations.

**Verdict:** manifest integrity, score arithmetic, and every attack-bounds number
check out exactly. Two defects block publication as written. Two more make the
bundle's "check it yourself" claim currently false. Three are minor polish.

---

## BLOCKING

### 1. `dossier.md` quotes a superseded, already-fixed vulnerability as the current verdict

**Where:** the "Game Theory" and "Security" sections both open with:

> Red Team verdict: vulnerable (strongest attack: Saw-tooth retention bias: the
> retention clip band 0.1..0.9 is asymmetric around the base delta_r=0.3, so a
> crafted zero-mean saw-tooth (slow negative separation legs, fast positive
> legs) biases the ti…)

**Why it's wrong:** this is a verbatim (truncated) quote of `redteam-history.json`
record `id=569`, filed `2026-09-08T10:34:19` — the *first* of three red-team
rounds, run against a pre-v3 retention formula. Two independent facts confirm
it's stale:

- The clip band it describes, `0.1..0.9`, doesn't exist in the published model.
  `model-v3.json`'s actual retention equation clips to `delta_r ± 0.25` —
  i.e. `[0.05, 0.55]` around the default `delta_r=0.3`.
- The *last* red-team round (`id=577`, `2026-09-08T11:04:14`) explicitly states
  this exact flaw was "measured closed" and returns `verdict: survives`,
  `strongest_attack_is_profitable: false`. `release-package.md` §4 ("No
  profitable attack remains unaddressed by the final model version") already
  reflects this later, correct round — so the bundle currently contradicts
  itself between `dossier.md` and `release-package.md` about the same
  candidate's status.

**Fix:** whatever code assembles `dossier.md`'s Game Theory / Security sections
needs to select the red-team record with the latest `created_at` for the
published model version, not the earliest. This is a selection/sort bug in the
bundle generator, not just a text problem in this one file — hand-editing the
current `dossier.md` will not stop the next candidate's bundle from doing the
same thing. Fix the underlying logic, then regenerate `dossier.md` from source.

**For reference**, the correct (final-round) content, pulled from
`redteam-history.json` ids 574–577 (`2026-09-08T11:04:14`):

- **Red Team** (`id 577`): verdict `survives`; strongest remaining attack is
  "Long-period alternation partial ride" — bounded by the symmetric band's
  half-width, "no profitable path identified." Both v1 and v2 flaws recorded
  as closed.
- **Game theory** (`id 574`, score 7.5): v3's sign-persistence counter closes
  both prior flaws; residual surface is a brief handoff window after the
  counter's decay — described as second-order.
- **Security** (`id 575`, score 7.0): the sign-persistence key removes the
  exploitable magnitude threshold entirely; hardest remaining attack is the
  same long-period alternation, bounded by the band half-width.
- **Oracle** (`id 576`, score 8.0): no external oracle; states derive locally
  from the on-chain level series; the only remaining "manipulation vector" is
  paying for a real sustained move — the design's intended use case, not an
  exploit.

The dimension *scores* already in `dossier.md` / `score-decomposition.json`
(game_theory 7.5, security 7.0, oracle_feasibility 8.0) are correctly pulled
from this final round — only the quoted prose is wrong.

### 2. Two dossier sections are byte-identical duplicates of two other sections

**Where:** "Game Theory" and "Security" render the exact same four lines (Red
Team verdict + three count lines). "Economic Analysis" and "Market" also
render the exact same six score lines. Same generator-bug family as #1:
whatever populates these headers isn't differentiating by section — it's
dumping one shared block under four different headings.

**Fix:** each section should show content specific to its own heading — e.g.
Security should surface `hardest_attack_to_defend` and the security agent's
own summary; Game Theory should surface `equilibria_notes` and
`death_spiral_risk`; Market should cover `market_demand` / competitive
positioning, not repeat every dimension's score. Fix in the generator, then
regenerate.

---

## SHOULD FIX (the "check it yourself" claim is currently false)

### 3. `verify.py` cannot actually be run by a third party from this bundle alone

Running it as shipped:
```
$ python verify.py .
Traceback (most recent call last):
  File "verify.py", line 40, in <module>
    from blockchain_rd_lab.formalization import MathModel
ModuleNotFoundError: No module named 'blockchain_rd_lab'
```
The README says this installs via `pip install -e .` "from the repo," but no
repo is linked or included. Right now an outside reader can only check the
**integrity** tier (file hashes, JSON parses, score arithmetic) — not the
**substance** tier (re-running the §20 attack battery or §15 scenarios), which
is the actual point of `verify.py` and what the README promises ("A third
party can re-run this script against the bundle").

**Fix — pick one:**
- Publish (or link) `blockchain_rd_lab`, or at minimum the deterministic pieces
  `verify.py` needs (`MathModel`, `MechanismSimulation`, `ScenarioBattery`,
  `AttackPatternBattery`), alongside this bundle; **or**
- If the package is intentionally kept private, change the README's "How to
  verify" section to say plainly that the substance checks require
  lab-internal tooling not included here, so readers don't believe they can
  currently self-serve something they can't.

### 4. `verify.py` has a broken timestamp in its own report header

```python
f"Bundle: `{bundle.name}` — verified from the published files "
"alone (no database access), {__import__('datetime').UTC"
".datetime.now(__import__('datetime').UTC).isoformat()[:19]}Z",
```
Only the first literal has the `f` prefix — Python doesn't propagate it across
implicit string-literal concatenation — so this prints the literal text
`{__import__('datetime').UTC.datetime.now(...)...}Z` instead of a date. It
also wouldn't work even with `f` added: `datetime.UTC` is a `timezone` object
with no `.datetime` attribute; the correct call is
`datetime.datetime.now(datetime.UTC).isoformat()[:19]`.

**Fix:**
```python
import datetime as _dt
...
f"Bundle: `{bundle.name}` — verified from the published files "
f"alone (no database access), "
f"{_dt.datetime.now(_dt.UTC).isoformat()[:19]}Z",
```
(or equivalent — the point is one `f`-prefixed string with a correct datetime
call). Doesn't change any REPRODUCED / CONSISTENT / NOT-REPRODUCIBLE verdict,
but a broken line in the flagship verifier's own output undercuts a bundle
whose entire premise is "code is the only evidence that counts."

---

## OPTIONAL / MINOR

### 5. `prior-art.json` likely double-counts one search as two

Both entries have identical `query` and `finding` text, differing only in
`source_id` (84 vs. 85). `release-package.md` §3 reports "Prior-art searches
recorded: 2" — confirm this is really two independent searches and not one
search logged under two source records; dedupe or correct the count if not.

### 6. Monte Carlo / §15 scenario numbers aren't independently checkable from the bundle

Unlike the attack-pattern bounds (fully backed by `adversarial-bounds.json` —
every number in `release-package.md` §4b traces to it exactly), the Monte
Carlo `mean_final` / `failures` figures and the "13/13 scenarios clean" claim
in `dossier.md` / `release-package.md` have no raw backing file here. Consider
shipping a `scenario-results.json` the way `adversarial-bounds.json` backs the
attack claims, or note in the README that these specific figures sit in the
CONSISTENT (not REPRODUCED) tier.

### 7. The one open, unresolved question isn't in the Residual Attacks Disclosure

`model-v3.json`'s `open_questions` field — "can sustained genuine pressure
(not crafted) hold the separation key high enough to farm retention?" — is
honestly disclosed there, but doesn't appear in `release-package.md` §4, which
is where a reader would look for exactly this kind of caveat. Add one line
there.

---

## Verification checklist (re-run after fixes land)

- [ ] `dossier.md`'s Red Team quote's underlying `created_at` is the latest
      red-team record for the published model version, not the earliest
- [ ] The quoted clip band matches `model-v3.json`'s actual retention equation
- [ ] "Game Theory" ≠ "Security" section text; "Economic Analysis" ≠ "Market"
      section text
- [ ] `python verify.py .` runs to completion without `ModuleNotFoundError`
      (or the README no longer claims a reader can do this unaided)
- [ ] The generated `*-VERIFICATION.md` header contains a real ISO timestamp,
      not literal `{...}` text
- [ ] `MANIFEST.json` hashes/byte counts still match after any file edits
      (re-run `sha256sum` / regenerate the manifest)
- [ ] `score-decomposition.json`'s `sum(score*weight)` still equals
      `overall_score`, and `README.md` / `dossier.md` still quote the same
      number
