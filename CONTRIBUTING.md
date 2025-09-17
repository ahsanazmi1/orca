# Contributing to Orca

## Ways to Help
- **File issues** with clear repro or proposals
- **Improve docs** / examples
- **Add tests** and small features discussed in issues

## Dev Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
pytest -q
```

## Coding Standards
- **Black** (line length 100), **Ruff** (lint), type hints encouraged
- **Small PRs**; include tests when reasonable
- **Follow the JSON Decision Contract** draft

## Commit & PR
- **Conventional commits** preferred (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **Link to an issue**; include before/after when UI/behavior changes


