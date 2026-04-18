# TARS Code Style

This document captures the working code style for TARS based on the current codebase and explicit project preferences.

It is intentionally practical rather than ideological.

The goal is readable, easy-to-extend code that fits a personal assistant product built by one primary user and one coding agent over time.

## Core Principles

### Readability over cleverness

Choose names and control flow that are easy to understand on first read.

- prefer explicit parameter names
- prefer descriptive class and method names
- avoid abbreviations unless they are already standard in the repo
- do not shorten names to save characters or memory

If a reader has to infer meaning from context, the name is probably too vague.

### Prefer early exits over nested branching

Avoid heavy `if/else` trees where possible.

Preferred style:

- use guard clauses
- use negation with early `return` or `continue`
- flatten control flow whenever it improves readability

This is the default style across backend and frontend unless a different structure is clearly simpler.

### Keep responsibilities narrow

Favor code where each file, function, class, or component has a clear job.

This is not a rigid purity rule, but it is the design direction:

- one file should ideally own one area of behavior
- one class should ideally represent one concept
- one function should ideally do one thing

If combining logic into one file makes the code easier to understand in practice, do that instead of over-fragmenting.

### Structure first, dogma second

The backend is intentionally a hybrid of:

- OOP-style modeling where schemas and boundaries benefit from it
- scripting-style flexibility where orchestration and glue code benefit from it

Use dataclasses, small classes, and explicit models where they improve clarity.
Do not force object-oriented patterns where they make the flow harder to follow.

## Backend Style

### Naming

- use clear full names for variables, parameters, methods, classes, and files
- avoid underscored "private-style" method naming unless there is a strong reason
- prefer names like `build_application_context` over compressed or vague alternatives
- use singular nouns for single values and plural nouns for collections

### Control flow

- prefer guard clauses for invalid or empty inputs
- prefer `continue` over wrapping the rest of a loop in a large conditional
- prefer helper functions when a block of logic has a distinct meaning
- if two failure scopes are both useful, separate them into different functions rather than nesting large `try` blocks inline

### Data modeling

- use dataclasses for structured backend artifacts, requests, and results
- keep schema-like types explicit
- prefer passing rich named objects where that improves clarity over passing loosely shaped dicts everywhere

### Functions and files

- keep orchestrators focused on sequencing and delegation
- keep parsing, inference prompts, rendering, and file output in separate helpers or modules when practical
- avoid hiding meaningful behavior inside large utility files

### Errors and fallbacks

- fail safely when the system can recover
- make fallback behavior explicit in code
- keep user-facing fallback messages honest and concise

### Comments

- comments should explain intent, not restate obvious syntax
- add comments sparingly
- remove stale comments rather than letting them drift

## Frontend Style

### Component design

- prefer small functional React components
- keep each component responsible for one clear rendering concern
- move formatting or protocol interpretation out of presentation components when it starts to grow

### State

- keep state shapes explicit and readable
- prefer naming that matches user-facing concepts like `run`, `progress`, `artifact`, or `reply`
- avoid ambiguous containers like generic `data` when a more specific name is available

### Rendering

- conversational text can remain markdown-driven
- structured content should use dedicated UI rendering rather than being flattened into strings
- keep the UI visually calm, readable, and intentionally terminal-adjacent

### Styling

- prefer clear layout, spacing, and hierarchy over decorative complexity
- keep colors and motion restrained
- use styles that support an operator-style assistant experience rather than a generic chat app

## Existing Repo Conventions To Preserve

- Python modules commonly use `snake_case`
- schema-like backend types often use dataclasses
- React code uses functional components
- backend orchestration favors small helpers over one giant function when the boundaries are obvious
- TARS voice should be concise, useful, and lightly dry rather than noisy or theatrical

## Practical Defaults

When choosing between two acceptable implementations:

1. choose the one with flatter control flow
2. choose the one with clearer names
3. choose the one with more explicit data boundaries
4. choose the one that is easier to extend in the next milestone

If a future thread needs style context quickly, this file should be treated as the coding-style source of truth.
