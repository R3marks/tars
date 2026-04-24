# Milestone 1 Plan: Generic Agent Workbench

Milestone 1 has been reset away from bespoke job-search, job-application, and interview-prep workflows.

The product lesson from the removed prototype is simple: hardcoded domain flows become brittle quickly. TARS should first become a stronger general-purpose local assistant that can reason, inspect context, use tools, write code, execute code, verify results, and explain what happened.

## Product Direction

The core loop is now:

1. User talks to TARS normally.
2. Router chooses either `direct_chat` or the generic task agent.
3. The generic task agent plans the work, uses broad tools, and produces a normal conversational answer.
4. The frontend renders the run lifecycle clearly without domain-specific UI.
5. Codex and the user improve the generic loop through live app tests.

The aim is not to build a workflow for every domain. The aim is to make the generic agent capable enough that domains emerge from prompts, tools, files, and code rather than from one-off backend branches.

## Current Runtime Shape

- `backend/src/app/`
  - WebSocket transport, run lifecycle events, model runtime setup.
- `backend/src/orchestration/request_router.py`
  - Chooses `direct_chat` or `task_orchestrator`.
- `backend/src/orchestration/task_orchestrator.py`
  - Selects and runs the registered task agent.
- `backend/src/orchestration/task_agent_registry.py`
  - Currently registers only `generic_task_agent`.
- `backend/src/orchestration/generic_agent_flow.py`
  - Legacy expected-outcomes, planner, executor, verifier, final-response loop.
- `backend/src/agents/`
  - Generic planner/executor tools.
- `src/`
  - Generic chat/run UI with acknowledgement, route, phase, results, artifacts, response, telemetry.

Removed from runtime:

- hardcoded job-search workflow
- hardcoded job-application workflow
- hardcoded interview-prep workflow
- job/interview-specific frontend renderers
- job/interview run actions

## Milestone 1 Goals

### 1. Make The Generic Agent Useful

Improve the existing generic flow before adding new domain agents.

Near-term capabilities:

- reliable file reading
- safe file writing
- web search
- code writing
- code execution in a bounded workspace
- concise result synthesis
- better failure recovery when a step returns weak evidence

### 2. Add Code Execution As The Main Tool

Coding is the highest-leverage capability for this assistant.

The next major tool should let TARS:

- create a small scratch script
- run it
- inspect stdout/stderr
- revise it when needed
- summarize the result

Initial implementation should be conservative:

- execute only inside an approved scratch/generated workspace
- surface commands and outputs in the run log
- keep destructive filesystem actions blocked or approval-gated
- prefer short-lived scripts over persistent hidden state

### 3. Keep The UI Generic

The frontend should stay focused on run comprehension:

- what the user asked
- what route was selected
- what phases occurred
- what tool/result/artifact events were produced
- what TARS ultimately answered

Do not add domain-specific cards until a result type is stable and broadly reusable.

### 4. Improve Tool Contracts

Tool calls should be understandable and inspectable.

Useful generic result types:

- `task_agent_selection`
- `partial_result`
- `tool_result`
- `workflow_summary`
- `artifact`

Avoid domain-specific payloads such as job cards, saved job state, mock interview turns, or application packages for now.

### 5. Test Through The App

Every non-trivial agent change should be tested in the live UI with stable prompts.

Minimum checks:

- direct chat prompt routes to `direct_chat`
- substantive prompt routes to `task_orchestrator`
- generic agent can answer a file/tool question
- generic agent can do a small web-search-backed answer
- after code execution exists, generic agent can write and run a tiny script

## Stable Test Prompts

Keep these in `docs/process/LIVE_TEST_PROMPTS.md`:

- `hello TARS, give me a one sentence status check`
- `search the web for the latest stable Python version and summarize what you found in one paragraph`
- `read docs/START_HERE.md and tell me the current product direction in three bullets`

After code execution lands:

- `write and run a tiny Python script that prints the first five square numbers`

## Non-Goals

For now, do not rebuild:

- job search
- job application drafting
- interview prep
- domain-specific UI cards
- silent state actions
- autonomous external submissions or account actions

Those can return later as generic-agent use cases once the broad tool loop is strong enough.

## Review Question

Before adding any new domain workflow, ask:

> Could the generic agent do this well with better tools, better prompts, and better memory?

If yes, improve the generic agent. If no, define the smallest reusable abstraction and keep it out of transport/UI catch-all files.
