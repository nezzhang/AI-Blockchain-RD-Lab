# Rejected Mechanisms

Failed experiments are a research asset (§26): they record what was considered and why it did not survive. Nothing here is hidden or deleted.

| Candidate | Name | Category | Rejected because |
|-----------|------|----------|------------------|
| cand-642ea9f42170 | Corridor-Native FX Batch Matching | decentralized fx | SUPERSEDED (r7 evidence-quality correction): uninterpretable evidence — stored v1 model has a dependency cycle (impact_check/rebate_pool) today's interpreter rejects; its §15 runs predate the toposort gate. Successor candidate with a contract-compliant model follows. |
| cand-ef024f8bb596 | Escrowed Batch-Clearing Insurance Pool | decentralized fx | SUPERSEDED (r7 evidence-quality correction): uninterpretable evidence — stored v2 model has a dependency cycle (partition_income/shared_spend/solvency_tie) today's interpreter rejects; its §15 runs predate the toposort gate. Successor candidate with a contract-compliant model follows. |
| cand-3acbd67d51cb | Escrowed Batch-Clearing Insurance Pool | decentralized fx | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-9fba1d8cbe98 | Habitat Bond Curve | ecology | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-108293ca9f4f | AI-Compute Denominated Debt | financial markets | SUPERSEDED (r7 evidence-quality correction): replay-duplicate of cand-1acbaa9de0b0 (AI-Compute Denominated Debt) — same description, replayed evidence; a restorage workaround, not independent ranking evidence. Successor candidate with a contract-compliant model follows. |
| cand-cb4d584867ed | Tranche-Segmented Settlement Guarantee Stack | institutional settlement | SUPERSEDED (r7 evidence-quality correction): vacuous evidence — §15 battery 13/13 degenerate under today's gates (states pinned at clip bounds); v2 'clean' verdicts describe identical saturated trajectories, not stress survival. Successor candidate with a contract-compliant model follows. |
| cand-a218268ad562 | Prediction-Coupled Insurance Float | insurance | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-bec3b6e85a91 | Prediction-Coupled Insurance Float | insurance | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-94920de262c7 | Prediction-Coupled Insurance Float | insurance | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-a7f8794b596a | Congestion-Reflexive Bandwidth Unit | internet | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-023e4ade3011 | Congestion-Reflexive Bandwidth Unit | internet | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-abb98e812f6b | Congestion-Reflexive Bandwidth Unit | internet | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-9f7f38fbc39b | Demographic Reserve Rule | monetary economics | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-7f2f07fd4e9a | Population-Linked Supply | monetary economics | confirmed fatal flaw(s) (game_theory); §20 gate |
| cand-db0588dfed1a | Bandwidth Futures Market | network economics | SUPERSEDED (r7 evidence-quality correction): replay-duplicate of cand-58d7091eb2a7 (Bandwidth Futures Market) — same description, replayed evidence; a restorage workaround, not independent ranking evidence. Successor candidate with a contract-compliant model follows. |
| cand-06418647c270 | Trade-Corridor Clearing Tokens | payments | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-f9d0e9af020b | Trade-Corridor Clearing Tokens | payments | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-0572a9589784 | Dual-Quote Stability Insurance Market | stablecoin mechanism | prior-art filter cut (novelty class very_similar_existing); §7/§12 |
| cand-af096f7f6aa2 | Countercyclical Corridor Insurance Float | stablecoin routing | SUPERSEDED (r7 evidence-quality correction): stored model has a dependency cycle today's interpreter rejects; its §15 runs predate the toposort gate and read stale values. Non-finalist, recorded for §26 honesty; no successor needed (idea remains archived with research). |
| cand-636a97854ac8 | Dual-Sided Bond Auction Rebalancer | stablecoin routing | SUPERSEDED (r7 evidence-quality correction): uninterpretable evidence — stored v2 model has a dependency cycle (capacity/rebalance/seasoning_depth) today's interpreter rejects; its §15 runs predate the toposort gate and read stale values. Successor candidate with a contract-compliant model follows. |
| cand-07d9ef676123 | Prediction-Weighted Corridor Risk Pricing | stablecoin routing | SUPERSEDED (r7 evidence-quality correction): stored model has a dependency cycle today's interpreter rejects; its §15 runs predate the toposort gate and read stale values. Non-finalist, recorded for §26 honesty; no successor needed (idea remains archived with research). |
| cand-4952b2a96bab | Prediction-Weighted Corridor Risk Pricing | stablecoin routing | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-c70d44d533eb | Homeostatic Reserve Stablecoin | stablecoins | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-c17ab7a0f74e | Homeostatic Reserve Stablecoin | stablecoins | SUPERSEDED (r7 evidence-quality correction): vacuous evidence — §15 battery 13/13 degenerate under today's gates (states pinned at clip bounds); v2 'clean' verdicts describe identical saturated trajectories, not stress survival. Successor candidate with a contract-compliant model follows. |
| cand-16d505be99f6 | Homeostatic Reserve Stablecoin | stablecoins | research-funnel cut (class A/B or §7 overflow); see filter records |
| cand-7f4c2dee85e7 | Vol-Weighted Fee Smoothing Escrow | transaction fee markets | SUPERSEDED (r7 evidence-quality correction): vacuous evidence — §15 battery 13/13 degenerate under today's gates (states pinned at clip bounds); v2 'clean' verdicts describe identical saturated trajectories, not stress survival. Successor candidate with a contract-compliant model follows. |

## Confirmed Fatal Flaws (§20)

- **Population-Linked Supply** (cand-7f2f07fd4e9a): Red team confirmed a profitable structural attack: Coordinate an anchor spike during a low-liquidity window so the mechanism over-expands exactly when exit is cheapest.
