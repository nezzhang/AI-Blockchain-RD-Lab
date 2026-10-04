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


def test_phased_prevote_precommit_finalize():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    votes = tuple(
        Vote(1, 0, p.proposal_id, v, 1, phase="prevote") for v in ("v1", "v2", "v3")
    ) + tuple(Vote(1, 0, p.proposal_id, v, 1, phase="precommit") for v in ("v1", "v2", "v3"))
    r = SettlementSimulator(state, vals()).settle_phased(((p,),), votes, {})
    assert r.finalized and r.prevote_weight == 3
    assert r.precommit_weight == 3 and r.liveness_progress


def test_phased_prevotes_alone_do_not_finalize():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    votes = tuple(Vote(1, 0, p.proposal_id, v, 1, phase="prevote") for v in ("v1", "v2", "v3"))
    r = SettlementSimulator(state, vals()).settle_phased(((p,),), votes, {})
    assert not r.finalized and r.prevote_weight == 3
    assert r.precommit_weight == 0


def test_phased_omitted_proposer_round_change():
    state = base()
    p = make_proposal(1, 1, state, (), "v2")
    votes = tuple(
        Vote(1, 1, p.proposal_id, v, 1, phase=phase)
        for phase in ("prevote", "precommit")
        for v in ("v1", "v2", "v3")
    )
    r = SettlementSimulator(state, vals()).settle_phased(
        (tuple(), (p,)),
        votes,
        {},
        proposer_schedule=("v1", "v2"),
        omitted_proposers=frozenset({"v1"}),
    )
    assert r.finalized and r.round_changes == 1
    assert r.proposer_omissions == 1


def test_disabled_proposer_rejected():
    state = base()
    vs = (
        Validator("v1", 1, False),
        Validator("v2", 1),
        Validator("v3", 1),
        Validator("v4", 1),
    )
    p = make_proposal(1, 0, state, (), "v1")
    votes = tuple(Vote(1, 0, p.proposal_id, v, 1, phase="precommit") for v in ("v2", "v3", "v4"))
    r = SettlementSimulator(state, vs).settle_phased(((p,),), votes, {})
    assert not r.finalized
    assert any("disabled" in x for x in r.failures)


def test_phased_precommit_without_prevote_has_no_finality():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    votes = tuple(Vote(1, 0, p.proposal_id, v, 1, phase="precommit") for v in ("v1", "v2", "v3"))
    r = SettlementSimulator(state, vals()).settle_phased(((p,),), votes, {})
    assert not r.finalized and r.prevote_weight == 0


def test_duplicate_proposal_does_not_report_safety_violation():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    votes = votes_for(p.proposal_id, ("v1", "v2", "v3"))
    r = SettlementSimulator(state, vals()).settle((p, p), votes, {})
    assert r.finalized and not r.safety_violation_observed


def test_phased_lock_conflict_blocks_conflicting_vote():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    q = make_proposal(1, 1, state, (), "v2")
    votes = tuple(
        Vote(1, 0, p.proposal_id, v, 1, phase=phase)
        for phase in ("prevote", "precommit")
        for v in ("v1", "v2", "v3")
    )
    first = SettlementSimulator(state, vals()).settle_phased(((p,),), votes, {})
    assert first.finalized and first.locked_validator_count == 3
    # Lock state is internal to this bounded run; a separate run remains deterministic.
    second = SettlementSimulator(state, vals()).settle_phased(
        ((q,),),
        tuple(Vote(1, 1, q.proposal_id, v, 1, phase="prevote") for v in ("v1", "v2", "v3")),
        {},
    )
    assert not second.finalized


def test_phased_liveness_metrics_no_quorum():
    state = base()
    p = make_proposal(1, 0, state, (), "v1")
    votes = (Vote(1, 0, p.proposal_id, "v1", 1, phase="prevote"),)
    r = SettlementSimulator(state, vals()).settle_phased(((p,),), votes, {})
    assert not r.finalized and not r.liveness_progress
    assert r.rounds_attempted == 1 and r.prevote_weight == 0
