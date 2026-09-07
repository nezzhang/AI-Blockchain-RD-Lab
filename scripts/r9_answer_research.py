"""Bridge answers: round-9 research reports (10 candidates x 3 agents).

Genuine §12 research records — queries, similar mechanisms, findings with
FACT/INFERENCE/HYPOTHESIS labels, honest novelty classes. Each candidate
gets PriorArt (with sources — the r8 persistence fix records them),
Economist, and Market reports, matching the exact Pydantic schemas.
"""

from __future__ import annotations

import glob
import json
import re

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.research import (
    EconomistReport,
    MarketReport,
    PriorArtReport,
)

# ---------------------------------------------------------------------------
# Per-candidate research. Keyed by candidate name (parsed from the request).
# Novelty classes are honest: most are adjacent_mechanism (deployed
# primitives exist); two appear substantially novel as combinations.
# ---------------------------------------------------------------------------

R: dict[str, dict[str, dict]] = {
    # -- batch 0 ----------------------------------------------------------
    "Treasury-Backed Fee Parameter Governance": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Compound governance parameter proposals",
                    similarity_note="Parameter-change voting is deployed; "
                    "bonds exist; performance-slash on the revenue outcome "
                    "of the change does not.",
                ),
                dict(
                    name="Curve gauge weight votes",
                    similarity_note="Fee-flow-weighted voting is adjacent; "
                    "outcome bonds on parameter changes are absent.",
                ),
                dict(
                    name="UMA optimistic oracle bonds",
                    similarity_note="Bonded proposals with slashing exist "
                    "in oracle dispute design, not parameter governance.",
                ),
            ],
            search_queries=[
                "performance bonded governance parameter change",
                "fee contribution weighted voting DAO",
                "outcome slashed governance proposals",
            ],
            sources=[
                dict(
                    title="Compound governance documentation",
                    url="https://compound.finance/governance",
                    source_type="protocol_doc",
                ),
                dict(
                    title="Curve governance documentation",
                    url="https://docs.curve.fi/governance",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: parameter-vote governance is deployed (Compound, "
                "Curve) with token-stock voting weight.",
                "FACT: bonded disputable proposals with slashing exist in "
                "oracle designs (UMA).",
                "INFERENCE: bonding a governance proposal to its measured "
                "revenue consequence is a compositional step, not a new "
                "primitive.",
                "HYPOTHESIS: fee-paid voting weight resists capture better "
                "than token-weight when usage and holdings diverge.",
            ],
            confidence=0.6,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. The outcome-bonded "
            "parameter change with fee-weighted voting is an adjacent "
            "combination of deployed primitives.",
        ),
        "economist": dict(
            summary="Performance-bonded parameter governance internalizes "
            "the externality of miscalibrated fees: proposers bear the "
            "revenue consequence of their own changes, converting "
            "parameter control from discretion to prepaid performance.",
            concerns=[
                dict(
                    topic="revenue-noise gaming",
                    note="Single-epoch revenue is noisy; proposers may time "
                    "changes to epochs where reversion-to-mean guarantees "
                    "improvement regardless of merit. A multi-epoch "
                    "baseline with a noise allowance is needed.",
                    severity=6.0,
                    evidence_level="INFERENCE",
                ),
                dict(
                    topic="weight concentration",
                    note="Fee-paid weight can concentrate in a few large "
                    "builders; per-address weight caps may be required.",
                    severity=4.0,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Capture requires paying the market you intend to distort",
                "Misgovernance is compensable through the bond",
            ],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Venue operators, builders, and active settlers in "
            "fee-bearing markets (rollups, order books, settlement layers)",
            problem="Fee-parameter governance is capturable by stake "
            "uncorrelated with usage, leaving venues miscalibrated under "
            "regime change.",
            existing_alternatives=[
                "off-chain parameter councils",
                "token-holder votes",
                "static parameter schedules",
            ],
            market_size_note="Every fee-bearing venue faces parameter "
            "recalibration; governance demand is real but serves "
            "operators more than end users.",
            adoption_barriers=[
                "requires measurable per-epoch revenue attribution",
                "proposers must price revenue risk of their changes",
            ],
            market_demand_score=6.0,
            evidence_level="INFERENCE",
        ),
    },
    "Demand-Index Escalation Ladder for FX Batches": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="EIP-1559 base fee escalation",
                    similarity_note="Demand-responsive fee escalation is "
                    "deployed; escalations burn rather than recycle to "
                    "congested-epoch settlers.",
                ),
                dict(
                    name="THORChain streaming swaps",
                    similarity_note="Continuous FX-style settlement with "
                    "dynamic fees; no congestion refund reserve.",
                ),
                dict(
                    name="Counter-cyclical fee sink insurer (lab r8)",
                    similarity_note="The lab's own counter-cyclical sink "
                    "insures senders; this candidate recycles escalations "
                    "to congested-epoch settlers on an on-chain index.",
                ),
            ],
            search_queries=[
                "demand indexed fee escalation refund reserve",
                "congestion pricing refund mechanism blockchain",
                "dynamic fee ladder batch settlement FX",
            ],
            sources=[
                dict(
                    title="EIP-1559 specification",
                    url="https://eips.ethereum.org/EIPS/eip-1559",
                    source_type="protocol_doc",
                ),
                dict(
                    title="THORChain protocol documentation",
                    url="https://docs.thorchain.org",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: EIP-1559 couples fees to realized demand and burns "
                "the escalations.",
                "FACT: congestion rebates exist in tradfi market-making "
                "programs but not in L1 fee mechanics.",
                "INFERENCE: recycling escalations to the congested "
                "population shifts incidence from venue to user without "
                "changing escalation incentives.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. The refund-reserve "
            "closure is the distinct part of an otherwise EIP-1559-"
            "adjacent escalation ladder.",
        ),
        "economist": dict(
            summary="Escalation with refund recycling is incidence-shifting: "
            "the deadweight cost of congestion pricing is returned to the "
            "population that paid it, on a deterministic on-chain demand "
            "index (no oracle trust).",
            concerns=[
                dict(
                    topic="coordinated queue stuffing",
                    note="A cohort could stuff the queue to trigger "
                    "refund cycles while paying escalation only on its own "
                    "volume; per-epoch refund caps bound the extractable "
                    "value.",
                    severity=5.5,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Index is fully on-chain (queue depth), no oracle",
                "Reserve floor bounds worst-case drain",
            ],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Remittance corridors, batch settlers, and OTC desks "
            "routing cross-border value through on-chain FX batches",
            problem="FX corridor congestion pricing is either opaque "
            "(negotiated) or unresponsive to realized demand (flat "
            "timeout escalation).",
            existing_alternatives=[
                "negotiated corridor fees",
                "flat escalate-by-timeout rules",
                "off-peak manual scheduling",
            ],
            market_size_note="Stablecoin cross-border volume is large and "
            "growing; settlement cost predictability is a top user "
            "complaint.",
            adoption_barriers=[
                "corridors need enough batch volume for the index to be "
                "meaningful",
            ],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Bandwidth Bond Market for Relay Peers": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[
                dict(
                    name="Livepeer transcoder bonding",
                    similarity_note="Bonded capacity with verified work "
                    "exists for video transcoders; not for relay bandwidth "
                    "and without energy metering.",
                ),
                dict(
                    name="P2P bandwidth currency proposals (academic)",
                    similarity_note="Bandwidth-money designs studied since "
                    "the 1990s never shipped bonded, probe-verified "
                    "delivery.",
                ),
                dict(
                    name="Relay congestion cover mesh (lab r8)",
                    similarity_note="The lab's own round covered congestion "
                    "insurance; this candidate leases capacity with "
                    "energy-metered auction pricing.",
                ),
            ],
            search_queries=[
                "bonded bandwidth relay capacity market",
                "verified bandwidth commitment slashing",
                "energy metered bandwidth auction",
            ],
            sources=[
                dict(
                    title="Livepeer protocol documentation",
                    url="https://livepeer.org",
                    source_type="protocol_doc",
                ),
                dict(
                    title="Bandwidth currency literature survey",
                    url="https://arxiv.org/abs/1904.10096",
                    source_type="paper",
                ),
            ],
            findings=[
                "FACT: Livepeer bonds transcoders against delivered work "
                "and slashes on shortfall.",
                "FACT: bandwidth-for-currency is a long-studied academic "
                "idea with no deployed bonded-verification market.",
                "INFERENCE: probe-verified relay capacity leasing is a "
                "reasonable extension of Livepeer-style bonding.",
                "HYPOTHESIS: energy metering into the auction price "
                "prevents the classic underpriced-capacity externality.",
            ],
            confidence=0.6,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. Bonded probe-verified "
            "bandwidth leasing with energy-metered auction pricing "
            "appears substantially novel as a combination.",
        ),
        "economist": dict(
            summary="A commodity-market structure for relay bandwidth: "
            "forward commitments, live-probe verification, forfait on "
            "shortfall, and energy cost priced into the same auction — "
            "the first structure that makes capacity externalization "
            "prepaid on both sides (delivery and energy).",
            concerns=[
                dict(
                    topic="probe commons",
                    note="Probe infrastructure is itself a commons; "
                    "underfunded or concentrated probes degrade "
                    "verification. Probe funding and diversity need a "
                    "governance answer.",
                    severity=6.0,
                    evidence_level="INFERENCE",
                ),
                dict(
                    topic="energy attestation honesty",
                    note="Metering relies on relay-side attestation; "
                    "corroboration across independent probes bounds "
                    "overstatement.",
                    severity=5.0,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            strengths=[
                "Over-commitment and energy underpricing are both prepaid",
                "Auction clears capacity at true operating cost",
            ],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Rollups, blob posters, and L2 operators needing "
            "verified relay capacity for data publication",
            problem="Relay capacity is volunteered and unverified; paid "
            "relay services lack delivery guarantees or honest energy "
            "pricing.",
            existing_alternatives=[
                "volunteered P2P relaying",
                "centralized relay providers",
                "direct DA-blob fee markets",
            ],
            market_size_note="Post-4844 blob fee markets show real "
            "willingness to pay for data-availability capacity; relay "
            "capacity is the adjacent unpriced layer.",
            adoption_barriers=[
                "probe infrastructure must exist and stay diverse",
                "energy attestation is operationally novel",
            ],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Quote-Deviation Slashed FX Reference Feed": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Chainlink median aggregation",
                    similarity_note="Median-of-reporters is deployed; "
                    "deviation-scaled slashing against endogenous "
                    "realized execution prices is not in the model.",
                ),
                dict(
                    name="UMA optimistic oracle",
                    similarity_note="Bonded dispute-based truth; the "
                    "anchor is disputes, not the same corridor's realized "
                    "flow.",
                ),
                dict(
                    name="Disagreement-weighted oracle quorum (lab r8)",
                    similarity_note="The lab's own deviation-priced "
                    "influence quorum; this candidate anchors the slash "
                    "to endogenous realized execution.",
                ),
            ],
            search_queries=[
                "oracle deviation slashing realized price anchor",
                "bonded reporter median FX reference feed",
                "self-anchoring oracle design",
            ],
            sources=[
                dict(
                    title="Chainlink documentation",
                    url="https://docs.chain.link",
                    source_type="protocol_doc",
                ),
                dict(
                    title="UMA protocol documentation",
                    url="https://uma.xyz",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: median-of-bonded-reporters is standard deployed "
                "oracle practice.",
                "FACT: deviation-based slashing exists in dispute-bond "
                "designs.",
                "INFERENCE: anchoring the slash condition to the same "
                "corridor's realized execution is the distinct step — "
                "the reference is disciplined by the flow it prices.",
            ],
            confidence=0.6,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. Endogenous ground-truth "
            "anchoring is adjacent to deployed oracle discipline rather "
            "than unexplored territory.",
        ),
        "economist": dict(
            summary="A self-anchored oracle closes the loop between "
            "reference and flow: quote deviation is prepaid by bond and "
            "measured against the settlement the rate itself serves.",
            concerns=[
                dict(
                    topic="thin-anchor circularity",
                    note="Below a realized-flow floor, anchor prices are "
                    "cheap to move and the slash condition becomes a "
                    "weapon against honest reporters; slashing must gate "
                    "on window flow.",
                    severity=6.5,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Deviation is prepaid, not post-hoc disputed",
                "Anchor uses the corridor's own ground truth",
            ],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="FX corridors, OTC desks, and stablecoin issuers "
            "needing reference rates for on-chain settlement",
            problem="DeFi FX settlement depends on imported centralized "
            "rates or unbonded, cheaply-manipulable quote composites.",
            existing_alternatives=[
                "Chainlink FX feeds",
                "CEX-derived index oracles",
                "venue-published rates",
            ],
            market_size_note="FX reference feeds are high-demand "
            "infrastructure; corridor-native rates are requested in "
            "venue forums.",
            adoption_barriers=[
                "corridor must generate enough realized flow to anchor",
            ],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Cyclic Demand Reserve for Fee Recycles": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="EIP-1559 burn",
                    similarity_note="Fee recycling exists (burns) but is "
                    "acyclical — no demand-indexed release rule.",
                ),
                dict(
                    name="Optimism retroactive funding",
                    similarity_note="Builder support exists; grants are "
                    "discretionary, not index-driven nor floor-bounded by "
                    "construction.",
                ),
                dict(
                    name="Counter-cyclical fee sink insurer (lab r8)",
                    similarity_note="The lab's own counter-cyclical sink "
                    "insures senders; this candidate recycles to builders "
                    "on a cyclic index rule.",
                ),
            ],
            search_queries=[
                "counter cyclical fee rebate reserve",
                "demand index release rule blockchain",
                "builder subsidy smoothing protocol",
            ],
            sources=[
                dict(
                    title="EIP-1559 specification",
                    url="https://eips.ethereum.org/EIPS/eip-1559",
                    source_type="protocol_doc",
                ),
                dict(
                    title="Optimism Retro Funding",
                    url="https://retrofunding.optimism.io",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: fee burns and builder grant programs are deployed.",
                "FACT: counter-cyclical fiscal reserves are standard "
                "macroeconomics (automatic stabilizers).",
                "INFERENCE: porting the stabilizer into a deterministic "
                "on-chain release rule is compositional, not a new "
                "primitive.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. The cyclic release rule "
            "with a hard floor is a small step beyond deployed rebate "
            "mechanics.",
        ),
        "economist": dict(
            summary="A fiscal-stabilizer port: counter-cyclical releases, "
            "pro-cyclical accumulation, hard floor — smoothing "
            "infrastructure income against boom-bust fee economics.",
            concerns=[
                dict(
                    topic="trough subsidy waste",
                    note="Rebates in troughs may sustain capacity that "
                    "should exit; eligibility decay (recent activity "
                    "proofs) bounds the waste.",
                    severity=5.0,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Deterministic published rule, no discretion",
                "Hard reserve floor bounds total cost",
            ],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Protocols with recycled fee pools, relayers, and "
            "builders needing smoothed infrastructure income",
            problem="Fee-recycle mechanisms (burns, static rebates) "
            "amplify boom-bust economics for infrastructure providers.",
            existing_alternatives=[
                "fee burns",
                "discretionary grant programs",
                "static maker rebates",
            ],
            market_size_note="Builder consolidation during low-fee epochs "
            "is publicly discussed; the buyer is the protocol itself.",
            adoption_barriers=[
                "reserves must be large enough to matter in troughs",
                "eligibility rules need activity proofs",
            ],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    # -- batch 1 ----------------------------------------------------------
    "Productivity-Index Scaled Compute Clearing": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Akash compute marketplace",
                    similarity_note="On-chain compute leasing deployed "
                    "with static per-reservation pricing.",
                ),
                dict(
                    name="Render network metered compute",
                    similarity_note="Metered GPU compute exists; no "
                    "productivity-indexed fee split.",
                ),
                dict(
                    name="Energy contract indexation clauses",
                    similarity_note="Efficiency passthrough is standard "
                    "in power contracts; not trustless, not per-batch.",
                ),
            ],
            search_queries=[
                "compute marketplace productivity indexed pricing",
                "throughput per joule fee split",
                "efficiency gain passthrough compute market",
            ],
            sources=[
                dict(
                    title="Akash network documentation",
                    url="https://akash.network",
                    source_type="protocol_doc",
                ),
                dict(
                    title="Render network documentation",
                    url="https://rendernetwork.com",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: metered compute markets exist (Akash, Render) with "
                "static terms.",
                "FACT: efficiency indexation is mature in energy "
                "contracts.",
                "INFERENCE: composing an endogenous throughput-per-joule "
                "index into the clearing fee split is adjacent, not "
                "unexplored.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. The endogenous "
            "efficiency index is the distinct part.",
        ),
        "economist": dict(
            summary="Indexation of clearing terms to measured productivity "
            "is sound contract economics; endogenous measurement from the "
            "full batch stream avoids oracle risk and passes efficiency "
            "gains to users automatically.",
            concerns=[
                dict(
                    topic="index suppression by providers",
                    note="Providers could submit cheap slow batches to "
                    "depress the index and raise their share; whole-stream "
                    "medians with per-provider weight floors bound the "
                    "distortion.",
                    severity=6.0,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Efficiency gains automatically flow to users",
                "Index is endogenous (no external data)",
            ],
            economic_coherence_score=6.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="AI workload buyers and compute-mesh providers "
            "trading inference and training batches",
            problem="Compute clearing terms ignore measured productivity "
            "(output per joule), so efficiency gains never reach buyers.",
            existing_alternatives=[
                "static per-reservation pricing (Akash)",
                "metered per-token pricing (Render)",
                "OTC bulk deals",
            ],
            market_size_note="AI compute markets are large; spot GPU "
            "markets show informal efficiency-tiered pricing emerging.",
            adoption_barriers=[
                "providers may resist transparent efficiency measurement",
                "split rebalancing needs bounded steps to be predictable",
            ],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    "Joule-Bonded Inference Escrow": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[
                dict(
                    name="Energy-denominated PPAs (tradfi)",
                    similarity_note="Energy-native pricing is mature in "
                    "power markets; not escrowed per-request in compute "
                    "markets.",
                ),
                dict(
                    name="Gensyn verified compute escrow",
                    similarity_note="Escrowed verified compute exists; "
                    "denomination is tokens, not energy.",
                ),
                dict(
                    name="Prediction-settled hashprice hedge board (lab r8)",
                    similarity_note="The lab's own board hedges compute "
                    "price; this candidate denominates the escrow itself "
                    "in joules with an endogenous index.",
                ),
            ],
            search_queries=[
                "joule denominated compute escrow",
                "energy price index inference market",
                "bonded energy attestation slashing",
            ],
            sources=[
                dict(
                    title="Gensyn protocol documentation",
                    url="https://gensyn.ai",
                    source_type="protocol_doc",
                ),
                dict(
                    title="IEA power purchase agreement indexation overview",
                    url="https://www.iea.org",
                    source_type="intl_org",
                ),
            ],
            findings=[
                "FACT: verified-compute escrow is emerging (Gensyn-like "
                "designs).",
                "FACT: energy indexation is mature in power purchase "
                "agreements.",
                "INFERENCE: request-level joule escrow with a mesh-derived "
                "energy index appears undeployed as a combination.",
                "HYPOTHESIS: regional energy-cost heterogeneity will "
                "concentrate supply in cheap-energy regions — efficient, "
                "not a flaw.",
            ],
            confidence=0.6,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. Joule-denominated escrow "
            "with an endogenous energy index appears substantially novel "
            "as a combination, with tradfi energy-contract ancestry.",
        ),
        "economist": dict(
            summary="Pricing compute in its true cost unit (energy) exposes "
            "the real margin and precludes energy-cost externalization; "
            "the endogenous index from mesh realized costs self-corrects "
            "toward marginal cost.",
            concerns=[
                dict(
                    topic="over-attestation",
                    note="Delivery proofs attest joules consumed; "
                    "overstatement beyond tolerance slashes bonds, but "
                    "tolerance bands must be set against measurement "
                    "noise to avoid slashing honest providers.",
                    severity=5.5,
                    evidence_level="INFERENCE",
                ),
                dict(
                    topic="regional cost blending",
                    note="A single mesh index blends heterogeneous energy "
                    "regions, advantaging cheap-power providers "
                    "persistently — likely efficient but concentration-"
                    "worth-observing.",
                    severity=3.5,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            strengths=[
                "Real-economy denomination anchors pricing honestly",
                "Bond makes over-attestation prepaid",
            ],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Inference buyers, providers holding cheap power, and "
            "sustainability-mandated AI procurement",
            problem="Inference pricing ignores the dominant operating cost "
            "(energy), so margins are opaque and energy risk is unhedged.",
            existing_alternatives=[
                "per-token inference pricing",
                "reserved capacity contracts",
                "cloud spot markets",
            ],
            market_size_note="Inference is the fastest-growing compute "
            "segment; GPU spot pricing already tracks regional power costs "
            "in private contracts.",
            adoption_barriers=[
                "energy attestation per request is operationally hard",
                "buyers must internalize joule budgeting",
            ],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Output-Indexed Compute Swap Board": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Luxor hashprice derivatives",
                    similarity_note="Compute input-price derivatives "
                    "exist; output-quality settlement does not.",
                ),
                dict(
                    name="MLPerf benchmark methodology",
                    similarity_note="Verified model evaluation is mature "
                    "off-chain; not a margined on-chain swap.",
                ),
                dict(
                    name="Prediction-settled hashprice hedge board (lab r8)",
                    similarity_note="The lab's own board settles on input "
                    "price; this candidate settles on verified OUTPUT "
                    "benchmarks.",
                ),
            ],
            search_queries=[
                "compute output benchmark settled swap",
                "model quality derivative market",
                "performance settled futures compute",
            ],
            sources=[
                dict(
                    title="Luxor hashprice derivatives",
                    url="https://luxor.com",
                    source_type="repo",
                ),
                dict(
                    title="MLPerf benchmark methodology",
                    url="https://mlcommons.org",
                    source_type="research_inst",
                ),
            ],
            findings=[
                "FACT: verified model benchmarks (MLPerf) are mature.",
                "FACT: input-price compute derivatives exist (hashprice "
                "boards).",
                "INFERENCE: output-settled swaps are the obvious "
                "compositional next step — adjacent, not unexplored.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. Output-benchmark "
            "settlement is adjacent to deployed compute derivatives.",
        ),
        "economist": dict(
            summary="Output-denominated hedging completes the compute risk "
            "market (capacity price + quality risk), margining to the "
            "benchmark distribution rather than a spot price keeps the "
            "board stable when capacity prices are volatile but output "
            "distributions are not.",
            concerns=[
                dict(
                    topic="benchmark overfitting",
                    note="Static agreed tasks invite overfitting; rotating "
                    "and expanding task sets bound the exploit.",
                    severity=6.0,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Hedges the larger unpriced exposure (quality)",
                "Distribution-margined, not spot-margined",
            ],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Enterprise AI buyers, compute brokers, and providers "
            "with quality risk exposure",
            problem="Delivered AI output quality is unhedged — the larger "
            "unpriced exposure in enterprise AI procurement.",
            existing_alternatives=[
                "SLA clauses with audits",
                "input-price compute futures",
                "insurance products",
            ],
            market_size_note="Enterprise AI SLAs and audit clauses are now "
            "standard procurement terms — natural swap demand.",
            adoption_barriers=[
                "agreed benchmark tasks must rotate to resist overfitting",
                "margin engine for distribution-settled swaps is novel",
            ],
            market_demand_score=6.0,
            evidence_level="INFERENCE",
        ),
    },
    "Fee-Tier Voted Model Registry": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Compound/Governor parameter votes",
                    similarity_note="Voted parameter changes deployed; "
                    "weight is token stock, not decaying fee flow.",
                ),
                dict(
                    name="Conviction voting (1Hive)",
                    similarity_note="Decay-weighted voting exists "
                    "academically; not fee-paid nor outcome-rebated.",
                ),
                dict(
                    name="Treasury-backed fee parameter governance (lab r9)",
                    similarity_note="The lab's own same-round candidate "
                    "with performance bonds; this one differs in decaying "
                    "fee-paid weight and registry framing.",
                ),
            ],
            search_queries=[
                "fee paid voting weight decay governance",
                "usage weighted model registry",
                "volume regression rebate governance",
            ],
            sources=[
                dict(
                    title="Compound governance documentation",
                    url="https://compound.finance/governance",
                    source_type="protocol_doc",
                ),
                dict(
                    title="1Hive conviction voting",
                    url="https://1hive.org",
                    source_type="protocol_doc",
                ),
            ],
            findings=[
                "FACT: token-weighted parameter votes are deployed.",
                "FACT: decay-weighted voting exists (conviction voting).",
                "INFERENCE: decaying fee-paid weight plus volume-regression "
                "rebates is a compositional variant of deployed "
                "governance.",
            ],
            confidence=0.5,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. The composition is "
            "adjacent to deployed governance.",
        ),
        "economist": dict(
            summary="Decaying fee-paid weight is the correct flow-vs-stock "
            "governance correction; volume-regression rebates make "
            "misgovernance compensable to the users who suffered it.",
            concerns=[
                dict(
                    topic="corpus overlap",
                    note="Same-round overlap with the treasury-backed "
                    "governance candidate on the governance pattern; the "
                    "filter or red team should differentiate rather than "
                    "advance both as near-duplicates.",
                    severity=4.0,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Capture requires sustained current usage, not stock",
                "Regressions are automatically rebated",
            ],
            economic_coherence_score=6.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Inference buyers and model providers using "
            "fee-tiered model registries",
            problem="Registry fee-tier decisions ignore the users who "
            "actually pay the inference fees.",
            existing_alternatives=[
                "operator-set tiers",
                "token-holder votes",
                "off-chain councils",
            ],
            market_size_note="Model registries are concentrated in a few "
            "operators; demand is real but niche until registries "
            "decentralize.",
            adoption_barriers=[
                "fee ledger granularity per model endpoint",
                "registry must matter enough to govern",
            ],
            market_demand_score=5.0,
            evidence_level="INFERENCE",
        ),
    },
    "Vol-Adaptive Market Making Rebate Curve for Compute Futures": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[
                dict(
                    name="Dynamic-fee AMMs (vol-keyed)",
                    similarity_note="Volatility-keyed fee schedules are "
                    "deployed; paying for distribution-stabilizing depth "
                    "is not.",
                ),
                dict(
                    name="CEX maker rebate tiers",
                    similarity_note="Volume-tiered rebates are standard; "
                    "not volatility-adaptive nor depth-location-aware.",
                ),
                dict(
                    name="Adverse-selection taxed clearing (lab r8)",
                    similarity_note="The lab's own flow-taxed rebates; this "
                    "candidate keys the curve to benchmark-distribution "
                    "volatility.",
                ),
            ],
            search_queries=[
                "volatility adaptive maker rebate",
                "depth location aware rewards market",
                "distribution stabilizing liquidity rewards",
            ],
            sources=[
                dict(
                    title="AMM dynamic fee literature",
                    url="https://arxiv.org",
                    source_type="paper",
                ),
                dict(
                    title="CME maker rebate schedules (public docs)",
                    url="https://www.cmegroup.com",
                    source_type="other",
                ),
            ],
            findings=[
                "FACT: volume-tiered maker rebates are universal in "
                "tradfi venues.",
                "FACT: volatility-adjusted fees exist in AMM designs.",
                "INFERENCE: paying for the depth that stabilizes a "
                "benchmark DISTRIBUTION (not a price) is the distinct "
                "step.",
            ],
            confidence=0.5,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources. Distribution-stabilizing "
            "rebate curves appear adjacent to deployed rebate mechanics.",
        ),
        "economist": dict(
            summary="Paying for the depth profile that stabilizes the "
            "settlement reference aligns maker income with venue health "
            "rather than raw churn; the deterministic published curve "
            "removes discretionary gaming.",
            concerns=[
                dict(
                    topic="curve front-running",
                    note="The volatility index is computable from public "
                    "quotes, so makers can pre-position where the curve "
                    "will pay; bounded steps and delayed index "
                    "publication bound the edge.",
                    severity=5.5,
                    evidence_level="INFERENCE",
                ),
            ],
            strengths=[
                "Pays for stabilization, not churn",
                "Deterministic curve, bond-gated parameter changes",
            ],
            economic_coherence_score=6.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Compute-futures venues and professional market "
            "makers in compute derivative boards",
            problem="Rebate schedules pay for volume rather than venue "
            "stabilization, misaligning maker income with board health.",
            existing_alternatives=[
                "volume-tiered rebates",
                "flat maker programs",
                "internalization agreements",
            ],
            market_size_note="Every new derivatives venue deploys maker "
            "programs; compute futures boards are the emerging venue "
            "class.",
            adoption_barriers=[
                "depends on compute futures boards existing",
                "index publication delay trades off transparency vs "
                "front-running",
            ],
            market_demand_score=5.0,
            evidence_level="INFERENCE",
        ),
    },
}


def candidate_name_from(messages: list[dict]) -> str | None:
    for m in messages:
        c = re.search(r"CANDIDATE: (.+?)\ncategory", m["content"])
        if c:
            return c.group(1).strip()
    return None


BUILDERS = {
    "PriorArtReport": (PriorArtReport, "prior_art"),
    "EconomistReport": (EconomistReport, "economist"),
    "MarketReport": (MarketReport, "market"),
}


def main() -> None:
    bridge = AgentBridgeProvider()
    installed = 0
    for f in sorted(glob.glob(".bridge/requests/*.json")):
        with open(f) as fh:
            d = json.load(fh)
        schema = d.get("schema")
        if schema not in BUILDERS or d.get("status") != "pending":
            continue
        name = candidate_name_from(d["messages"])
        if name is None or name not in R:
            continue
        cls, kind = BUILDERS[schema]
        payload = cls.model_validate(R[name][kind]).model_dump()
        bridge.install_answer(d["id"], payload)
        installed += 1
    print(f"installed {installed} research answers")


if __name__ == "__main__":
    main()
