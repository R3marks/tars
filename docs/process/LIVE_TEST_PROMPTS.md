# Live Test Prompts

Use these exact prompts for repeated Chrome DevTools MCP live checks. Keeping the strings stable reduces repeated approval prompts for fill actions.

## Core Prompts

### Smoke Status

```text
hello TARS, give me a one sentence status check
```

Expected result:

- frontend moves from `CONNECTED / STANDING BY` to `PROCESSING / LIVE STREAM ACTIVE`
- backend emits acknowledgement, route, response, and run summary
- route should usually be `direct_chat`
- input re-enables after completion

### Generic Web Search

```text
search the web for the latest stable Python version and summarize what you found in one paragraph
```

Expected result:

- backend routes to `task_orchestrator`
- task agent selection is `generic_task_agent`
- generic executor may use `web_search`
- response cites what it found without rendering domain-specific cards

### Generic File Context

```text
read docs/START_HERE.md and tell me the current product direction in three bullets
```

Expected result:

- backend routes to `task_orchestrator`
- task agent selection is `generic_task_agent`
- generic executor may use `read_file`
- response reflects the current generic-agent direction

## Future Code Execution Prompt

Add this once a bounded code-execution tool exists:

```text
write and run a tiny Python script that prints the first five square numbers
```

Expected result:

- backend routes to `task_orchestrator`
- generic executor writes or stages a bounded script
- generic executor runs it in the approved scratch/generated workspace
- response includes the observed output

## Approval Hygiene

If a prompt needs to change for a new feature, add it here first and reuse it exactly during future live tests. Avoid one-off wording changes during routine smoke checks.
