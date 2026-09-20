<!-- Thanks for contributing. Keep it scoped; CI must pass (ruff, mypy,
     pytest, bundle verifier on Python 3.12/3.13). See CONTRIBUTING.md. -->

## What & why

## Type of change
- [ ] `feat:` new capability (stays within the current phase — §38/§39)
- [ ] `fix:` correctness / honesty / reproducibility
- [ ] `test:` test only
- [ ] `docs:` documentation only

## Checklist
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src tests` is clean
- [ ] `uv run mypy` is clean
- [ ] New behavior is pinned by a test that **fails on the pre-change code**
- [ ] No LLM free-text controls a deterministic path (Pydantic at the boundary)
- [ ] No published number changed silently (if one changed, it's disclosed
      and artifacts regenerated — "never a silent re-score")

## Audit-finding linkage (if applicable)
<!-- Reference the issue / *-FIXES.md this addresses. -->
