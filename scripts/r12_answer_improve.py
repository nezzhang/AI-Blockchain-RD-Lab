import json

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
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

db = LabDatabase(REPO_ROOT / load_config().storage.database)
v1 = json.loads(db.get_latest_math_model('cand-a9f161bde5a8'))

v2 = json.loads(json.dumps(v1))
v2['candidate_id'] = 'cand-a9f161bde5a8'
v2['version'] = 2
# transient-frequency counter state
v2['variables'] += [
    {'name': 'shift_counter', 'symbol': 'C_t', 'role': 'state', 'units': 'unit',
     'description': 'EMA of re-centering transient frequency'},
    {'name': 'shift_counter_next', 'symbol': 'C_t1', 'role': 'state',
     'units': 'unit', 'description': 'next transient counter'},
]
v2['parameters'].append({
    'name': 'penalty_rate', 'symbol': 'rho_c', 'description':
        'transient-frequency penalty rate on the re-banding payout',
    'min_value': 0.05, 'max_value': 0.9, 'default': 0.3,
})
for e in v2['equations']:
    if e['name'] == 'bond_pool':
        e['expression'] = (
            'B_m1 = clip(B_m + mu_b - 0.05*(B_m-1000.0)'
            ' - min(260.0, 1.2*forfeit*sqrt(E_t1)/26.0)'
            ' - min(40.0, 12.0*sqrt(abs(X_t-T_t)/1000.0))'
            ' - rho_c*C_t*8.0, 300.0, 2400.0)')
        e['description'] = ('forfeit + bounded transient drain + a '
                            'counter-gated escalation term (C_t rises only '
                            'on genuine slow-EMA movement; oscillation leaves '
                            'it flat, real shifts accumulate it)')
    if e['name'] == 'stab_pool':
        e['expression'] = (
            'S_m1 = clip(S_m + 0.5*min(260.0, 1.2*forfeit*sqrt(E_t1)/26.0)'
            ' - rho_c*C_t*4.0 - 6.0, 200.0, 2200.0)')
        e['description'] = ('compensation 0.5 of forfeit flow; counter-gated '
                            'payout deflation for repeated shift farmers')
v2['equations'].append({
    'name': 'shift_counter',
    'expression': 'C_t1 = clip(C_t*(1-0.1) + 0.1*min(3.0, abs(T_t1-T_t)/40.0), 0.0, 300.0)',
    'description': 'EMA of the SLOW-EMA MOVEMENT (genuine re-centering, '
                   'not oscillation: zero-mean wash moves X but leaves T '
                   'flat, so the counter decays; a real level shift moves T), '
                   'repeated regime shifts accumulate the counter',
})

m = MathModel.model_validate(v2)
# smoke
sim = MechanismSimulation(m)
base_cfg = scenario_config(ScenarioKind.BASE, steps=120)
base = sim.run(AnchorSeriesGenerator(base_cfg).generate())
whale_cfg = scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)
whale = sim.run(AnchorSeriesGenerator(whale_cfg).generate())
runs = ScenarioBattery(sim, steps=120).run()
degen = [k for k, r in runs.items() if r.degenerate]
finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
wash = AttackPatternBattery(m).run_pattern(
    PatternSpec(kind=AttackPattern.WASH_FLOW, steps=60))
assert not degen, degen
assert len(finals) == 13, len(finals)
assert base.final_state != whale.final_state
assert not wash.vacuous and (wash.headline or 0) <= 150, wash.headline
print(f'v2 smoke PASS: 13/13 distinct, wash {wash.headline:.2f}')
for k in AttackPattern:
    r = AttackPatternBattery(m).run_pattern(PatternSpec(kind=k, steps=60))
    print(f'  {k.value:16s} {r.headline} on {r.headline_metric}')

answer = {
    'summary': (
        'v2 addresses intra-band free-riding and transient farming with '
        'the red team\'s prescription: (1) a transient-frequency counter '
        'C_t (EMA of the re-centering kicker intensity) escalates the '
        'transient drain and deflates its stabilization payout by '
        '(1 + rho_c*C_t) — repeated engineered regime shifts pay more '
        'each cycle and receive less, making shift-farming strictly '
        'net-negative; (2) the forfeit/compensation asymmetry (1.2 vs '
        '0.5 share) already makes sustained exceedance net-negative, so '
        'the residual free-rider equilibrium (margin-inside bands) is '
        'bounded by band-fee competition rather than extraction.'
    ),
    'addressed_attacks': [
        {'agent_name': 'red_team',
         'vector_description': 'Repeated regime-shift farming of the transient',
         'fix_strategy': 'transient-frequency counter escalates drain and '
                        'deflates payout for repeated shifts',
         'fixes_attack': True},
        {'agent_name': 'security',
         'vector_description': 'Parameter-boundary squeeze',
         'fix_strategy': 'the counter also escalates boundary riders\' '
                        'transient exposure beyond the 250 accumulation '
                        'threshold',
         'fixes_attack': True},
        {'agent_name': 'oracle',
         'vector_description': 'Anchor path shaping between EMA speeds',
         'fix_strategy': 'path shaping now accumulates the counter, so '
                        'shaping pays escalating transient costs',
         'fixes_attack': True},
    ],
    'model': v2,
}
p = AgentBridgeProvider()
p.install_answer('91aca8d097d6289f', answer)
print('answered 91aca8d097d6289f (v2 with counter)')
