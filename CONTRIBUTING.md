# Contributing Guide 🤝

Thanks for helping improve PT-PT Learning Companion.

## Ways to contribute

- Report bugs
- Suggest product and UX improvements
- Improve docs and examples
- Submit code fixes and features

## Development setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn pt_pt_learning_companion.app:app --reload --port 8000
```

## Branch and PR flow

1. Create a branch from `main`:
   - `feat/<short-name>` for features
   - `fix/<short-name>` for bug fixes
   - `docs/<short-name>` for documentation
2. Make focused commits with clear messages.
3. Run tests before opening a PR:

```bash
pytest
```

4. Open a pull request using the PR template.

## Style expectations

- Keep UI copy clear and simple.
- Prefer small, reviewable changes.
- Keep credentials, keys, and tokens out of source code.
- Update `README.md` when behavior or flow changes.

## Reporting bugs

Use the bug report template and include:

- Expected behavior
- Actual behavior
- Steps to reproduce
- OS/browser details
- Screenshots or screen recording when possible

## Feature requests

Use the feature request template and include:

- User problem
- Proposed solution
- Alternatives considered
- Impact on current flows
