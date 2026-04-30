# Contributing

This project is open to contributions. The theory is fixed (it comes from the book); the implementation is open.

## What we accept

- Bug fixes in axiom enforcement
- New resource types (extend `ResourceType`)
- Better conflict resolution strategies (must not violate hard invariants)
- Stronger dialectical manipulation detection (layer 1 conclusion testers)
- Language bindings (TypeScript, Rust, Go)
- Integration examples (LangChain, AutoGen, custom agent loops)
- Documentation improvements and translations

## What we do not accept

- Changes that weaken the hard invariants (`HARD_INVARIANTS` in `synthesis/constrained.py`)
- Changes that allow machine sovereignty to increase without veto
- Removal of the A4 (ownerless machine) check
- "Emergency exceptions" that bypass the verifier

## Process

1. Fork → branch → PR against `main`
2. All tests must pass: `pytest`
3. Lint must pass: `ruff check src tests`
4. Add tests for any new axiom check or detection pattern

## Running locally

```bash
pip install -e ".[dev]"
pytest
uvicorn freedom_theory.api.app:app --reload   # REST API
python examples/agi_agent_loop.py             # demo
```
