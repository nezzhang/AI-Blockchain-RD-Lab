---
name: Audit finding
about: Report a correctness / honesty / reproducibility defect in a load-bearing system
title: "[audit] <short description>"
labels: [audit]
---

## System affected
<!-- e.g. §19 scorer, §20 fatal-flaw gate, attack battery, interpreter,
     report assembler, §17 tokenomics, publication bundle. See AUDITING.md. -->

## Finding
<!-- What is wrong, and why it matters. Distinguish FACT / INFERENCE /
     HYPOTHESIS (§12). -->

## Reproduction
<!-- The exact command or minimal script that demonstrates the finding.
     Findings are verified by live execution before any fix (§2). -->

```bash
# steps / probe
```

## Expected vs actual
<!-- What the code/docs claim vs what it does. -->

## Prior-art check
<!-- Confirm this is not already fixed in a prior round — cite the
     round / *-FIXES-RESPONSE.md you checked. See AUDITING.md "do not
     re-report those." -->

## Suggested fix (optional)
