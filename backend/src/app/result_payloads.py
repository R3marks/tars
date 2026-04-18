from dataclasses import asdict, dataclass, field


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
    item_id: str
    title: str
    company: str
    location: str
    source: str
    summary: str
    url: str
    suitability_label: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobSearchResultsPayload:
    query_summary: str
    matches: list[JobSearchMatchPayload] = field(default_factory=list)
    total_matches: int = 0
    recommendation_summary: str = ""

    def to_payload(self) -> dict:
        payload = asdict(self)
        payload["total_matches"] = self.total_matches or len(self.matches)
        return payload
