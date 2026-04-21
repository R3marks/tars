const ACTION_LABELS = {
  "job.save": "Save job",
  "job.select_for_draft": "Select for draft",
  "job.prepare_application": "Prepare application",
  "job.open_source": "Open posting",
};

function normalizeStringArray(value) {
  if (typeof value === "string") {
    return [value.trim()].filter(Boolean);
  }

  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item) => String(item).trim()).filter(Boolean);
}

export function humanizeIdentifier(value = "") {
  return String(value)
    .replace(/\./g, " ")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function normalizeJobAction(rawAction, fallback = {}) {
  if (!rawAction) {
    return null;
  }

  const actionObject = typeof rawAction === "string" ? { action_type: rawAction } : rawAction;

  if (typeof actionObject !== "object") {
    return null;
  }

  const actionType = String(actionObject.action_type || actionObject.type || actionObject.action || "").trim();

  if (!actionType) {
    return null;
  }

  const jobSlug = String(actionObject.job_slug || fallback.jobSlug || "").trim();
  const jobSlugs = normalizeStringArray(actionObject.job_slugs || fallback.jobSlugs);
  const artifactTypes = normalizeStringArray(actionObject.artifact_types || actionObject.artifactTypes);

  return {
    action_type: actionType,
    label: String(actionObject.label || ACTION_LABELS[actionType] || humanizeIdentifier(actionType)).trim(),
    description: String(actionObject.description || actionObject.reason || "").trim(),
    job_slug: jobSlug,
    job_slugs: jobSlugs,
    target_status: String(actionObject.target_status || "").trim(),
    artifact_types: artifactTypes,
    tone: String(actionObject.tone || "").trim(),
    source_url: String(actionObject.source_url || actionObject.url || "").trim(),
    display_mode: String(actionObject.display_mode || actionObject.displayMode || "").trim(),
    disabled: Boolean(actionObject.disabled),
  };
}

export function normalizeJobActions(rawActions, fallback = {}) {
  if (!Array.isArray(rawActions)) {
    return [];
  }

  return rawActions.map((action) => normalizeJobAction(action, fallback)).filter(Boolean);
}

export function normalizeViewBlocks(rawViewBlocks) {
  if (!rawViewBlocks) {
    return [];
  }

  const blocks = Array.isArray(rawViewBlocks) ? rawViewBlocks : [rawViewBlocks];

  return blocks
    .map((block) => {
      if (typeof block === "string") {
        return {
          block_type: block,
          actions: [],
        };
      }

      if (!block || typeof block !== "object") {
        return null;
      }

      const blockType = String(block.block_type || block.view_block_type || block.type || block.kind || "").trim();

      if (!blockType) {
        return null;
      }

      return {
        ...block,
        block_type: blockType,
        actions: normalizeJobActions(block.actions || []),
      };
    })
    .filter(Boolean);
}

export function getActionSignature(action) {
  if (!action) {
    return "";
  }

  const jobSlugs = normalizeStringArray(action.job_slugs).sort().join(",");
  const artifactTypes = normalizeStringArray(action.artifact_types).sort().join(",");

  return [
    action.action_type || "",
    action.job_slug || "",
    jobSlugs,
    action.target_status || "",
    artifactTypes,
    action.display_mode || "",
  ].join("|");
}

export function actionMatchesJob(action, jobSlug) {
  if (!action || !jobSlug) {
    return false;
  }

  if (action.job_slug && action.job_slug === jobSlug) {
    return true;
  }

  return normalizeStringArray(action.job_slugs).includes(jobSlug);
}

export function normalizeJobRecord(job = {}, fallback = {}) {
  const jobSlug = String(job.job_slug || job.slug || job.item_id || fallback.jobSlug || "").trim();

  return {
    ...job,
    job_slug: jobSlug,
    title: String(job.title || job.role || job.position || "Untitled role").trim(),
    company: String(job.company || job.employer || "").trim(),
    location: String(job.location || job.remote || "").trim(),
    source: String(job.source || job.provider || "").trim(),
    result_origin: String(job.result_origin || job.origin || "").trim(),
    url: String(job.url || job.source_url || "").trim(),
    summary: String(job.summary || job.description || "").trim(),
    suitability_label: String(job.suitability_label || job.fit_label || "").trim(),
    suitability_rationale: String(job.suitability_rationale || job.rationale || "").trim(),
    status: String(job.status || "").trim(),
    actions: normalizeJobActions(job.actions || [], { jobSlug }),
  };
}
