# External Audit — Round 4 (2026-09-15)

## Scope
Fresh hostile re-audit of the current public `main` against `AUDITING.md`'s four load-bearing systems:

1. §19 deterministic scorer
2. §20 fatal-flaw gate
3. Attack battery classification layers
4. Deterministic interpreter

Prior rounds 27–30 and findings already fixed in the repository were not re-reported.

## Result
**NO NEW VERIFIED FINDINGS.**

### §19 scorer
The scorer remains deterministic. Missing dimensions are explicitly imputed at the configured 5.0 floor and flagged as imputed; confirmed fatal flaws are capped at 5.0 and cannot be averaged away. No new candidate-controlled scoring path was found that changes the already-disclosed imputation-floor limitation.

### §20 fatal-flaw gate
The former LLM profitability trust/suppression vector is closed in the live implementation. Every non-terminal `fatal` verdict invokes `_measured_flaw_edge()`; confirmation is based on deterministic battery evidence exceeding `FLAW_EDGE_THRESHOLD`, while the LLM profitability boolean is persisted only as metadata. Thus `profitable=false` cannot suppress measurement and a fatal assertion alone cannot reject.

### Attack battery classification
The current implementation preserves full `PatternSpec` calibration for doubled-window transit confirmation, keeps load-bearing pin counterfactuals keyed by the full spec, and keeps pinned states disclosed rather than automatically classifying them as regime tracking/transit. Drift wedges are disclosed, while headline attribution remains tied to measured consumer-response metrics. I did not verify a distinct new bypass in the current classification code.

### Interpreter
The interpreter and §13 formalization schema share the canonical `e`/`pi` constant set. AST validation permits only the documented arithmetic/functions/constants, and evaluation resolves the constants correctly. No new arithmetic/schema-language mismatch was found in the reviewed path.

## Verification limitation
The public GitHub source is readable and was inspected directly, including `AUDITING.md`, `CLAUDE.md`, the live load-bearing modules, and the red-team gate tests. A local `git clone` and full pytest execution were attempted but the audit environment cannot resolve `github.com`; therefore this pass is source/test inspection rather than an independently executed full-suite run.
