---
name: slack-stock-bot-maintainer
description: Maintain this Python Slack stock market bot safely. Use for changes to main.py, requirements.txt, README.md, tests, Slack Incoming Webhook behavior, stock/market data retrieval, message formatting, scheduling, error handling, or repository workflow for slack-stock-daily-bot.
---

# Slack Stock Bot Maintainer

## Workflow

1. Start with repository context.
   - Read `AGENTS.md` and `.codex/rules/`.
   - Run `git status --short`.
   - For the first implementation request in a session, create a new branch unless the user already specified a branch.
   - For follow-up requests in the same session, continue the current work branch instead of creating a branch per request.

2. Understand the requested behavior.
   - Check `README.md`, `main.py`, `requirements.txt`, and relevant tests.
   - Treat `README.md` and implementation drift as something to resolve deliberately.
   - Keep the bot small unless the user asks for a larger architecture.

3. Implement with testable boundaries.
   - Keep Slack posting, market data retrieval, message formatting, and environment loading separable.
   - Give external calls explicit timeouts and clear user-facing errors.
   - Avoid making tests depend on live Slack webhooks, yfinance, market availability, or network access.

4. Protect secrets and local files.
   - Use `SLACK_WEBHOOK_URL` from `.env` or the environment.
   - Never commit `.env`, real webhook URLs, generated caches, `.pyc`, or `.venv`.
   - Use dummy webhook examples in docs and tests.

5. Verify changes.
   - Run focused tests, usually `python -m pytest`, when test dependencies are available.
   - If dependencies are missing, explain the exact blocker and the command needed to install them.
   - Update `README.md` whenever setup, runtime behavior, target symbols, env vars, or output format changes.

## Defaults

- Prefer standard library plus existing dependencies.
- Add dependencies to `requirements.txt` only when they materially simplify the bot or are required for the requested behavior.
- Keep messages readable in Slack plain text.
- On partial data failure, continue where reasonable and show which symbol or service failed.
- When adding scheduling, separate scheduler/platform setup from the bot's Python runtime behavior.
