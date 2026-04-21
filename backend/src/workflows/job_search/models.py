from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class SearchSpec:
    query: str
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    location: str = ""
    remote_preference: str = ""
    seniority: str = ""
    company_names: list[str] = field(default_factory=list)
    exact_urls: list[str] = field(default_factory=list)
    preferred_boards: list[str] = field(default_factory=lambda: ["greenhouse", "lever", "ashby"])
    limit: int = 10

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobLead:
    job_slug: str
    title: str
    company: str
    location: str
    source: str
    source_url: str
    summary: str
    state: str = "discovered"
    score: float = 0.0
    suitability_label: str = ""
    suitability_rationale: str = ""
    job_posting_text: str = ""
    board: str = ""
    search_keywords: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    result_origin: str = "new"

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobSearchWorkflowResult:
    status: str
    final_response: str
    search_spec: SearchSpec
    matches: list[JobLead] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    recommendation_summary: str = ""

    def to_payload(self) -> dict:
        return {
            "status": self.status,
            "final_response": self.final_response,
            "search_spec": self.search_spec.to_payload(),
            "matches": [match.to_payload() for match in self.matches],
            "output_paths": self.output_paths,
            "recommendation_summary": self.recommendation_summary,
        }
