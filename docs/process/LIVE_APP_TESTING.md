# Live App Testing

This document is the source of truth for Codex live frontend and browser testing in TARS.

Use it whenever a change affects user-facing behavior, routing, websocket events, frontend rendering, or local runtime state.

## Startup

When Codex starts the app on the user's behalf, use visible PowerShell terminals for backend and frontend by default. The user should be able to see the same backend, frontend, and model-runtime logs Codex is using.

Do not use detached or background startup as the first choice. Use background processes only when the user explicitly requests them, when visible terminal startup is blocked, or when collecting extra logs after visible terminals are already running.

Current Windows startup:

```powershell
# Backend terminal
python backend/main.py

# Frontend terminal
npm.cmd run dev -- --host 127.0.0.1
```

On non-Windows shells, use:

```bash
npm run dev -- --host 127.0.0.1
```

## Browser Tooling

Prefer browser tools in this order:

1. Use the in-app browser or Chrome DevTools MCP when it is available in the current session.
2. Use screenshots, console logs, network state, and websocket observations from that browser session.
3. If browser control is unavailable, say so plainly and fall back to builds, backend smoke tests, logs, and user-provided screenshots.

Do not claim live browser testing was done unless Codex actually exercised the running app.

## Stable Prompts

Use `docs/process/LIVE_TEST_PROMPTS.md` for routine live checks.

Keep prompt text exact unless testing a new capability. Stable wording reduces repeated approval prompts for browser fill actions and makes future tests easier to compare.

If a prompt needs to change for a new feature, add it to `docs/process/LIVE_TEST_PROMPTS.md` first and reuse it exactly during future live tests.

## Inspection Checklist

Inspect at least:

- initial connection state
- console errors and accessibility issues
- network activity and websocket behavior
- one representative prompt or changed workflow
- whether the input re-enables after run completion
- whether the observed UI matches the milestone or acceptance goal

## Current Baseline

The expected generic-agent baseline is:

- frontend shows a TARS terminal shell with connected, processing, and idle states
- direct chat prompt renders acknowledgement, operator log, route, response, telemetry, and run summary
- substantive prompts route to the generic task agent
- generic results render through shared result cards, artifacts, markdown responses, telemetry, and run summaries

