from dataclasses import dataclass, field


@dataclass(frozen=True)
class JobApplicationRequest:
    query: str
    request_type: str
    job_description_path: str
    experience_path: str
    template_path: str
    output_path: str


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
class SkillPackage:
    name: str
    editable_experience_section_limit: int = 2
    max_review_iterations: int = 2


@dataclass(frozen=True)
class WorkflowRunResult:
    status: str
    output_path: str
    iteration_count: int
    final_response: str
    review: DraftReview
    pdf_output_path: str = ""
    pdf_page_count: int | None = None
    change_summary: list[str] = field(default_factory=list)
    unchanged_summary: list[str] = field(default_factory=list)
