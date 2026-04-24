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

Frontend live testing expectations live in `docs/process/LIVE_APP_TESTING.md`.

Frontend review expectations live in `docs/process/REVIEW.md`.

## MCP Approval Prompts

MCP tool-call approval is controlled by Codex itself, not by this repo's `.codex/mcp.json`.

The user-level Codex config is expected to include:

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

That setting lives in `~/.codex/config.toml` and may require restarting Codex or opening a new chat before it fully applies. If Chrome DevTools MCP still prompts, use the approval dialog's "do not ask again" / "allow always" option when it appears; plain "allow" is session-local and may not persist.

## Local Overrides

Do not commit machine-specific secrets or private paths here. Use ignored local files under `.codex/local/` if a future setup needs per-machine notes.

## GitHub

This project intentionally uses the GitHub CLI (`gh`) for GitHub operations instead of a GitHub MCP server.

That keeps authentication in the user's local GitHub CLI setup and avoids committing or configuring GitHub tokens for Codex.
