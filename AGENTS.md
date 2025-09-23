# Repository Guidelines

## Project Structure & Module Organization
- Source lives in `src/` with clear layers:
  - `src/api/` FastAPI app and auth; `src/main.py` entrypoint.
  - `src/core/`, `src/services/`, `src/handlers/`, `src/events/`, `src/database/`, `src/utils/`, `src/modules/` for domain logic.
- Tests in `tests/` mirroring package paths (e.g., `tests/services/` for `src/services/`).
- Docs in `docs/`; helper scripts in `scripts/`; env templates in `.env.example`.

## Build, Test, and Development Commands
- Create venv: `python -m venv venv && source venv/bin/activate`
- Install deps: `pip install -r requirements.txt -r requirements-test.txt`
- Run app (local): `python src/main.py` (reads `.env` or `src/.env`).
- Start API only: `python -m src.api.server` if module exposes `app`.
- Run tests: `pytest` (coverage, timeouts, strict markers enabled).
- Coverage HTML: open `htmlcov/index.html` after tests.

## Coding Style & Naming Conventions
- Python 3.11+, 4‑space indentation, type hints required for public functions/classes.
- Names: modules `snake_case.py`, classes `PascalCase`, functions/vars `snake_case`, constants `UPPER_SNAKE`.
- Keep files focused; prefer composition over inheritance in services and handlers.
- Lint/format: prefer `ruff` and `black` style; if not installed, follow PEP8. Docstrings in Google style for non‑trivial modules.

## Testing Guidelines
- Framework: `pytest` with markers `unit`, `integration`, `security`, `performance`, `smoke`, `slow`, `asyncio`.
- Location/naming: `tests/test_*.py`, functions `test_*`, classes `Test*`.
- Coverage: enforced `--cov-fail-under=80` (see `pytest.ini`). Add tests with meaningful assertions and edge cases.
- Async tests: use `pytest` asyncio support (`asyncio_mode=auto`).

## Commit & Pull Request Guidelines
- Commits: present‑tense, concise scope, e.g., `feat(services): add subscription renewal`, `fix(api): handle 401 on /login`.
- Include why and what changed; link issue IDs in the body (`Refs #123`).
- PRs: clear description, checklist of impacted areas (API, DB, events), steps to test, and screenshots/logs when UI/API changes are relevant.
- Add labels and request review from domain owners (API, DB, events) as applicable.

## Security & Configuration Tips
- Never commit secrets; copy `.env.example` to `.env` and fill required variables (tokens, DB URIs, Redis).
- SQLite files (`yabot.db*`) are local artifacts; exclude from PRs unless migrations are intentional.
- Prefer dependency pins in `requirements*.txt`; run `pip-audit` if available.

## Architecture Overview
- Event‑driven core with Redis Pub/Sub fallback to local queues; FastAPI for internal services; MongoDB for dynamic state, SQLite for transactional data.
- Extend behavior via new handlers in `src/handlers/` and services in `src/services/`; wire through `src/core/router.py` and events in `src/events/`.
