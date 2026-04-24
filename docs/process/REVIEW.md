# Review Process

This document defines how Codex should review TARS changes before the user commits or pushes.

The goal is to keep the repository safe, portable, and shippable without making the user repeat the same review expectations in every thread.

## Review Mindset

Assume anything pushed to the repository may be public, reused by another person, or attacked by someone curious and bored.

Review for:

- correctness
- security
- privacy
- portability
- frontend/backend contract safety
- user experience regressions
- stale or misleading docs

## Required Review Gate

Before saying code is ready for the user to review, Codex should run this gate where relevant:

1. Inspect the git diff.
2. Check for secrets, personal paths, personal names, machine-specific details, and local-only assumptions.
3. Check for hardcoded absolute paths outside ignored local files.
4. Check whether frontend-visible backend payloads still match `docs/architecture/WEBSOCKET_EVENT_CONTRACT.md`.
5. Run backend compile checks for touched Python files.
6. Run `npm run build` for frontend changes.
7. Follow `docs/process/LIVE_APP_TESTING.md` for frontend and live app E2E review where relevant.
8. If live browser testing is unavailable, say so clearly and use build checks plus user screenshots as fallback.
9. Update docs if the change alters architecture, workflow, setup, contracts, or review process.
10. Summarise residual risks honestly.

## Docs-Only Review Gate

For changes that only affect docs, ignored local config patterns, or agent instructions:

1. Inspect `git diff --stat --find-renames`.
2. Check that moved docs are recognized as renames where practical.
3. Search for stale links to old doc paths.
4. Search for secrets, private paths, personal names, machine-specific details, and local-only assumptions.
5. Run `git diff --check`.
6. Skip frontend builds and Python compile checks unless product code changed.
7. Summarise what was reviewed and any residual risk.

Useful searches:

```powershell
rg -n "docs/[A-Z_]+\.md|docs/Tars Design Doc\.md" AGENTS.md .codex docs
rg -n "(T:|C:\\Users|DESKTOP-|api[_-]?key|token|password|secret|credential|cookie|BEGIN [A-Z ]*PRIVATE KEY)" AGENTS.md .codex docs .gitignore
```

## Frontend E2E Expectations

For frontend work, Codex should act like a copilot observer and follow `docs/process/LIVE_APP_TESTING.md`.

If browser control is not available in the current session, do not pretend it was tested. Record exactly what was verified instead.

## Security And Privacy Checks

Before pushing, check that changes do not expose:

- secrets, tokens, API keys, cookies, or credentials
- private local paths in committed configs or docs
- machine-specific hardware details in general project docs
- generated personal artifacts
- private input files under `personal/`
- unnecessary details about the user's machine or environment

Machine-specific setup belongs in ignored local files or generated benchmark artifacts, not reusable project guidance.

## Portability Checks

Prefer:

- relative paths inside repo docs
- environment variables for local setup
- example paths that are clearly placeholders
- generated local config files that are ignored by git

Avoid:

- hardcoded drive letters in product code
- assumptions about one username, one GPU, or one model folder
- committed configs that only work on the user's machine

## GitHub And Push Workflow

Use `gh` for GitHub operations where useful.

Before pushing:

1. Tell the user the code is ready for their review.
2. Ask the user to review the code.
3. Wait for explicit confirmation before committing or pushing.
4. After confirmation, Codex may commit and push on the user's behalf.
5. Pushing to `main` is allowed for this solo-developer project if the user confirms.

Do not commit or push without explicit user confirmation.

## Docs Should Evolve

Docs are not append-only logs.

When new lessons emerge:

- refine the relevant process
- remove stale guidance
- move details into a better doc if needed
- delete useless docs when they no longer help

Prefer a smaller accurate doc set over a large fossil record.
