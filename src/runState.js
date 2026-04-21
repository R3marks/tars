import { getActionSignature, normalizeJobAction, normalizeJobActions, normalizeViewBlocks } from "./jobContracts.js";

const legacyEventKindByType = {
  ack: "assistant.acknowledgement",
  route_decision: "run.routed",
  status: "run.progress",
  final_response: "assistant.response.delta",
  final: "run.completed",
  error: "run.failed",
};

function buildLegacyPayload(type, message) {
  if (type === "ack") {
    return { text: message ?? "" };
  }

  if (type === "route_decision") {
    return { mode: "", reason: message ?? "" };
  }

  if (type === "status") {
    return { status: message ?? "", details: {} };
  }

  if (type === "final_response") {
    return { text: message ?? "" };
  }

  if (type === "final") {
    return { status: message === "[DONE]" ? "completed" : message ?? "completed" };
  }

  if (type === "error") {
    return { error: message ?? "", detail: "" };
  }

  return {};
}

export function parseServerEvent(rawEvent) {
  const eventKind = rawEvent.event_kind || legacyEventKindByType[rawEvent.type] || "";
  const payload = rawEvent.payload || buildLegacyPayload(rawEvent.type, rawEvent.message);

  return {
    protocolVersion: rawEvent.protocol_version || "",
    eventKind,
    runId: rawEvent.run_id || "",
    sessionId: rawEvent.session_id || rawEvent.sessionId || 1,
    timestamp: rawEvent.ts || new Date().toISOString(),
    payload,
  };
}

function sanitizeStructuredValue(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => sanitizeStructuredValue(item))
      .filter((item) => item !== undefined);
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  const sanitizedEntries = Object.entries(value)
    .filter(([key]) => key !== "expected_outcome_index")
    .map(([key, nestedValue]) => [key, sanitizeStructuredValue(nestedValue)])
    .filter(([, nestedValue]) => nestedValue !== undefined);

  if (sanitizedEntries.length === 0) {
    return undefined;
  }

  return Object.fromEntries(sanitizedEntries);
}

function createRunRecord({
  localId,
  runId = "",
  sessionId = 1,
  userMessage = "",
  createdAt = new Date().toISOString(),
  status = runId ? "accepted" : "draft",
}) {
  return {
    localId,
    runId,
    sessionId,
    userMessage,
    acknowledgementText: "",
    route: null,
    currentPhase: "",
    phases: [],
    timelineItems: [],
    progressItems: [],
    responseText: "",
    responseReasoningText: "",
    results: [],
    artifacts: [],
    availableActions: [],
    viewBlocks: [],
    actionRequests: [],
    latestTelemetry: null,
    acknowledgementTelemetry: null,
    responseTelemetry: null,
    completionTelemetry: null,
    status,
    error: null,
    createdAt,
    updatedAt: createdAt,
  };
}

function isTerminalStatus(status) {
  return status === "completed"
    || status === "failed"
    || status === "blocked"
    || status === "needs_review";
}

function findRunIndex(runs, event) {
  if (event.runId) {
    const exactMatchIndex = runs.findIndex((run) => run.runId === event.runId);

    if (exactMatchIndex >= 0) {
      return exactMatchIndex;
    }
  }

  if (event.eventKind === "run.accepted") {
    for (let index = runs.length - 1; index >= 0; index -= 1) {
      if (!runs[index].runId) {
        return index;
      }
    }
  }

  for (let index = runs.length - 1; index >= 0; index -= 1) {
    if (!isTerminalStatus(runs[index].status)) {
      return index;
    }
  }

  return -1;
}

function mergePhase(run, phase, detail, timestamp) {
  if (!phase) {
    return run;
  }

  const phaseEntry = {
    phase,
    detail: detail || "",
    timestamp,
  };

  return {
    ...run,
    currentPhase: phase,
    phases: [...run.phases, phaseEntry],
  };
}

function appendTimelineItem(run, item) {
  return {
    ...run,
    timelineItems: [...run.timelineItems, item],
  };
}

function createActionRequest(action, timestamp, source = "local") {
  const normalizedAction = normalizeJobAction(action);

  if (!normalizedAction) {
    return null;
  }

  return {
    ...normalizedAction,
    signature: getActionSignature(normalizedAction),
    requestedAt: timestamp,
    source,
  };
}

function mergeActionRequests(existingRequests, nextRequest) {
  if (!nextRequest) {
    return existingRequests;
  }

  const existingIndex = existingRequests.findIndex((request) => request.signature === nextRequest.signature);

  if (existingIndex >= 0) {
    const existingRequest = existingRequests[existingIndex];
    const source = existingRequest.source === "local" || nextRequest.source === "local"
      ? "local"
      : (nextRequest.source || existingRequest.source || "");
    const requestedAt = existingRequest.source === "local"
      ? existingRequest.requestedAt
      : nextRequest.requestedAt;

    const mergedRequest = {
      ...existingRequest,
      ...nextRequest,
      source,
      requestedAt,
    };

    const updatedRequests = [...existingRequests];
    updatedRequests[existingIndex] = mergedRequest;
    return updatedRequests;
  }

  return [...existingRequests, nextRequest];
}

function updateJobSearchResultsWithSavedState(results, savedState) {
  const jobSlug = savedState.job_slug || savedState.job_record?.job_slug || "";
  if (!jobSlug) {
    return results;
  }

  return results.map((result) => {
    if (result.result_type !== "job_search_results") {
      return result;
    }

    const matches = (result.matches || []).map((job) => {
      if (job.job_slug !== jobSlug) {
        return job;
      }

      return {
        ...job,
        state: savedState.state || job.state,
        previous_state: savedState.previous_state || job.previous_state,
        output_paths: savedState.output_paths || job.output_paths,
      };
    });

    const viewBlocks = (result.view_blocks || result.viewBlocks || []).map((block) => {
      const items = (block.items || []).map((job) => {
        if (job.job_slug !== jobSlug) {
          return job;
        }

        return {
          ...job,
          state: savedState.state || job.state,
          previous_state: savedState.previous_state || job.previous_state,
          output_paths: savedState.output_paths || job.output_paths,
        };
      });

      return {
        ...block,
        items,
      };
    });

    return {
      ...result,
      matches,
      view_blocks: viewBlocks,
    };
  });
}

function removeCompletedStateActionRequests(actionRequests, savedState) {
  const jobSlug = savedState.job_slug || savedState.job_record?.job_slug || "";
  const completedActionTypes = new Set(["job.save", "job.select_for_draft"]);

  return actionRequests.filter((request) => {
    if (request.source !== "local") {
      return true;
    }

    if (!completedActionTypes.has(request.action_type)) {
      return true;
    }

    if (request.job_slug === jobSlug) {
      return false;
    }

    return !request.job_slugs.includes(jobSlug);
  });
}

function applyServerEvent(run, event) {
  const eventTelemetry = event.payload.telemetry || null;
  const nextRun = {
    ...run,
    runId: event.runId || run.runId,
    sessionId: event.sessionId || run.sessionId,
    updatedAt: event.timestamp,
    latestTelemetry: eventTelemetry || run.latestTelemetry,
  };

  if (event.eventKind === "run.accepted") {
    return {
      ...nextRun,
      userMessage: run.userMessage || event.payload.user_message || "",
      status: "accepted",
      error: null,
    };
  }

  if (event.eventKind === "assistant.acknowledgement") {
    return {
      ...nextRun,
      acknowledgementText: `${nextRun.acknowledgementText}${event.payload.text || ""}`,
      acknowledgementTelemetry: eventTelemetry || nextRun.acknowledgementTelemetry,
      status: "running",
    };
  }

  if (event.eventKind === "run.routed") {
    return appendTimelineItem({
      ...nextRun,
      route: {
        mode: event.payload.mode || "",
        reason: event.payload.reason || "",
      },
      status: "running",
    }, {
      kind: "route",
      label: "Route",
      value: event.payload.mode || "",
      detail: event.payload.reason || "",
      timestamp: event.timestamp,
    });
  }

  if (event.eventKind === "run.phase") {
    return appendTimelineItem({
      ...mergePhase(nextRun, event.payload.phase, event.payload.detail, event.timestamp),
      status: "running",
    }, {
      kind: "phase",
      label: "Phase",
      value: event.payload.phase || "",
      detail: event.payload.detail || "",
      timestamp: event.timestamp,
    });
  }

  if (event.eventKind === "run.progress") {
    const sanitizedDetails = sanitizeStructuredValue(event.payload.details || {}) || {};

    return {
      ...nextRun,
      progressItems: [
        ...nextRun.progressItems,
        {
          status: event.payload.status || "",
          details: sanitizedDetails,
          telemetry: eventTelemetry,
          timestamp: event.timestamp,
        },
      ],
      status: "running",
    };
  }

  if (event.eventKind === "run.result") {
    const { telemetry, ...resultPayload } = event.payload;
    const sanitizedPayload = sanitizeStructuredValue(resultPayload) || {};
    const resultActions = normalizeJobActions(sanitizedPayload.actions || []);
    const nextActionRequests = resultActions
      .map((action) => createActionRequest(action, event.timestamp, "server"))
      .filter(Boolean);
    const nextViewBlocks = normalizeViewBlocks(sanitizedPayload.view_blocks || sanitizedPayload.viewBlocks || []);

    if (sanitizedPayload.result_type === "saved_job_state") {
      const updatedResults = updateJobSearchResultsWithSavedState(nextRun.results, sanitizedPayload);
      const stateOnlyUpdate = sanitizedPayload.state === "saved" || sanitizedPayload.state === "selected_for_draft";

      return {
        ...nextRun,
        results: stateOnlyUpdate
          ? updatedResults
          : [
              ...updatedResults,
              {
                ...sanitizedPayload,
                telemetry: telemetry || null,
                timestamp: event.timestamp,
              },
            ],
        actionRequests: removeCompletedStateActionRequests(nextRun.actionRequests, sanitizedPayload),
        latestTelemetry: eventTelemetry || nextRun.latestTelemetry,
        status: stateOnlyUpdate ? nextRun.status : "running",
      };
    }

    return {
      ...nextRun,
      results: [
        ...nextRun.results,
        {
          ...sanitizedPayload,
          telemetry: telemetry || null,
          timestamp: event.timestamp,
        },
      ],
      availableActions: [
        ...nextRun.availableActions,
        ...resultActions,
      ],
      viewBlocks: [
        ...nextRun.viewBlocks,
        ...nextViewBlocks,
      ],
      actionRequests: [
        ...nextRun.actionRequests,
        ...nextActionRequests,
      ],
      status: "running",
    };
  }

  if (event.eventKind === "run.action") {
    const nextActionRequest = createActionRequest(event.payload, event.timestamp, "server");

    return {
      ...nextRun,
      availableActions: nextActionRequest
        ? [...nextRun.availableActions, nextActionRequest]
        : nextRun.availableActions,
      actionRequests: mergeActionRequests(nextRun.actionRequests, nextActionRequest),
      timelineItems: nextActionRequest
        ? [
            ...nextRun.timelineItems,
            {
              kind: "action",
              label: "Action",
              value: nextActionRequest.action_type,
              detail: nextActionRequest.job_slug || nextActionRequest.job_slugs.join(", "),
              timestamp: event.timestamp,
            },
          ]
        : nextRun.timelineItems,
      status: "running",
    };
  }

  if (event.eventKind === "run.artifact") {
    const { telemetry, ...artifactPayload } = event.payload;

    return {
      ...nextRun,
      artifacts: [
        ...nextRun.artifacts,
        {
          ...artifactPayload,
          telemetry: telemetry || null,
          timestamp: event.timestamp,
        },
      ],
      status: "running",
    };
  }

  if (event.eventKind === "assistant.response.delta") {
    return {
      ...nextRun,
      responseText: `${nextRun.responseText}${event.payload.text || ""}`,
      responseReasoningText: `${nextRun.responseReasoningText}${event.payload.reasoning_text || ""}`,
      responseTelemetry: eventTelemetry || nextRun.responseTelemetry,
      status: "running",
    };
  }

  if (event.eventKind === "run.completed") {
    return {
      ...nextRun,
      completionTelemetry: eventTelemetry || nextRun.completionTelemetry,
      status: event.payload.status || "completed",
    };
  }

  if (event.eventKind === "run.failed") {
    return {
      ...nextRun,
      completionTelemetry: eventTelemetry || nextRun.completionTelemetry,
      status: "failed",
      error: {
        message: event.payload.error || "Unknown error",
        detail: event.payload.detail || "",
      },
    };
  }

  return nextRun;
}

export function chatRunsReducer(runs, action) {
  if (action.type === "run.queued") {
    return [
      ...runs,
      createRunRecord({
        localId: action.localId,
        sessionId: action.sessionId,
        userMessage: action.userMessage,
        createdAt: action.createdAt,
        status: "queued",
      }),
    ];
  }

  if (action.type === "action.sent") {
    const runIndex = runs.findIndex((run) => run.runId === action.runId || run.localId === action.runLocalId);

    if (runIndex === -1) {
      return runs;
    }

    const updatedRuns = [...runs];
    const nextActionRequest = createActionRequest(action.payload, action.createdAt, "local");

    updatedRuns[runIndex] = {
      ...updatedRuns[runIndex],
      actionRequests: mergeActionRequests(updatedRuns[runIndex].actionRequests, nextActionRequest),
      availableActions: nextActionRequest
        ? [...updatedRuns[runIndex].availableActions, nextActionRequest]
        : updatedRuns[runIndex].availableActions,
      timelineItems: nextActionRequest
        ? [
            ...updatedRuns[runIndex].timelineItems,
            {
              kind: "action",
              label: "Action",
              value: nextActionRequest.action_type,
              detail: nextActionRequest.job_slug || nextActionRequest.job_slugs.join(", "),
              timestamp: action.createdAt,
            },
          ]
        : updatedRuns[runIndex].timelineItems,
      updatedAt: action.createdAt,
    };

    return updatedRuns;
  }

  if (action.type === "event.received") {
    const event = parseServerEvent(action.rawEvent);
    const runIndex = findRunIndex(runs, event);

    if (runIndex === -1) {
      return [
        ...runs,
        applyServerEvent(
          createRunRecord({
            localId: event.runId || `server-${event.timestamp}`,
            runId: event.runId,
            sessionId: event.sessionId,
            createdAt: event.timestamp,
            status: event.runId ? "accepted" : "draft",
          }),
          event,
        ),
      ];
    }

    const updatedRuns = [...runs];
    updatedRuns[runIndex] = applyServerEvent(updatedRuns[runIndex], event);
    return updatedRuns;
  }

  if (action.type === "connection.changed") {
    return runs;
  }

  return runs;
}

export function hasActiveRun(runs) {
  return runs.some((run) => !isTerminalStatus(run.status) && run.status !== "draft");
}
