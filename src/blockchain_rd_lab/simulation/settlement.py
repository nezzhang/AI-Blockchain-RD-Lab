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
            if p.proposer not in {v.validator_id for v in self.validators}:
                failures.append(f"unknown_proposer:{p.proposal_id}")
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
        qualified = [
            p for p in proposals
            if proposal_weights.get(p.proposal_id, 0)
            >= self.required_quorum
        ]
        conflict = len({p.proposal_id for p in proposals}) > 1
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


__all__ = [
    "AccountState", "ApplyResult", "Proposal", "SettlementResult",
    "SettlementSimulator", "Transaction", "Validator", "Vote",
    "apply_proposal", "apply_transaction", "make_proposal",
]
