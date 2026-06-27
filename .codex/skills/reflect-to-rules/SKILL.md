---
name: reflect-to-rules
description: Review completed or ongoing repository work and convert durable lessons into new or updated rule files under .codex/rules. Use when the user asks for 振り返り, 振り返りを行なって, reflection, retrospective, /reflect, /refect, or asks Codex to capture lessons learned as rules.
---

# Reflect To Rules

## Workflow

1. Inspect the current repository state before writing rules.
   - Read `git status --short`.
   - Read existing `.codex/rules/` files and `AGENTS.md` when present.
   - Check the recent diff or touched files when the reflection concerns the current task.

2. Extract only reusable lessons.
   - Keep rules that should change future Codex behavior in this repository.
   - Ignore one-off observations, temporary command output, and details that belong only in a final status update.
   - Prefer concrete rules tied to files, commands, secrets, tests, deployment, data sources, or user preferences.

3. Choose where the rule belongs.
   - Append to an existing rule file when the lesson fits an existing section.
   - Create a new `.codex/rules/<topic>.md` file when the lesson is a distinct recurring workflow.
   - Update `AGENTS.md` if a new rule file must always be read.

4. Write rules as short imperatives.
   - Make each bullet actionable.
   - Mention exact commands, paths, and env vars when they matter.
   - Do not include private secret values, real webhook URLs, or noisy transcripts.

5. Verify the rule update.
   - Re-read changed rule files.
   - Run `git status --short`.
   - Summarize what was added and where.

## Rule Quality Bar

- Add a rule only when it is likely to help on future tasks.
- Prefer current repository truth over memory of earlier behavior.
- Keep historical context only when it prevents repeating a mistake.
- If implementation and documentation disagree, record a rule to verify the source of truth before changing behavior.
- If the lesson is uncertain, ask for confirmation instead of fossilizing it as a rule.

