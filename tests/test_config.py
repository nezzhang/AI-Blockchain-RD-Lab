"""Configuration loading tests."""

from __future__ import annotations

from blockchain_rd_lab.config import CONFIG_DIR, LabConfig, load_config


class TestConfig:
    def test_load_defaults_from_repo(self):
        cfg = load_config()
        assert isinstance(cfg, LabConfig)
        assert cfg.lab.name == "AI Blockchain R&D Lab"
        assert cfg.runtime.llm_provider == "mock"
        assert cfg.pipeline.discovery_count == 100
        assert cfg.pipeline.post_prior_art == 20
        assert cfg.pipeline.finalists == 5

    def test_human_approval_gates_present(self):
        cfg = load_config()
        gates = set(cfg.pipeline.require_human_approval_for)
        assert "issuing_real_tokens" in gates
        assert "deploying_contracts" in gates
        assert "publishing_novelty_claims" in gates

    def test_missing_dir_falls_back_to_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "empty")
        assert cfg.pipeline.discovery_count == 100  # schema default

    def test_reads_current_config_dir(self):
        # CONFIG_DIR is read at call time so tests/other tools can repoint it.
        cfg = load_config(CONFIG_DIR)
        assert cfg.runtime.llm_provider == "mock"
