from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.research import (
    EconomicConcern,
    EconomistReport,
    MarketReport,
    PriorArtReport,
    ResearchSource,
    SimilarMechanism,
)

REQ = REPO = Path('.bridge/requests')

prior = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="MACD fast/slow EMA divergence indicator",
            url="https://www.investopedia.com/terms/m/macd.asp",
            similarity_note=(
                "The fast/slow EMA divergence gate is the standard MACD "
                "construction from technical analysis; here it gates a "
                "collateralized fee band, not a trading signal"
            ),
        ),
        SimilarMechanism(
            name="Tellor dispute-bonded oracle reports",
            url="https://docs.tellor.io/",
            similarity_note=(
                "Reporter bonds forfeited on disputed values, but "
                "forfeiture keys to discrete disputes rather than "
                "sustained EMA divergence"
            ),
        ),
        SimilarMechanism(
            name="Target-zone band models in FX (BIS literature)",
            url="https://www.bis.org/",
            similarity_note=(
                "Band exceedance with mean reversion inside the zone; "
                "the level-recentering construction differs (the band "
                "follows the level, not a fixed target)"
            ),
        ),
    ],
    search_queries=[
        "fast slow EMA divergence gate collateral forfeiture",
        "forecast band oracle reporter bond sustained exceedance",
        "level re-centering band mechanism MACD oracle",
    ],
    sources=[
        ResearchSource(title="MACD indicator reference",
                       url="https://www.investopedia.com/terms/m/macd.asp",
                       source_type="web"),
        ResearchSource(title="Tellor oracle documentation",
                       url="https://docs.tellor.io/", source_type="protocol_doc"),
        ResearchSource(title="BIS FX target-zone studies",
                       url="https://www.bis.org/", source_type="intl_org"),
    ],
    findings=[
        "FACT: the fast/slow EMA divergence construction is the MACD "
        "indicator, standard in market technical analysis.",
        "INFERENCE: no searched source applies divergence gating to "
        "collateralized forecast bands — existing bonded oracles forfeit "
        "on discrete dispute events.",
        "HYPOTHESIS: the re-centering property (one bounded transient "
        "per permanent shift) is the economically meaningful difference "
        "from anchored-band constructions.",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: MACD divergence gating is standard in "
        "technical analysis and bonded fee oracles exist in protocol "
        "documentation, but no substantially similar implementation was "
        "identified in the searched sources for a divergence-gated "
        "collateralized forecast band."
    ),
)

econ = EconomistReport(
    summary=(
        "Keying mis-banding to sustained fast/slow EMA divergence makes "
        "the forfeiture rule economically consistent with what a "
        "forecaster actually claims: a SUSTAINED level path. "
        "Zero-mean oscillation leaves both EMAs flat (no forfeit); a "
        "permanent shift yields one bounded re-centering transient "
        "(forfeit once, then re-band honestly); persistent mis-banding "
        "integrates exceedance and forfeits at 1.2:0.5. The residual "
        "cost is the re-banding window: reporters forfeit a bounded "
        "amount on every genuine regime shift."
    ),
    concerns=[
        EconomicConcern(
            topic="re-banding window cost",
            note=(
                "Every permanent level shift imposes one bounded "
                "transient forfeiture on honest reporters; frequent "
                "regime shifts make the meter expensive to report for, "
                "recruiting only reporters with superior shift "
                "forecasts — which is arguably the intended selection."
            ),
            severity=5.5,
        ),
        EconomicConcern(
            topic="divergence-band calibration",
            note=(
                "The band and vol-discount (omega) parameters trade off "
                "re-banding cost against sustained-mis-banding "
                "sensitivity; mis-calibration in either direction "
                "reintroduces an r11-style residual."
            ),
            severity=5.0,
        ),
    ],
    strengths=[
        "Forfeiture semantics finally match forecast semantics: "
        "forecasters are persistently wrong, not instantaneously.",
        "Forfeit/compensation ratio above one makes every sustained "
        "mis-banding strategy strictly net-negative.",
    ],
    economic_coherence_score=7.3,
)

market = MarketReport(
    customer=(
        "L2 sequencers and fee-oracle consumers who need safe-to-quote "
        "fee bands, plus reporters willing to post bonds for band fees"
    ),
    problem=(
        "Fee oracles are uncollateralized, and prior band designs either "
        "harvest honest bonds under oscillation or forfeit forever under "
        "permanent shifts — no construction priced sustained mis-banding "
        "without double-charging honest re-banding"
    ),
    existing_alternatives=[
        "EIP-1559 base fee (algorithmic, not forecast-collateralized)",
        "Median-of-fees oracles without bonds",
        "Off-chain fee SaaS tiers (Alchemy/Infura style)",
    ],
    market_size_note=(
        "L2/appchain fee-oracle demand is order-of-magnitude millions in "
        "notional bonds if adopted; the divergence-gated niche is a "
        "quality improvement on bonded-band designs."
    ),
    adoption_barriers=[
        "Reporters must post bonds and accept bounded re-banding forfeits",
        "Divergence-gate calibration needs historical band data",
    ],
    market_demand_score=6.0,
)

answers = {'030f0c3c70819126': econ, '9c53808371163451': prior, 'dc089e483e9606e5': market}
p = AgentBridgeProvider()
for rid, ans in answers.items():
    p.install_answer(rid, ans.model_dump(mode='json'))
    print('installed', rid, type(ans).__name__)
