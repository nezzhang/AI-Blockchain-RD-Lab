"""Research-only deterministic settlement state machine (§41).

This is a synthetic state-machine experiment, not a blockchain node or
consensus implementation. It has no networking, clocks, keys, signatures,
wallets, contracts, token issuance, or deployment behavior.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class AccountState:
    balances: dict[str, int]
    nonces: dict[str, int]

    def canonical(self) -> str:
        return json.dumps(
            {"balances": self.balances, "nonces": self.nonces},
            sort_keys=True, separators=(",", ":"),
        )

    @property
    def state_hash(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


@dataclass(frozen=True)
class Transaction:
    tx_id: str
    sender: str
    recipient: str
    amount: int
    nonce: int
    fee: int = 0


@dataclass(frozen=True)
class Validator:
    validator_id: str
    weight: int
    enabled: bool = True


@dataclass(frozen=True)
class Proposal:
    height: int
    round: int
    parent_state_hash: str
    tx_ids: tuple[str, ...]
    proposer: str
    proposal_id: str


@dataclass(frozen=True)
class Vote:
    height: int
    round: int
    proposal_id: str
    validator_id: str
    weight: int
    phase: str = "legacy"


@dataclass(frozen=True)
class ApplyResult:
    accepted: bool
    state: AccountState
    reason: str | None = None
    tx_id: str | None = None


def apply_transaction(state: AccountState, tx: Transaction) -> ApplyResult:
    """Apply one integer transfer atomically, or return unchanged state."""
    if tx.amount <= 0 or tx.fee < 0:
        return ApplyResult(False, state, "non_positive_amount_or_fee", tx.tx_id)
    if tx.sender == tx.recipient:
        return ApplyResult(False, state, "self_transfer", tx.tx_id)
    if tx.sender not in state.balances or tx.recipient not in state.balances:
        return ApplyResult(False, state, "unknown_account", tx.tx_id)
    expected = state.nonces.get(tx.sender, 0)
    if tx.nonce != expected:
        return ApplyResult(False, state, "wrong_nonce", tx.tx_id)
    if state.balances[tx.sender] < tx.amount + tx.fee:
        return ApplyResult(False, state, "insufficient_balance", tx.tx_id)
    balances = dict(state.balances)
    nonces = dict(state.nonces)
    balances[tx.sender] -= tx.amount + tx.fee
    balances[tx.recipient] += tx.amount
    nonces[tx.sender] = expected + 1
    return ApplyResult(True, AccountState(balances, nonces), tx_id=tx.tx_id)


def apply_proposal(state: AccountState, txs: tuple[Transaction, ...]) -> ApplyResult:
    """Apply all transactions atomically; invalid proposal commits nothing."""
    current = state
    seen: set[str] = set()
    for tx in txs:
        if tx.tx_id in seen:
            return ApplyResult(False, state, "duplicate_transaction_id", tx.tx_id)
        seen.add(tx.tx_id)
        result = apply_transaction(current, tx)
        if not result.accepted:
            return ApplyResult(False, state, f"invalid:{result.reason}", tx.tx_id)
        current = result.state
    return ApplyResult(True, current)


def make_proposal(height: int, round: int, parent: AccountState,
                  tx_ids: tuple[str, ...], proposer: str) -> Proposal:
    payload = {
        "height": height, "round": round,
        "parent_state_hash": parent.state_hash,
        "tx_ids": tx_ids, "proposer": proposer,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    pid = hashlib.sha256(canonical.encode()).hexdigest()
    return Proposal(height, round, parent.state_hash, tx_ids, proposer, pid)


@dataclass(frozen=True)
class SettlementResult:
    finalized: bool
    proposal_id: str | None
    state: AccountState
    quorum_required: int
    vote_weight: int
    conflict_count: int
    equivocation_count: int
    safety_violation_observed: bool
    failures: tuple[str, ...]
    equivocation_evidence: tuple[str, ...] = ()
    prevote_weight: int = 0
    precommit_weight: int = 0
    rounds_attempted: int = 1
    round_changes: int = 0
    proposer_omissions: int = 0
    locked_validator_count: int = 0
    lock_conflict_count: int = 0
    liveness_progress: bool = False
    certificate_observed: bool = False


class SettlementSimulator:
    """Bounded in-memory settlement experiment; never connects externally."""
    def __init__(self, genesis: AccountState, validators: tuple[Validator, ...],
                 quorum_numerator: int = 2, quorum_denominator: int = 3) -> None:
        if not validators or quorum_denominator <= 0:
            raise ValueError("validators and quorum required")
        if not 0 < quorum_numerator <= quorum_denominator:
            raise ValueError("invalid quorum")
        if any(v.weight <= 0 for v in validators):
            raise ValueError("validator weights must be positive")
        self.genesis = genesis
        self.validators = validators
        self.numerator = quorum_numerator
        self.denominator = quorum_denominator

    @property
    def required_quorum(self) -> int:
        total = sum(v.weight for v in self.validators if v.enabled)
        return ceil(total * self.numerator / self.denominator)

    def settle(self, proposals: tuple[Proposal, ...], votes: tuple[Vote, ...],
               transactions: dict[str, Transaction], height: int = 1,
               round: int = 0) -> SettlementResult:
        failures: list[str] = []
        valid: dict[str, AccountState] = {}
        for p in proposals:
            if (
                p.height != height
                or p.round != round
                or p.parent_state_hash != self.genesis.state_hash
            ):
                failures.append(f"invalid_parent_or_round:{p.proposal_id}")
                continue
            validator_by_id = {v.validator_id: v for v in self.validators}
            if p.proposer not in validator_by_id:
                failures.append(f"unknown_proposer:{p.proposal_id}")
                continue
            if not validator_by_id[p.proposer].enabled:
                failures.append(f"disabled_proposer:{p.proposal_id}")
                continue
            txs = tuple(transactions[x] for x in p.tx_ids if x in transactions)
            if len(txs) != len(p.tx_ids):
                failures.append(f"unknown_transaction:{p.proposal_id}")
                continue
            applied = apply_proposal(self.genesis, txs)
            if applied.accepted:
                valid[p.proposal_id] = applied.state
            else:
                failures.append(f"invalid_proposal:{p.proposal_id}:{applied.reason}")
        weights = {v.validator_id: v.weight for v in self.validators if v.enabled}
        counted: dict[str, set[str]] = {}
        equivocation: set[str] = set()
        for vote in votes:
            if vote.height != height or vote.round != round or vote.validator_id not in weights:
                failures.append(f"ignored_vote:{vote.validator_id}")
                continue
            counted.setdefault(vote.validator_id, set()).add(vote.proposal_id)
            if len(counted[vote.validator_id]) > 1:
                equivocation.add(vote.validator_id)
        proposal_weights: dict[str, int] = {}
        for vote in votes:
            if (
                vote.validator_id in weights
                and vote.proposal_id in valid
                and len(counted.get(vote.validator_id, set())) == 1
            ):
                proposal_weights[vote.proposal_id] = (
                    proposal_weights.get(vote.proposal_id, 0)
                    + weights[vote.validator_id]
                )
        unique_proposals = {p.proposal_id: p for p in proposals}
        qualified = [
            p for p in unique_proposals.values()
            if proposal_weights.get(p.proposal_id, 0)
            >= self.required_quorum
        ]
        conflict = len(unique_proposals) > 1
        safety = len(qualified) > 1
        if safety:
            failures.append("multiple_quorum_proposals")
        if len(qualified) != 1:
            return SettlementResult(
                False, None, self.genesis, self.required_quorum,
                max(proposal_weights.values(), default=0), int(conflict),
                len(equivocation), safety, tuple(failures)
            )
        chosen = qualified[0]
        return SettlementResult(
            True, chosen.proposal_id, valid[chosen.proposal_id],
            self.required_quorum, proposal_weights[chosen.proposal_id],
            int(conflict), len(equivocation), safety, tuple(failures)
        )


    def settle_phased(
        self,
        proposals_by_round: tuple[tuple[Proposal, ...], ...],
        votes: tuple[Vote, ...],
        transactions: dict[str, Transaction],
        *,
        height: int = 1,
        start_round: int = 0,
        proposer_schedule: tuple[str, ...] | None = None,
        omitted_proposers: frozenset[str] = frozenset(),
        continue_after_certificate: bool = False,
    ) -> SettlementResult:
        """Explicit prevote -> precommit -> finalize research run.

        Bounded, deterministic, and non-production: locks and phase
        certificates are abstract measurements, not cryptographic proofs.
        """
        failures: list[str] = []
        enabled = {v.validator_id: v for v in self.validators if v.enabled}
        configured = {v.validator_id: v for v in self.validators}
        locks: dict[str, tuple[int, str]] = {}
        prevote_weight = precommit_weight = 0
        equivocations: set[str] = set()
        equivocation_evidence: set[str] = set()
        lock_conflicts = 0
        omissions = 0
        rounds = 0
        certificate_observed = False
        for idx, proposals in enumerate(proposals_by_round):
            current_round = start_round + idx
            rounds += 1
            scheduled = (
                proposer_schedule[idx]
                if proposer_schedule and idx < len(proposer_schedule)
                else None
            )
            if scheduled is not None and (
                scheduled in omitted_proposers
                or scheduled not in enabled
            ):
                omissions += 1
                failures.append(f"proposer_omission:{scheduled}:{current_round}")
                continue
            valid: dict[str, AccountState] = {}
            for proposal in {p.proposal_id: p for p in proposals}.values():
                if (
                    proposal.height != height
                    or proposal.round != current_round
                    or proposal.parent_state_hash != self.genesis.state_hash
                ):
                    failures.append(f"invalid_parent_or_round:{proposal.proposal_id}")
                    continue
                if scheduled is not None and proposal.proposer != scheduled:
                    failures.append(f"unexpected_proposer:{proposal.proposal_id}")
                    continue
                proposer = configured.get(proposal.proposer)
                if proposer is None or not proposer.enabled:
                    failures.append(f"disabled_proposer:{proposal.proposal_id}")
                    continue
                txs = tuple(transactions[x] for x in proposal.tx_ids if x in transactions)
                if len(txs) != len(proposal.tx_ids):
                    failures.append(f"unknown_transaction:{proposal.proposal_id}")
                    continue
                applied = apply_proposal(self.genesis, txs)
                if applied.accepted:
                    valid[proposal.proposal_id] = applied.state
            phase_votes: dict[str, dict[str, set[str]]] = {
                "prevote": {},
                "precommit": {},
            }
            for vote in votes:
                if vote.height != height or vote.round != current_round:
                    continue
                if vote.phase not in phase_votes or vote.validator_id not in enabled:
                    continue
                if vote.proposal_id not in valid:
                    continue
                lock = locks.get(vote.validator_id)
                if lock and lock[1] != vote.proposal_id:
                    lock_conflicts += 1
                    failures.append(f"lock_conflict:{vote.validator_id}")
                    continue
                key = vote.validator_id
                seen = phase_votes[vote.phase].setdefault(key, set())
                seen.add(vote.proposal_id)
                if len(seen) > 1:
                    equivocations.add(vote.validator_id)
                    evidence = ":".join(
                        (
                            vote.validator_id,
                            vote.phase,
                            str(height),
                            str(current_round),
                            *sorted(seen),
                        )
                    )
                    equivocation_evidence.add(evidence)
            def weight_for(
                phase: str,
                proposal_id: str,
                _phase_votes=phase_votes,
                _valid=valid,
            ) -> int:
                return sum(
                    enabled[vid].weight
                    for vid, ids in _phase_votes[phase].items()
                    if ids == {proposal_id} and proposal_id in _valid
                )
            prev_candidates = [
                pid for pid in valid if weight_for("prevote", pid) >= self.required_quorum
            ]
            if not prev_candidates:
                continue
            candidate = sorted(prev_candidates)[0]
            prevote_weight = weight_for("prevote", candidate)
            matching_precommit = {
                vid
                for vid, ids in phase_votes["precommit"].items()
                if ids == {candidate}
                and phase_votes["prevote"].get(vid) == {candidate}
            }
            precommit_weight = sum(
                enabled[vid].weight for vid in matching_precommit
            )
            if precommit_weight < self.required_quorum:
                continue
            for vid in matching_precommit:
                locks[vid] = (current_round, candidate)
            certificate_observed = True
            if not continue_after_certificate:
                return SettlementResult(
                    finalized=True,
                    proposal_id=candidate,
                    state=valid[candidate],
                    quorum_required=self.required_quorum,
                    vote_weight=precommit_weight,
                    conflict_count=int(len(valid) > 1),
                    equivocation_count=len(equivocations),
                    safety_violation_observed=False,
                    failures=tuple(failures),
                    prevote_weight=prevote_weight,
                    precommit_weight=precommit_weight,
                    rounds_attempted=rounds,
                    round_changes=max(0, rounds - 1),
                    proposer_omissions=omissions,
                    locked_validator_count=len(locks),
                    lock_conflict_count=lock_conflicts,
                    liveness_progress=True,
                    certificate_observed=True,
                    equivocation_evidence=tuple(sorted(equivocation_evidence)),
                )
        return SettlementResult(
            finalized=False,
            proposal_id=None,
            state=self.genesis,
            quorum_required=self.required_quorum,
            vote_weight=max(prevote_weight, precommit_weight),
            conflict_count=0,
            equivocation_count=len(equivocations),
            safety_violation_observed=False,
            failures=tuple(failures),
            prevote_weight=prevote_weight,
            precommit_weight=precommit_weight,
            rounds_attempted=rounds,
            round_changes=max(0, rounds - 1),
            proposer_omissions=omissions,
            locked_validator_count=len(locks),
            lock_conflict_count=lock_conflicts,
            liveness_progress=False,
            certificate_observed=certificate_observed,
            equivocation_evidence=tuple(sorted(equivocation_evidence)),
        )


__all__ = [
    "AccountState", "ApplyResult", "Proposal", "SettlementResult",
    "SettlementSimulator", "Transaction", "Validator", "Vote",
    "apply_proposal", "apply_transaction", "make_proposal",
]
