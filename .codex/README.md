# Codex Project Setup

This folder contains project-level Codex guidance and local tool configuration for TARS.

## Chrome DevTools MCP

`.codex/mcp.json` declares the Chrome DevTools MCP server:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"]
    }
  }
}
```

After Codex is restarted with this MCP config loaded, frontend work should use Chrome DevTools MCP to:

- inspect the running app
- read console errors
- check network requests
- take screenshots
- verify UI changes interactively

If the MCP server is unavailable in a session, say so and fall back to `npm run build`, logs, and user screenshots.

Frontend review expectations live in `docs/process/REVIEW.md`.

## Local Overrides

Do not commit machine-specific secrets or private paths here. Use ignored local files under `.codex/local/` if a future setup needs per-machine notes.

## GitHub

This project intentionally uses the GitHub CLI (`gh`) for GitHub operations instead of a GitHub MCP server.

That keeps authentication in the user's local GitHub CLI setup and avoids committing or configuring GitHub tokens for Codex.
