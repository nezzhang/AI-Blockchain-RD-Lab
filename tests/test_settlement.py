from blockchain_rd_lab.simulation.settlement import (
    AccountState,
    SettlementSimulator,
    Transaction,
    Validator,
    Vote,
    apply_transaction,
    make_proposal,
)


def base():
    return AccountState({"a": 100, "b": 0}, {"a": 0, "b": 0})


def vals():
    return tuple(Validator(f"v{i}", 1) for i in range(1, 5))


def votes_for(proposal_id, validators):
    return tuple(Vote(1, 0, proposal_id, v, 1) for v in validators)


def test_transfer_atomic_and_nonce():
    r = apply_transaction(base(), Transaction("t", "a", "b", 10, 0))
    assert r.accepted and r.state.balances == {"a": 90, "b": 10}
    bad = apply_transaction(r.state, Transaction("t2", "a", "b", 200, 1))
    assert not bad.accepted and bad.state == r.state


def test_proposal_id_is_canonical_and_order_sensitive():
    p = make_proposal(1, 0, base(), ("a", "b"), "v1")
    q = make_proposal(1, 0, base(), ("b", "a"), "v1")
    assert p.proposal_id != q.proposal_id
    assert p == make_proposal(1, 0, base(), ("a", "b"), "v1")


def test_quorum_finalizes_atomically():
    tx = Transaction("t", "a", "b", 10, 0)
    p = make_proposal(1, 0, base(), ("t",), "v1")
    r = SettlementSimulator(base(), vals()).settle(
        (p,), votes_for(p.proposal_id, ("v1", "v2", "v3")), {"t": tx}
    )
    assert r.finalized and r.vote_weight == 3 and r.state.balances["b"] == 10


def test_split_conflict_does_not_finalize():
    p = make_proposal(1, 0, base(), (), "v1")
    q = make_proposal(1, 0, base(), ("x",), "v2")
    votes = (
        Vote(1, 0, p.proposal_id, "v1", 1),
        Vote(1, 0, p.proposal_id, "v2", 1),
        Vote(1, 0, q.proposal_id, "v3", 1),
        Vote(1, 0, q.proposal_id, "v4", 1),
    )
    r = SettlementSimulator(base(), vals()).settle((p, q), votes, {})
    assert not r.finalized and r.conflict_count == 1


def test_equivocation_is_observed_not_silently_finalized():
    p = make_proposal(1, 0, base(), (), "v1")
    q = make_proposal(1, 0, base(), (), "v2")
    votes = (
        Vote(1, 0, p.proposal_id, "v1", 1),
        Vote(1, 0, q.proposal_id, "v1", 1),
        Vote(1, 0, p.proposal_id, "v2", 1),
        Vote(1, 0, q.proposal_id, "v3", 1),
    )
    r = SettlementSimulator(base(), vals()).settle((p, q), votes, {})
    assert not r.finalized and r.equivocation_count == 1


def test_deterministic_run():
    p = make_proposal(1, 0, base(), (), "v1")
    votes = votes_for(p.proposal_id, ("v1", "v2", "v3"))
    s = SettlementSimulator(base(), vals())
    assert s.settle((p,), votes, {}) == s.settle((p,), votes, {})


def test_weighted_quorum_exact():
    validators = (Validator("a", 2), Validator("b", 1), Validator("c", 1))
    p = make_proposal(1, 0, base(), (), "a")
    one = Vote(1, 0, p.proposal_id, "a", 2)
    assert not SettlementSimulator(base(), validators).settle((p,), (one,), {}).finalized
    two = (one, Vote(1, 0, p.proposal_id, "b", 1))
    assert SettlementSimulator(base(), validators).settle((p,), two, {}).finalized
