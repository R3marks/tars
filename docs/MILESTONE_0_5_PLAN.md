# Milestone 0.5 Plan

Milestone 0.5 is the boundary-setting milestone between milestone 0 cleanup and milestone 1 job-domain expansion.

It exists because the current frontend/backend link is functional but still too string-oriented and ad hoc for the next stage of the project.

The purpose of this milestone is not just transport cleanup. It is to make TARS feel like one coherent assistant while also giving the UI enough structure to show useful progress, structured results, and future job-search workflows clearly.

## Core Intent

By the end of milestone 0.5:

- the frontend and backend communicate through a stable typed event contract over WebSocket
- the first visible response is still an LLM-authored TARS acknowledgement
- operator-facing status updates stay concise, truthful, and useful
- the UI is cleaner and more deliberate without becoming the focus of the project
- milestone 1 job-search and application work can be added without redesigning the communication boundary again

This project should feel like talking to TARS, not just to a backend service.

That means the architecture should preserve two things at once:

- functionality remains primary
- TARS personality remains part of the product contract

## Product Philosophy For This Milestone

### Conversational identity

TARS should remain a personal assistant with a recognizable voice.

- the initial acknowledgement should remain model-authored
- the acknowledgement should sound like TARS in a short, useful way
- later assistant output should also preserve some TARS charm where it does not get in the way of usefulness
- personality belongs in assistant speech, not in hidden internal reasoning

### Operator-first visibility

The UI should help the user understand what TARS is doing at all times.

- status messages should be short, readable, and truthful
- routing, progress, outputs, and review state should be visible without reading logs
- structured results should render as UI elements rather than flattened markdown whenever they are not naturally conversational text

### Visual direction

The UI should become more polished, but still feel like a TARS-facing terminal rather than a generic consumer chat app.

- keep the current dark palette direction as the near-term anchor
- improve spacing, alignment, hierarchy, and readability
- use restrained accent styling and motion
- let the interface look intentional and calm rather than flashy
- keep rich content such as cards and progress sections inside the terminal-like experience

## Why Milestone 0.5 Exists

Right now the frontend largely reconstructs meaning by concatenating websocket strings into one reply area.

That is too weak for milestone 1, where TARS will need to:

- stream acknowledgement and final conversational text
- expose route and progress updates
- return structured job-search result lists
- show generated artifacts and review packages
- allow the user to choose which jobs to pursue next

If this boundary is not stabilized first, milestone 1 work will either duplicate UI logic or force another protocol redesign halfway through the feature build.

## Milestone Goal

Create a typed, versioned WebSocket event boundary and a cleaner operator-style chat UI that can support:

- one active run at a time
- model-authored acknowledgement
- curated progress updates
- streamed assistant text
- structured result cards
- structured artifact cards
- future follow-up UI actions such as selecting jobs from a result list

## Architectural Decisions Locked For 0.5

- WebSocket remains the canonical transport for now
- there is one active run at a time
- chat remains the primary interaction surface
- structured cards appear inside the conversation flow, not in a separate product shell
- the first acknowledgement remains LLM-authored
- routing and progress events are structured and curated by the backend
- the frontend renders event types intentionally instead of flattening everything into markdown
- milestone 0.5 should produce docs good enough for frontend and backend work to continue in parallel threads

## Communication Contract

All frontend/backend communication should move to a shared event envelope.

Each message should carry:

- protocol version
- event kind
- run id
- session id
- timestamp
- typed payload

### Client to backend

The client should submit work through a structured request event rather than a free-form websocket payload shape.

Initial client messages should support:

- creating a run from user text
- reserving a path for later UI-originated actions such as selecting a job or approving a next step

### Backend to client

The backend should emit typed events for:

- run accepted
- LLM acknowledgement text
- route selected
- phase changed
- progress update
- assistant text delta
- structured result
- structured artifact
- completed
- failed

The acknowledgement should remain distinct from transport-level acceptance:

- acceptance confirms the run exists
- acknowledgement is the first assistant utterance

This preserves TARS personality without making basic lifecycle handling depend on LLM success.

## Backend Plan

### Phase 1: Introduce a shared websocket event layer

Create one small backend event-emitter layer that owns:

- event envelope formatting
- run lifecycle ordering
- typed payload helpers
- terminal success and failure semantics

Every backend path should use this layer instead of hand-writing websocket payloads.

### Phase 2: Refit existing routes to the event contract

Refit:

- direct chat
- fact check
- generic agent flow
- job application workflow

Each path should emit:

1. run acceptance
2. LLM acknowledgement
3. route and phase updates
4. progress and structured outputs as needed
5. final assistant response stream
6. a terminal completion or failure event

### Phase 3: Prepare milestone 1 result types

Add typed result payloads for:

- workflow summaries
- generated artifacts
- future job-search results

Job-search results should be designed now even if the backend search flow lands in milestone 1.

They should support at least:

- stable item id
- job title
- company
- location
- source
- short summary
- URL
- lightweight suitability or recommendation label

## Frontend Plan

### Phase 1: Replace string-concatenation state with run-based state

The frontend should store conversation state by run rather than by one growing reply string.

Each run should track:

- user prompt
- acknowledgement text
- route
- phase
- progress items
- streamed final assistant text
- results
- artifacts
- terminal state

### Phase 2: Build the operator-style conversation shell

Improve the current layout so it is clean and intentional:

- stable max-width conversation area
- better spacing and alignment
- sticky or anchored composer
- clearer user and TARS message surfaces
- readable status and result presentation

This should remain simple, but visibly polished.

### Phase 3: Add dedicated renderers for non-chat content

Keep markdown for conversational assistant text.

Render these with dedicated UI components instead:

- acknowledgement strip
- route badge or header
- progress timeline or stacked status list
- result cards
- artifact cards
- failure state

The user should be able to scan a run and understand what happened without parsing tags like `[ACK]` or `[STATUS]`.

## Milestone 1 Readiness Requirements

Milestone 0.5 is complete only when the system can support this future interaction cleanly:

1. the user asks TARS to find a certain kind of job
2. TARS acknowledges the request in character
3. the UI shows route and progress clearly
4. TARS returns a structured list of job matches
5. the user can inspect those results easily
6. the boundary is ready for a later follow-up action such as choosing which jobs to continue with

Milestone 0.5 does not need to implement the full job-search domain logic itself.

It does need to make that experience architecturally straightforward.

## Testing Strategy

Testing effort should focus on integration and end-to-end confidence more than unit-test volume.

### Backend integration focus

- verify each route emits the expected event sequence
- verify acknowledgement, progress, final response, and terminal events arrive in the correct order
- verify failure paths emit structured error events

### Frontend integration focus

- verify event streams render correctly into the run UI
- verify structured result and artifact events render as cards
- verify the UI remains readable during streaming and progress updates

### Human-in-the-loop end-to-end testing

Use the real assistant and the real UI as a core test loop:

- backend functionality can be exercised directly through the live assistant path
- frontend behavior can be reviewed visually with screenshots
- TARS can act as an observer during milestone execution by evaluating screenshots and run outputs

This should be treated as a first-class testing approach for this project, not as an afterthought.

## Deliverables

Milestone 0.5 should produce:

1. a documented websocket event contract
2. a shared backend event-emitter path
3. refit backend routes using that contract
4. a run-based frontend state model
5. a cleaner operator-style chat UI
6. dedicated UI rendering for progress, results, and artifacts
7. event shapes ready for milestone 1 job-search results
8. docs clear enough that frontend and backend implementation can continue in parallel if needed

## Suggested Execution Order

1. lock the websocket event schema and lifecycle semantics
2. implement the backend event helper and refit existing flows
3. rebuild frontend state around runs and typed events
4. polish the UI shell and add structured renderers
5. validate the boundary with end-to-end runs before starting milestone 1

## Notes For Future Threads

If a future thread starts from docs only, this file should be treated as the implementation-ready source of truth for milestone 0.5.

Frontend and backend work can be parallelized after the event schema is locked, because the main seam between those workstreams is the typed websocket contract defined by this milestone.
