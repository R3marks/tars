from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ViewBlockPayload:
    block_type: str
    title: str = ""
    summary: str = ""
    body: str = ""
    items: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobActionPayload:
    action_type: str
    label: str
    job_slug: str = ""
    job_slugs: list[str] = field(default_factory=list)
    target_status: str = ""
    artifact_types: list[str] = field(default_factory=list)
    source_url: str = ""
    view_block_type: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RunActionPayload:
    action_type: str
    job_slug: str = ""
    job_slugs: list[str] = field(default_factory=list)
    target_status: str = ""
    artifact_types: list[str] = field(default_factory=list)
    source_url: str = ""
    query: str = ""
    display_mode: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SearchSpecPayload:
    query: str
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    location: str = ""
    remote_preference: str = ""
    seniority: str = ""
    company_names: list[str] = field(default_factory=list)
    exact_urls: list[str] = field(default_factory=list)
    preferred_boards: list[str] = field(default_factory=list)
    limit: int = 10

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SavedJobStatePayload:
    job_slug: str
    state: str
    previous_state: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    source: str = ""
    source_url: str = ""
    summary: str = ""
    output_paths: list[str] = field(default_factory=list)
    job_record: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DocumentDiffPayload:
    document_type: str
    summary: str = ""
    source_path: str = ""
    target_path: str = ""
    changed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DraftPackageSummaryPayload:
    job_slug: str
    summary: str
    changed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TaskAgentSelectionPayload:
    agent_name: str
    reason: str

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowSummaryPayload:
    summary: str
    changed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SkillResultPayload:
    artifact_type: str
    status: str
    summary: str
    missing_inputs: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)
    change_summary: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobSearchMatchPayload:
    job_slug: str
    title: str
    company: str
    location: str
    source: str
    summary: str
    url: str
    source_url: str = ""
    state: str = ""
    score: float = 0.0
    suitability_label: str = ""
    suitability_rationale: str = ""
    result_origin: str = ""
    actions: list[JobActionPayload] = field(default_factory=list)
    view_blocks: list[ViewBlockPayload] = field(default_factory=list)

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobSearchResultsPayload:
    query_summary: str
    search_spec: SearchSpecPayload | dict = field(default_factory=dict)
    matches: list[JobSearchMatchPayload] = field(default_factory=list)
    total_matches: int = 0
    recommendation_summary: str = ""
    actions: list[JobActionPayload] = field(default_factory=list)
    view_blocks: list[ViewBlockPayload] = field(default_factory=list)

    def to_payload(self) -> dict:
        payload = asdict(self)
        if hasattr(self.search_spec, "to_payload"):
            payload["search_spec"] = self.search_spec.to_payload()
        payload["total_matches"] = self.total_matches or len(self.matches)
        return payload


@dataclass(frozen=True)
class SavedJobStateResultPayload:
    result_type: str
    saved_state: SavedJobStatePayload

    def to_payload(self) -> dict:
        return {
            "result_type": self.result_type,
            "saved_state": self.saved_state.to_payload(),
        }
