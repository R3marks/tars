import React from "react";
import { AppIcon } from "../ui/icons.jsx";
import {
  actionMatchesJob,
  getActionSignature,
  humanizeIdentifier,
  normalizeJobActions,
  normalizeJobRecord,
  normalizeViewBlocks,
} from "../jobContracts.js";

function getPendingActionSignatures(run) {
  return new Set(
    (run?.actionRequests || [])
      .filter((request) => request.source === "local")
      .map((request) => request.signature)
      .filter(Boolean),
  );
}

function ActionToolbar({ actions, run, job, onAction, compact = false }) {
  const pendingActionSignatures = getPendingActionSignatures(run);
  const normalizedActions = normalizeJobActions(actions);

  if (normalizedActions.length === 0) {
    return null;
  }

  return (
    <div className={`job-action-toolbar ${compact ? "compact" : ""}`}>
      {normalizedActions.map((action) => {
        const signature = getActionSignature(action);
        const isPending = pendingActionSignatures.has(signature);
        const isCompletedStateAction = (action.action_type === "job.save" && job?.state === "saved")
          || (action.action_type === "job.select_for_draft" && job?.state === "selected_for_draft");
        const tone = action.tone || (
          action.action_type === "job.save" ? "success"
            : action.action_type === "job.select_for_draft" ? "info"
              : action.action_type === "job.prepare_application" ? "warning"
                : "neutral"
        );

        return (
          <button
            key={signature || `${action.action_type}-${action.job_slug || "global"}`}
            type="button"
            className={`job-action-button tone-${tone}`}
            onClick={() => onAction?.({ action, run, job })}
            disabled={action.disabled || isPending || isCompletedStateAction}
            title={action.description || action.label}
          >
            <span className="job-action-button-icon" aria-hidden="true">
              <AppIcon name={action.action_type === "job.save"
                ? "save"
                : action.action_type === "job.select_for_draft"
                  ? "select"
                  : action.action_type === "job.prepare_application"
                    ? "prepare"
                    : "jobAction"} />
            </span>
            <span className="job-action-button-label">
              {isCompletedStateAction ? humanizeIdentifier(job.state) : (isPending ? "Sent" : action.label)}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function getJobName(job = {}) {
  return job.title || job.role || job.position || "Untitled role";
}

function getJobCompany(job = {}) {
  return job.company || job.employer || "";
}

function getJobLocation(job = {}) {
  return job.location || job.remote || "";
}

function getJobSource(job = {}) {
  return job.source || job.provider || "";
}

function getJobFields(job = {}) {
  return [
    { label: "Company", value: getJobCompany(job) },
    { label: "Location", value: getJobLocation(job) },
    { label: "Source", value: getJobSource(job) },
    { label: "Origin", value: job.result_origin ? humanizeIdentifier(job.result_origin) : "" },
    { label: "Slug", value: job.job_slug },
  ].filter((field) => field.value);
}

function MetaList({ items }) {
  if (!items?.length) {
    return null;
  }

  return (
    <dl className="meta-list job-meta-list">
      {items.map((item) => (
        <div key={item.label} className="meta-row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function PathList({ title, paths }) {
  if (!paths?.length) {
    return null;
  }

  return (
    <div className="detail-group">
      <p className="detail-group-title">{title}</p>
      <div className="path-list">
        {paths.map((path, index) => (
          <div key={`${path}-${index}`} className="path-chip" title={path}>
            <span className="path-chip-name">{path.split(/[\\/]/).pop() || path}</span>
            <span className="path-chip-value">{path}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusPills({ items }) {
  if (!items?.length) {
    return null;
  }

  return (
    <div className="job-status-pills">
      {items.map((item) => (
        <div key={`${item.label}-${item.value}`} className={`job-status-pill ${item.tone || "neutral"}`}>
          <span className="job-status-pill-label">{item.label}</span>
          <span className="job-status-pill-value">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function JobCard({ job, actions, run, onAction, contextLabel = "" }) {
  const normalizedJob = normalizeJobRecord(job);
  const jobSpecificActions = normalizeJobActions(actions)
    .filter((action) => actionMatchesJob(action, normalizedJob.job_slug));
  const stateLabel = normalizedJob.state && normalizedJob.state !== "discovered"
    ? humanizeIdentifier(normalizedJob.state)
    : "";
  const matchLabel = stateLabel || humanizeIdentifier(normalizedJob.suitability_label || "");

  return (
    <article className="job-result-card">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="job" className="card-eyebrow-icon" />
          <p className="card-eyebrow">{contextLabel || "Job Card"}</p>
        </div>
        {matchLabel ? (
          <span className="status-chip status-info">
            {matchLabel}
          </span>
        ) : null}
      </div>

      <p className="card-title">{getJobName(normalizedJob)}</p>
      <MetaList items={getJobFields(normalizedJob)} />
      {normalizedJob.summary ? <p className="card-supporting-copy">{normalizedJob.summary}</p> : null}
      {normalizedJob.suitability_rationale ? (
        <p className="job-rationale">{normalizedJob.suitability_rationale}</p>
      ) : null}
      {normalizedJob.url ? (
        <a className="card-link" href={normalizedJob.url} target="_blank" rel="noreferrer">
          Open posting
        </a>
      ) : null}
      <ActionToolbar actions={jobSpecificActions} run={run} job={normalizedJob} onAction={onAction} compact />
    </article>
  );
}

function JobListBlock({ block, result, run, onAction }) {
  const jobs = block.jobs || block.items || result.matches || result.jobs || [];
  const actions = block.actions || result.actions || [];

  return (
    <section className="job-block job-list-block">
      <div className="block-topline">
        <div>
          <p className="block-title">{block.title || "Job List"}</p>
          {block.subtitle || result.query_summary ? (
            <p className="block-copy">{block.subtitle || result.query_summary}</p>
          ) : null}
        </div>
        {block.status ? <span className="status-chip status-info">{humanizeIdentifier(block.status)}</span> : null}
      </div>
      <div className="job-list-grid">
        {jobs.map((job, index) => (
          <JobCard
            key={job.job_slug || job.item_id || `${getJobName(job)}-${index}`}
            job={job}
            actions={job.actions || block.actions || []}
            run={run}
            onAction={onAction}
            contextLabel={block.item_label || "Job Card"}
          />
        ))}
      </div>
      <ActionToolbar actions={actions} run={run} onAction={onAction} />
    </section>
  );
}

function SelectionPanelBlock({ block, result, run, onAction }) {
  const selectedJobs = block.selected_jobs || block.jobs || block.items || [];
  const selectedSlugs = block.selected_job_slugs || block.job_slugs || [];
  const actions = block.actions || result.actions || [];

  return (
    <section className="job-block job-selection-block">
      <div className="block-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="select" className="card-eyebrow-icon" />
          <p className="card-eyebrow">{block.title || "Selection Panel"}</p>
        </div>
        {block.status ? <span className="status-chip status-info">{humanizeIdentifier(block.status)}</span> : null}
      </div>
      {block.summary ? <p className="block-copy">{block.summary}</p> : null}
      {selectedSlugs.length > 0 ? (
        <div className="selection-slug-list">
          {selectedSlugs.map((slug) => (
            <span key={slug} className="selection-slug-chip">{slug}</span>
          ))}
        </div>
      ) : null}
      {selectedJobs.length > 0 ? (
        <div className="selection-job-list">
          {selectedJobs.map((job, index) => (
            <JobCard
              key={job.job_slug || job.item_id || `${getJobName(job)}-${index}`}
              job={job}
              actions={job.actions || block.actions || []}
              run={run}
              onAction={onAction}
              contextLabel="Selected Job"
            />
          ))}
        </div>
      ) : null}
      <ActionToolbar actions={actions} run={run} onAction={onAction} />
    </section>
  );
}

function StatusSummaryBlock({ block, result }) {
  const chips = [];
  const metrics = block.metrics || result.metrics || {};

  if (block.status || result.status) {
    chips.push({ label: "Status", value: humanizeIdentifier(block.status || result.status), tone: "info" });
  }

  Object.entries(metrics).slice(0, 4).forEach(([label, value]) => {
    if (value || value === 0) {
      chips.push({ label: humanizeIdentifier(label), value: String(value), tone: "neutral" });
    }
  });

  return (
    <section className="job-block job-status-block">
      <div className="block-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="status" className="card-eyebrow-icon" />
          <p className="card-eyebrow">{block.title || "Status Summary"}</p>
        </div>
      </div>
      {block.summary ? <p className="block-copy">{block.summary}</p> : null}
      <StatusPills items={chips} />
    </section>
  );
}

function TypedViewBlock({ block, result, run, onAction }) {
  if (block.block_type === "job_list") {
    return <JobListBlock block={block} result={result} run={run} onAction={onAction} />;
  }

  if (block.block_type === "job_card") {
    const job = block.job || block.item || block.data || block;
    return <JobCard job={job} actions={block.actions || job.actions || []} run={run} onAction={onAction} contextLabel={block.title || "Job Card"} />;
  }

  if (block.block_type === "selection_panel") {
    return <SelectionPanelBlock block={block} result={result} run={run} onAction={onAction} />;
  }

  if (block.block_type === "status_summary") {
    return <StatusSummaryBlock block={block} result={result} />;
  }

  return (
    <article className="job-block job-unknown-block">
      <div className="block-topline">
        <p className="card-eyebrow">{humanizeIdentifier(block.block_type)}</p>
        <span className="status-chip status-neutral">Typed Block</span>
      </div>
      {block.title ? <p className="card-title">{block.title}</p> : null}
      {block.summary ? <p className="block-copy">{block.summary}</p> : null}
      <pre className="structured-details">{JSON.stringify(block, null, 2)}</pre>
    </article>
  );
}

function RenderedViewBlocks({ result, run, onAction }) {
  const viewBlocks = normalizeViewBlocks(result.view_blocks || result.viewBlocks || []);

  if (viewBlocks.length === 0) {
    return null;
  }

  return (
    <div className="job-view-block-list">
      {viewBlocks.map((block, index) => (
        <TypedViewBlock
          key={`${block.block_type}-${index}`}
          block={block}
          result={result}
          run={run}
          onAction={onAction}
        />
      ))}
    </div>
  );
}

function getSavedStatePayload(result) {
  return result?.saved_state || result || {};
}

function getStateTone(state = "") {
  const toneByState = {
    saved: "success",
    selected_for_draft: "info",
    draft_ready: "warning",
    applied: "success",
    rejected: "danger",
  };

  return toneByState[state] || "neutral";
}

function SavedJobStateCard({ result }) {
  const savedState = getSavedStatePayload(result);
  const jobRecord = savedState.job_record || {};
  const currentState = savedState.state || jobRecord.state || "";
  const previousState = savedState.previous_state || jobRecord.previous_state || "";
  const title = savedState.title || jobRecord.title || savedState.job_slug || "Saved job state";
  const summary = savedState.summary || jobRecord.summary || "";
  const stateNote = jobRecord.state_note || "";
  const jobMetaItems = [
    { label: "Company", value: savedState.company || jobRecord.company },
    { label: "Location", value: savedState.location || jobRecord.location },
    { label: "Source", value: savedState.source || jobRecord.source },
    { label: "Slug", value: savedState.job_slug || jobRecord.job_slug },
  ].filter((item) => item.value);
  const stateItems = [
    { label: "From", value: previousState ? humanizeIdentifier(previousState) : "" },
    { label: "To", value: currentState ? humanizeIdentifier(currentState) : "" },
  ].filter((item) => item.value);
  const outputPaths = savedState.output_paths || jobRecord.output_paths || [];

  return (
    <article className="structured-card result-card result-card-wide">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="status" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Saved Job State</p>
        </div>
        {currentState ? (
          <span className={`status-chip status-${getStateTone(currentState)}`}>
            {humanizeIdentifier(currentState)}
          </span>
        ) : (
          <span className="status-chip status-neutral">Saved</span>
        )}
      </div>

      <p className="card-title">{title}</p>
      {summary ? <p className="card-supporting-copy">{summary}</p> : null}
      <MetaList items={jobMetaItems} />

      {stateItems.length > 0 || stateNote ? (
        <div className="detail-group">
          <p className="detail-group-title">State Transition</p>
          {stateItems.length > 0 ? (
            <div className="summary-chip-list">
              {stateItems.map((item) => (
                <div key={item.label} className="summary-chip">
                  <span className="summary-chip-label">{item.label}</span>
                  <span className="summary-chip-value">{item.value}</span>
                </div>
              ))}
            </div>
          ) : null}
          {stateNote ? <p className="card-copy">{stateNote}</p> : null}
        </div>
      ) : null}

      <PathList title="Output Paths" paths={outputPaths} />
      {Object.keys(jobRecord).length > 0 ? (
        <details className="reasoning-panel">
          <summary className="reasoning-summary">Saved Record</summary>
          <div className="reasoning-content">
            <pre className="reasoning-pre">{JSON.stringify(jobRecord, null, 2)}</pre>
          </div>
        </details>
      ) : null}
    </article>
  );
}

export default function JobSearchResultCard({ result, run, onAction }) {
  const normalizedResult = {
    ...result,
    matches: Array.isArray(result.matches) ? result.matches.map((job) => normalizeJobRecord(job)) : [],
    actions: normalizeJobActions(result.actions || []),
  };

  const matches = normalizedResult.matches;
  const topLevelActions = normalizedResult.actions.filter((action) => !action.job_slug && action.job_slugs.length === 0);
  const fallbackBlocks = normalizedResult.view_blocks || normalizedResult.viewBlocks || [];
  const viewBlocks = normalizeViewBlocks(fallbackBlocks);

  return (
    <article className="structured-card result-card result-card-wide job-search-result-card">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="job" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Job Search</p>
        </div>
        <span className="status-chip status-info">
          {`${normalizedResult.total_matches || matches.length} match${(normalizedResult.total_matches || matches.length) === 1 ? "" : "es"}`}
        </span>
      </div>

      {normalizedResult.query_summary ? <p className="card-copy">{normalizedResult.query_summary}</p> : null}
      {normalizedResult.recommendation_summary ? (
        <p className="card-supporting-copy">{normalizedResult.recommendation_summary}</p>
      ) : null}

      {topLevelActions.length > 0 ? (
        <ActionToolbar actions={topLevelActions} run={run} onAction={onAction} />
      ) : null}

      {viewBlocks.length > 0 ? (
        <RenderedViewBlocks result={normalizedResult} run={run} onAction={onAction} />
      ) : matches.length > 0 ? (
        <JobListBlock
          block={{ block_type: "job_list", title: "Matched Jobs", actions: normalizedResult.actions }}
          result={normalizedResult}
          run={run}
          onAction={onAction}
        />
      ) : (
        <p className="card-supporting-copy">No structured job matches were returned for this run.</p>
      )}
    </article>
  );
}

export { JobCard, JobListBlock, SelectionPanelBlock, StatusSummaryBlock, ActionToolbar, SavedJobStateCard, actionMatchesJob };
