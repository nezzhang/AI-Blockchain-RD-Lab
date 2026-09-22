"""§21 generator statistics — the test class whose absence let the r50
calibration finding live since Phase 4.

The calibration suite (known-answer fixtures) caught that
`_DeterministicRandom`'s mangled mulberry32 port produced uniforms
averaging 0.02 (not 0.5) and gaussians averaging +3.5 sigma: every §15
"base" scenario ran with a hidden +0.73%/step drift and Monte Carlo
"trials" across seeds were near-identical streams. These tests pin the
distribution properties directly so no port regression can hide again.
"""

from __future__ import annotations

import statistics

from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    ScenarioKind,
    _DeterministicRandom,
    scenario_config,
)

_DRAWS = 20_000


class TestDeterministicRandomStatistics:
    def test_uniform_covers_unit_interval(self) -> None:
        for seed in (7, 1, 42, 123):
            rng = _DeterministicRandom(seed)
            draws = [rng.uniform() for _ in range(_DRAWS)]
            assert all(0.0 <= u < 1.0 for u in draws)
            mean = statistics.fmean(draws)
            assert abs(mean - 0.5) < 0.02, f"uniform mean {mean:.4f} biased at seed {seed}"

    def test_gauss_is_standard_normal(self) -> None:
        for seed in (7, 1, 42, 123):
            rng = _DeterministicRandom(seed)
            draws = [rng.gauss(0.0, 1.0) for _ in range(_DRAWS)]
            mean = statistics.fmean(draws)
            std = statistics.pstdev(draws)
            assert abs(mean) < 0.05, f"gauss mean {mean:+.4f} at seed {seed}"
            assert abs(std - 1.0) < 0.05, f"gauss std {std:.4f} at seed {seed}"

    def test_gauss_respects_mu_sigma(self) -> None:
        rng = _DeterministicRandom(7)
        draws = [rng.gauss(0.0002, 0.002) for _ in range(_DRAWS)]
        assert abs(statistics.fmean(draws) - 0.0002) < 0.0002
        assert abs(statistics.pstdev(draws) - 0.002) < 0.0002

    def test_distinct_seeds_distinct_streams(self) -> None:
        # The r50 bug's second symptom: seed choice barely mattered.
        streams = [
            [_DeterministicRandom(s).uniform() for _ in range(5)] for s in (7, 8, 9)
        ]
        assert len({tuple(s) for s in streams}) == 3

    def test_same_seed_same_stream(self) -> None:
        a = [_DeterministicRandom(7).gauss(0.0, 1.0) for _ in range(50)]
        b = [_DeterministicRandom(7).gauss(0.0, 1.0) for _ in range(50)]
        assert a == b  # §21 determinism


class TestScenarioSeriesFidelity:
    """The generated anchor series must match the scenario's CONFIGURED
    statistics — the exact regression the calibration suite caught
    (base configured at +0.02%/step generated +0.73%/step)."""

    def _pcts(self, kind: ScenarioKind, steps: int = 120, seed: int = 7) -> list[float]:
        series = AnchorSeriesGenerator(scenario_config(kind, steps=steps, seed=seed)).generate()
        return [r["dX_t"] / r["X_t"] for r in series]

    def test_base_series_matches_config(self) -> None:
        cfg = scenario_config(ScenarioKind.BASE, steps=120, seed=7)
        pcts = self._pcts(ScenarioKind.BASE)
        mean = statistics.fmean(pcts)
        std = statistics.pstdev(pcts)
        # 120-draw sampling noise on the mean is ~vol/sqrt(120) ~ 0.0002;
        # the buggy generator measured +0.0073 — 36x the configured mean.
        assert abs(mean - cfg.mean_delta_pct) < 0.002, f"base mean {mean:+.5f}"
        assert abs(std - cfg.vol_pct) < 0.002, f"base std {std:.5f}"

    def test_bear_series_drifts_down(self) -> None:
        pcts = self._pcts(ScenarioKind.BEAR)
        assert statistics.fmean(pcts) < 0.0, "bear scenario must drift negative"

    def test_shock_lands_at_configured_step(self) -> None:
        cfg = scenario_config(ScenarioKind.BANK_RUN, steps=120, seed=7)
        assert cfg.shock_step is not None
        pcts = self._pcts(ScenarioKind.BANK_RUN)
        # the -30% bank-run shock must be the window's extreme move
        assert min(pcts) < -0.25
        assert pcts.index(min(pcts)) == cfg.shock_step
