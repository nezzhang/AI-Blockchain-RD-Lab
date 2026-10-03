"""§21 census for the research-only settlement state-machine simulator.

No network, wallet, key, signature, deployment, or production consensus.
Synthetic integer accounts, proposals, votes, and scripted faults only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import ExperimentRecord
from blockchain_rd_lab.simulation.settlement import (
    AccountState,
    SettlementSimulator,
    Transaction,
    Validator,
    Vote,
    make_proposal,
)

CENSUS_ID = "r48-settlement-state-machine-census"


def main() -> None:
    state = AccountState({"a": 100, "b": 0}, {"a": 0, "b": 0})
    validators = tuple(Validator(f"v{i}", 1) for i in range(1, 5))
    sim = SettlementSimulator(state, validators)
    tx = Transaction("tx-valid", "a", "b", 10, 0)
    valid = make_proposal(1, 0, state, (tx.tx_id,), "v1")
    empty = make_proposal(1, 0, state, (), "v1")
    conflict = make_proposal(1, 0, state, (), "v2")
    scenarios = []
    cases = [
        ("honest_quorum", (valid,), (valid.proposal_id, "v1", "v2", "v3"), {tx.tx_id: tx}),
        ("no_quorum", (valid,), (valid.proposal_id, "v1"), {tx.tx_id: tx}),
        ("conflicting_split", (empty, conflict), (empty.proposal_id, "v1", "v2"), {}),
        ("equivocation", (empty, conflict), (empty.proposal_id, "v1", "v2"), {}),
        ("invalid_transaction", (make_proposal(1, 0, state, ("bad",), "v1"),), ("",), {}),
    ]
    for name, proposals, vote_spec, txs in cases:
        if name == "honest_quorum":
            votes = tuple(Vote(1, 0, vote_spec[0], v, 1) for v in vote_spec[1:])
        elif name == "no_quorum":
            votes = (Vote(1, 0, vote_spec[0], vote_spec[1], 1),)
        elif name == "conflicting_split":
            votes = (
                Vote(1, 0, empty.proposal_id, "v1", 1),
                Vote(1, 0, conflict.proposal_id, "v2", 1),
            )
        elif name == "equivocation":
            votes = (
                Vote(1, 0, empty.proposal_id, "v1", 1),
                Vote(1, 0, conflict.proposal_id, "v1", 1),
                Vote(1, 0, empty.proposal_id, "v2", 1),
            )
        else:
            votes = tuple()
        r = sim.settle(proposals, votes, txs)
        scenarios.append(
            {
                "scenario": name,
                "finalized": r.finalized,
                "quorum_required": r.quorum_required,
                "vote_weight": r.vote_weight,
                "conflict_count": r.conflict_count,
                "equivocation_count": r.equivocation_count,
                "safety_violation_observed": r.safety_violation_observed,
                "failures": r.failures,
                "state_hash": r.state.state_hash,
            }
        )
    rec = ExperimentRecord(
        experiment_id=CENSUS_ID,
        candidate_id="research-settlement-simulator",
        kind="settlement_state_machine",
        timestamp=datetime.now(UTC),
        git_commit="r48",
        parameters={
            "protocol_version": "settlement-sm-0.1.0",
            "quorum": "2/3",
            "validators": 4,
            "production": False,
            "network": False,
        },
        results={
            "rows": scenarios,
            "total_runs": len(scenarios),
            "scope": (
                "synthetic deterministic research-only; no "
                "network/wallet/signature/deployment"
            ),
        },
    )
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    with db._session() as s:
        s.execute(
            text("DELETE FROM experiments WHERE experiment_id = :eid"),
            {"eid": CENSUS_ID},
        )
    db.save_experiment(rec)
    print(f"stored {CENSUS_ID}: {len(scenarios)} scenarios")


if __name__ == "__main__":
    main()
