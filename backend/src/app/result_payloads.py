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
