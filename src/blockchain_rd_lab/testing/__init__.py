"""Test and demo fixtures (offline discovery batches).

These are deterministic hand-written fixtures — NOT research output. They
let `lab discover --mock-fixtures` run the full generate → normalize →
dedup → store loop offline.
"""

from blockchain_rd_lab.testing.fixtures_ideas import FIXTURE_BATCHES, fixture_responses

__all__ = ["FIXTURE_BATCHES", "fixture_responses"]
