"""Round 13: v1 models for the persistent-EMA successors (authored,
smoke-gated in-memory; the formalize answer carries them to the DB —
the r12 no-double-save flow)."""
from __future__ import annotations

import json

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    MechanismSimulation,
    ScenarioBattery,
    ScenarioKind,
    scenario_config,
)
from blockchain_rd_lab.simulation.adversarial import (
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)

ORACLE = 'cand-d656eeeaeca1'
JOULE = 'cand-4e292d1b929b'


def oracle_model(db: LabDatabase) -> MathModel:
    pred = json.loads(db.get_latest_math_model('cand-b2b411464015'))
    vs = [
        {'name': 'anchor', 'symbol': 'X_t', 'role': 'input', 'units': 'unit',
         'description': 'anchor level'},
        {'name': 'anchor_delta', 'symbol': 'dX_t', 'role': 'input', 'units': 'unit',
         'description': 'anchor change'},
        {'name': 'medium_ema', 'symbol': 'L_t', 'role': 'state', 'units': 'unit',
         'description': 'medium-speed EMA of the level'},
        {'name': 'medium_next', 'symbol': 'L_t1', 'role': 'state', 'units': 'unit',
         'description': 'next medium EMA'},
        {'name': 'ultra_ema', 'symbol': 'U_s', 'role': 'state', 'units': 'unit',
         'description': 'ultra-slow EMA of the level (regime anchor)'},
        {'name': 'ultra_next', 'symbol': 'U_s1', 'role': 'state', 'units': 'unit',
         'description': 'next ultra-slow EMA'},
        {'name': 'regime_disp', 'symbol': 'g_t', 'role': 'auxiliary', 'units': 'frac',
         'description': 'regime displacement |L-U|/U (persistent while moved)'},
        {'name': 'open_interest', 'symbol': 'O_t', 'role': 'state', 'units': 'unit',
         'description': 'posted open interest'},
        {'name': 'open_interest_next', 'symbol': 'O_t1', 'role': 'state', 'units': 'unit',
         'description': 'next open interest'},
        {'name': 'fee', 'symbol': 'F_t', 'role': 'state', 'units': 'unit',
         'description': 'protection fee premium'},
        {'name': 'fee_next', 'symbol': 'F_t1', 'role': 'state', 'units': 'unit',
         'description': 'next fee'}]
    return MathModel(
        candidate_id=ORACLE, variables=vs,
        parameters=pred['parameters'] + [
            {'name': 'kappa_l', 'symbol': 'kappa_l', 'description':
             'medium level-EMA coefficient', 'min_value': 0.05, 'max_value': 0.4,
             'default': 0.15},
            {'name': 'kappa_u', 'symbol': 'kappa_u', 'description':
             'ultra-slow level-EMA coefficient (regime anchor)',
             'min_value': 0.005, 'max_value': 0.05, 'default': 0.015},
        ],
        equations=[
            {'name': 'medium_ema',
             'expression': 'L_t1 = clip(L_t + kappa_l*(X_t - L_t), 200.0, 4000.0)',
             'description': 'medium EMA of the level (fast enough to '
                            'reprice within the crash window)'},
            {'name': 'ultra_ema',
             'expression': 'U_s1 = clip(U_s + kappa_u*(X_t - U_s), 200.0, 4000.0)',
             'description': 'ultra-slow EMA: the regime anchor — in smooth '
                            'growth L tracks U (no false alarm); after a '
                            'crash-park L stays below U (persistent gate)'},
            {'name': 'regime_disp',
             'expression': 'g_t = abs(L_t - U_s)/max(U_s,1.0)',
             'description': 'REGIME displacement: persistent while the '
                            'regime stays moved, ~0 under smooth growth '
                            'and zero-mean oscillation'},
            {'name': 'open_interest',
             'expression': 'O_t1 = clip(O_t*(1-gamma) + gamma*(oi_floor'
                           ' + 260.0*g_t + 12.0*sqrt(abs(dX_t)/max(X_t,1.0))),'
                           ' 350.0, 1600.0)',
             'description': 'open interest follows persistent regime '
                            'displacement + a crash-window kicker'},
            {'name': 'fee',
             'expression': 'F_t1 = clip(F_t*(1-delta) + delta*(600.0'
                           ' + 1300.0*g_t + 90.0*max(0.0, 1200.0-O_t1)/100.0'
                           ' + 20.0*min(1.0, abs(dX_t)/max(X_t,1.0)/0.2)*10.0),'
                           ' 400.0, 2400.0)',
             'description': 'fee premium: PERSISTENT regime displacement '
                            '(cover stays priced up while the regime stays '
                            'moved — the r13 fix) + OI fallback + fast '
                            'crash kicker'},
        ],
        assumptions=pred['assumptions'], constraints=pred['constraints'],
        open_questions=['is the medium-EMA timescale fast enough to '
                        'reprice before the crash window closes?'],
        rationale=(
            'The predecessor keyed its fee to |R-1000|/|T-1000| where both '
            'EMAs reverted to the 1000 anchor once moves stopped — cover '
            'healed to 7% of peak while the level stayed -60% moved (r13 '
            'measured anchor-heal flaw). This model keys the fee to the '
            'persistent displacement between a medium-speed EMA and an '
            'ultra-slow regime-anchor EMA: in smooth growth they track '
            'together (no false premium), a crashed-and-parked market '
            'leaves the medium EMA below the anchor indefinitely (cover '
            'stays priced up while tail risk is maximal), and zero-mean '
            'oscillation leaves both flat (no wash harvest). Insurance '
            'polarity, r12 primitive, three-speed construction.'),
        version=1)


def joule_model(db: LabDatabase) -> MathModel:
    pred = json.loads(db.get_latest_math_model('cand-8212f81f4f75'))
    vs = [
        {'name': 'anchor', 'symbol': 'X_t', 'role': 'input', 'units': 'unit',
         'description': 'anchor level'},
        {'name': 'anchor_delta', 'symbol': 'dX_t', 'role': 'input', 'units': 'unit',
         'description': 'anchor change'},
        {'name': 'medium_ema', 'symbol': 'L_t', 'role': 'state', 'units': 'unit',
         'description': 'medium-speed EMA of the level'},
        {'name': 'medium_next', 'symbol': 'L_t1', 'role': 'state', 'units': 'unit',
         'description': 'next medium EMA'},
        {'name': 'ultra_ema', 'symbol': 'U_s', 'role': 'state', 'units': 'unit',
         'description': 'ultra-slow EMA of the level (regime anchor)'},
        {'name': 'ultra_next', 'symbol': 'U_s1', 'role': 'state', 'units': 'unit',
         'description': 'next ultra-slow EMA'},
        {'name': 'regime_disp', 'symbol': 'g_t', 'role': 'auxiliary', 'units': 'frac',
         'description': 'regime displacement |L-U|/U (persistent while moved)'},
        {'name': 'energy_price', 'symbol': 'P_e', 'role': 'state', 'units': 'unit',
         'description': 'delivery-denominated energy price'},
        {'name': 'energy_next', 'symbol': 'P_e1', 'role': 'state', 'units': 'unit',
         'description': 'next energy price'},
        {'name': 'drift_alarm', 'symbol': 'a_t', 'role': 'auxiliary', 'units': 'frac',
         'description': 'persistent-drift slash alarm'},
        {'name': 'escrow', 'symbol': 'J_t', 'role': 'state', 'units': 'unit',
         'description': 'provider escrow'},
        {'name': 'escrow_next', 'symbol': 'J_t1', 'role': 'state', 'units': 'unit',
         'description': 'next escrow'}]
    return MathModel(
        candidate_id=JOULE, variables=vs,
        parameters=pred['parameters'] + [
            {'name': 'kappa_l', 'symbol': 'kappa_l', 'description':
             'medium level-EMA coefficient', 'min_value': 0.05, 'max_value': 0.4,
             'default': 0.15},
            {'name': 'kappa_u', 'symbol': 'kappa_u', 'description':
             'ultra-slow level-EMA coefficient (regime anchor)',
             'min_value': 0.005, 'max_value': 0.05, 'default': 0.015},
        ],
        equations=[
            {'name': 'medium_ema',
             'expression': 'L_t1 = clip(L_t + kappa_l*(X_t - L_t), 200.0, 4000.0)',
             'description': 'medium EMA of the level'},
            {'name': 'ultra_ema',
             'expression': 'U_s1 = clip(U_s + kappa_u*(X_t - U_s), 200.0, 4000.0)',
             'description': 'ultra-slow EMA: the regime anchor'},
            {'name': 'regime_disp',
             'expression': 'g_t = abs(L_t - U_s)/max(U_s,1.0)',
             'description': 'persistent regime displacement'},
            {'name': 'energy_price',
             'expression': 'P_e1 = clip(P_e*(1-nu) + nu*(1000.0 + 1000.0*g_t'
                           ' + 120.0*min(3.0, abs(X_t-L_t)/1000.0)), 400.0, 1800.0)',
             'description': 'energy price re-prices at the new regime '
                            'rather than healing (g_t persistent)'},
            {'name': 'drift_alarm',
             'expression': 'a_t = min(1.0, max(0.0, 1000.0*g_t - 40.0'
                           ' - chi*max(0.0, (J_t-1000.0)))/120.0)',
             'description': 'alarm keyed to PERSISTENT regime displacement '
                            'with ratcheting tolerance (chi shrinks with '
                            'escrow turnover — r11 v2 discipline)'},
            {'name': 'escrow',
             'expression': 'J_t1 = clip(J_t + mu_j - 0.06*(J_t-1000.0) - psi*a_t*300.0'
                           ' - min(18.0, 8.0*sqrt(abs(dX_t)/max(X_t,1.0))), 600.0, 2200.0)',
             'description': 'escrow slashes while the alarm persists'},
        ],
        assumptions=pred['assumptions'], constraints=pred['constraints'],
        open_questions=['does the persistent alarm overcharge providers '
                        'who deliver fine at the new level?'],
        rationale=(
            'The predecessor keyed its drift alarm to |T-1000| where T '
            'reverted to 1000 once moves stopped — the alarm fired 4 '
            'steps then healed while the regime stayed moved, so defaults '
            'timed to healed windows paid no slash premium (r13 measured '
            'anchor-heal flaw). This model keys the alarm to the '
            'persistent displacement between a medium-speed EMA and an '
            'ultra-slow regime anchor: a moved regime keeps the alarm on '
            'until delivery resumes AT THE NEW LEVEL, smooth growth '
            'tracks the two EMAs together (no false alarm), and '
            'oscillation never trips it. Insurance polarity, r12 '
            'primitive, three-speed construction.'),
        version=1)


def smoke(m: MathModel) -> None:
    sim = MechanismSimulation(m)
    base = sim.run(AnchorSeriesGenerator(
        scenario_config(ScenarioKind.BASE, steps=120)).generate())
    whale = sim.run(AnchorSeriesGenerator(
        scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)).generate())
    runs = ScenarioBattery(sim, steps=120).run()
    degen = [k for k, r in runs.items() if r.degenerate]
    finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
    wash = AttackPatternBattery(m).run_pattern(
        PatternSpec(kind=AttackPattern.WASH_FLOW, steps=60))
    cp = AttackPatternBattery(m).run_pattern(
        PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60))
    assert not degen, degen
    assert len(finals) == 13, len(finals)
    assert base.final_state != whale.final_state
    assert not wash.vacuous and (wash.headline or 0) <= 150, wash.headline
    # THE r13 gate: protection must NOT heal under crash-park
    keyed = [s for s, r in cp.heal_flags.items() if s.startswith(('F_t', 'J_t', 'a_t'))]
    for s in keyed:
        assert cp.heal_flags[s] > 0.5, f"{s} heals: {cp.heal_flags[s]}"
    print(f"  smoke PASS {m.candidate_id}: 13/13 distinct, wash "
          f"{wash.headline:.2f}, heal_flags "
          f"{ {k: round(v, 3) for k, v in cp.heal_flags.items()} }")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for build in (oracle_model, joule_model):
        m = build(db)
        smoke(m)
    print("both v1 models authored + smoke-gated (in-memory; formalize "
          "answer carries them to the DB)")


if __name__ == "__main__":
    main()
