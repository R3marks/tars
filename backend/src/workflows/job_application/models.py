from dataclasses import dataclass, field


ArtifactType = str
OutputMode = str
TaskStatus = str


@dataclass(frozen=True)
class OutputTarget:
    path: str
    mode: OutputMode


@dataclass(frozen=True)
class ApplicationRequest:
    query: str
    requested_artifacts: list[ArtifactType] = field(default_factory=list)
    has_explicit_output_targets: bool = False
    job_description_path: str = ""
    experience_path: str = ""
    cv_template_path: str = ""
    cover_letter_template_path: str = ""
    motivations_path: str = ""
    questions_path: str = ""
    application_url: str = ""
    company_name: str = ""
    company_address: str = ""
    output_targets: dict[ArtifactType, OutputTarget] = field(default_factory=dict)


@dataclass(frozen=True)
class ApplicationField:
    identifier: str
    label: str
    required: bool = False
    field_type: str = "text"


@dataclass(frozen=True)
class JobPageArtifact:
    source_url: str
    platform: str = ""
    role_title: str = ""
    company_name: str = ""
    location: str = ""
    job_description_text: str = ""
    application_fields: list[ApplicationField] = field(default_factory=list)
    raw_page_markdown: str = ""
    fetch_status: str = ""


@dataclass(frozen=True)
class JobRequirementsArtifact:
    role_summary: str
    must_have_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    ats_keywords: list[str] = field(default_factory=list)
    company_context: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceExperienceArtifact:
    identifier: str
    company: str
    role_title: str
    date_range: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateEvidenceArtifact:
    core_skills: list[str] = field(default_factory=list)
    relevant_experience: list[str] = field(default_factory=list)
    strongest_points: list[str] = field(default_factory=list)
    truth_constraints: list[str] = field(default_factory=list)
    source_experience_sections: list[SourceExperienceArtifact] = field(default_factory=list)


@dataclass(frozen=True)
class MotivationArtifact:
    motivations: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    source_path: str = ""


@dataclass(frozen=True)
class QuestionItem:
    identifier: str
    question: str


@dataclass(frozen=True)
class QuestionsArtifact:
    questions: list[QuestionItem] = field(default_factory=list)
    source_path: str = ""


@dataclass(frozen=True)
class ApplicationResearchArtifact:
    company_name: str = ""
    company_address: str = ""
    application_url: str = ""
    role_title: str = ""
    location: str = ""
    platform: str = ""
    company_context: list[str] = field(default_factory=list)
    motivation_hooks: list[str] = field(default_factory=list)
    application_fields: list[ApplicationField] = field(default_factory=list)


@dataclass(frozen=True)
class ExperienceSectionArtifact:
    identifier: str
    heading: str
    role_title: str
    current_bullets: list[str] = field(default_factory=list)
    original_bullet_html: str = ""
    bullet_limit: int = 3
    bullet_word_limit: int = 30


@dataclass(frozen=True)
class TemplateStructureArtifact:
    section_order: list[str]
    current_summary: str
    current_technologies: list[str]
    current_expertise: list[str]
    experience_sections: list[ExperienceSectionArtifact] = field(default_factory=list)
    summary_word_limit: int = 38
    technology_item_limit: int = 8
    expertise_item_limit: int = 6


@dataclass(frozen=True)
class ExperienceSectionPlan:
    identifier: str
    heading: str
    priority_reason: str
    bullet_goals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TailoringPlanArtifact:
    summary_focus: str
    technologies: list[str] = field(default_factory=list)
    expertise: list[str] = field(default_factory=list)
    sections_to_rewrite: list[ExperienceSectionPlan] = field(default_factory=list)
    keep_unchanged: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperienceSectionDraft:
    identifier: str
    heading: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CvSectionDraft:
    summary: str
    technologies: list[str] = field(default_factory=list)
    expertise: list[str] = field(default_factory=list)
    experience_sections: list[ExperienceSectionDraft] = field(default_factory=list)


@dataclass(frozen=True)
class DraftReview:
    decision: str
    reviewer_summary: str
    issues: list[str] = field(default_factory=list)
    revision_targets: list[str] = field(default_factory=list)
    stop_reason: str = ""


@dataclass(frozen=True)
class SkillPackageConfig:
    name: str
    editable_experience_section_limit: int = 2
    max_review_iterations: int = 2


@dataclass(frozen=True)
class SkillResult:
    artifact_type: ArtifactType
    status: TaskStatus
    output_paths: list[str] = field(default_factory=list)
    output_mode: OutputMode = ""
    summary: str = ""
    missing_inputs: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)
    change_summary: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ApplicationContext:
    request: ApplicationRequest
    job_description_text: str = ""
    job_posting_markdown: str = ""
    experience_text: str = ""
    cv_template_text: str = ""
    cover_letter_template_text: str = ""
    motivations_text: str = ""
    questions_text: str = ""
    profile_defaults: dict[str, str] = field(default_factory=dict)
    job_page: JobPageArtifact | None = None
    job_requirements: JobRequirementsArtifact | None = None
    candidate_evidence: CandidateEvidenceArtifact | None = None
    application_research: ApplicationResearchArtifact | None = None
    motivations: MotivationArtifact | None = None
    questions: QuestionsArtifact | None = None


@dataclass(frozen=True)
class WorkflowRunResult:
    status: TaskStatus
    final_response: str
    skill_results: list[SkillResult] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
