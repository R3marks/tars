export function formatElapsedMs(elapsedMs = 0) {
  const safeElapsedMs = Number(elapsedMs) || 0;

  if (safeElapsedMs < 1000) {
    return `${safeElapsedMs} ms`;
  }

  const seconds = safeElapsedMs / 1000;

  if (seconds < 60) {
    return `${seconds.toFixed(seconds >= 10 ? 0 : 1)} s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatTokensPerSecond(tokensPerSecond = 0) {
  const safeTokensPerSecond = Number(tokensPerSecond) || 0;

  if (safeTokensPerSecond <= 0) {
    return "";
  }

  return `${safeTokensPerSecond.toFixed(safeTokensPerSecond >= 10 ? 0 : 1)} tok/s`;
}

export function getReadableModelName(telemetry) {
  return telemetry?.model?.display_name || "";
}

export function getActivityLabel(telemetry) {
  return telemetry?.activity?.label || telemetry?.phase?.detail || telemetry?.phase?.phase || "";
}

export function getLiveElapsedMs(telemetry, fallbackStartedAt = "", nowMs = Date.now()) {
  const startedAt = telemetry?.run?.started_at || fallbackStartedAt;

  if (!startedAt) {
    return 0;
  }

  const startedAtMs = Date.parse(startedAt);

  if (Number.isNaN(startedAtMs)) {
    return 0;
  }

  return Math.max(0, nowMs - startedAtMs);
}

export function getTelemetryItems(telemetry, options = {}) {
  if (!telemetry) {
    return [];
  }

  const items = [];
  const modelName = getReadableModelName(telemetry);
  const elapsedLabel = formatElapsedMs(telemetry?.timing?.elapsed_ms);
  const tokensPerSecondLabel = formatTokensPerSecond(telemetry?.usage?.tokens_per_second);
  const outputTokens = telemetry?.usage?.output_tokens || 0;
  const slotId = telemetry?.activity?.slot_id || "";

  if (modelName) {
    items.push({ label: "Model", value: modelName });
  }

  if (elapsedLabel && elapsedLabel !== "0 ms") {
    items.push({ label: "Elapsed", value: elapsedLabel });
  }

  if (options.includeTokensPerSecond && tokensPerSecondLabel) {
    items.push({ label: "Speed", value: tokensPerSecondLabel });
  }

  if (options.includeOutputTokens && outputTokens > 0) {
    items.push({ label: "Output", value: `${outputTokens} tok` });
  }

  if (slotId) {
    items.push({ label: "Slot", value: slotId });
  }

  return items;
}
