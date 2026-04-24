import React from "react";

function iconClass(className = "") {
  return className ? `ui-icon ${className}` : "ui-icon";
}

export function AcknowledgementIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M6 8h12M6 12h8M6 16h6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function OperatorIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <circle cx="7" cy="7" r="2" fill="currentColor" />
      <circle cx="17" cy="7" r="2" fill="currentColor" />
      <circle cx="7" cy="17" r="2" fill="currentColor" />
      <path d="M13 17h6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function ResultsIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <rect x="5" y="6" width="14" height="12" rx="2" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M9 10h6M9 14h4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function ArtifactsIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M8 5h6l4 4v10H8z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M14 5v4h4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  );
}

export function ResponseIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M5 12h10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M11 7l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function FailureIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M12 6v7" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
      <circle cx="12" cy="17" r="1.2" fill="currentColor" />
      <path d="M12 3l9 16H3z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  );
}

export function AgentIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <rect x="6" y="7" width="12" height="10" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="10" cy="12" r="1.2" fill="currentColor" />
      <circle cx="14" cy="12" r="1.2" fill="currentColor" />
      <path d="M12 4v3M9 18h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function SkillIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M7 17l4-4 2 2 4-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M15 11h2v2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function WorkflowIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <circle cx="7" cy="7" r="2" fill="currentColor" />
      <circle cx="17" cy="12" r="2" fill="currentColor" />
      <circle cx="7" cy="17" r="2" fill="currentColor" />
      <path d="M9 7h4l2 3M9 17h4l2-3" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ArtifactIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M8 5h6l4 4v10H8z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M14 5v4h4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  );
}

export function SaveIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M6 5h10l2 2v12H6z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M8 5v6h8V5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M8 16h8" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function SelectIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <rect x="5" y="6" width="14" height="12" rx="2" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M8 12h4M12 12l-2-2M12 12l-2 2" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function PrepareIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M7 7h10v10H7z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M9 12h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M12 9v6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function StatusIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M9 12h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function ToolIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" className={iconClass(className)} aria-hidden="true">
      <path d="M14 6l4 4-8 8H6v-4z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M12 8l4 4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export const ICONS_BY_NAME = {
  acknowledgement: AcknowledgementIcon,
  operator: OperatorIcon,
  results: ResultsIcon,
  artifacts: ArtifactsIcon,
  response: ResponseIcon,
  failure: FailureIcon,
  agent: AgentIcon,
  skill: SkillIcon,
  workflow: WorkflowIcon,
  artifact: ArtifactIcon,
  save: SaveIcon,
  select: SelectIcon,
  prepare: PrepareIcon,
  status: StatusIcon,
  tool: ToolIcon,
};

export function AppIcon({ name, className = "" }) {
  const Component = ICONS_BY_NAME[name];

  if (!Component) {
    return null;
  }

  return <Component className={className} />;
}
