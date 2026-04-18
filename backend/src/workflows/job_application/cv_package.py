from pathlib import Path
from typing import Awaitable, Callable

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.workflows.job_application.experience_parser import find_best_source_experience_section
from src.workflows.job_application.models import (
    ApplicationContext,
    CandidateEvidenceArtifact,
    CvSectionDraft,
    DraftReview,
    ExperienceSectionDraft,
    ExperienceSectionPlan,
    JobRequirementsArtifact,
    OutputTarget,
    SkillPackageConfig,
    SkillResult,
    TailoringPlanArtifact,
)
from src.workflows.job_application.pdf_exporter import export_html_to_pdf
from src.workflows.job_application.shared_context import call_required_function
from src.workflows.job_application.skill import (
    build_experience_rewrite_prompt,
    build_profile_draft_prompt,
    build_review_prompt,
)
from src.workflows.job_application.template_editor import (
    apply_cv_draft_to_template,
    extract_template_structure,
    find_drafted_section,
)
from src.workflows.job_application.truth_guard import (
    choose_supported_text,
    filter_supported_items,
    normalize_text,
    overlap_tokens,
    tokenize_for_overlap,
)

profileDraftTools = [
    {
        "type": "function",
        "function": {
            "name": "draft_profile_sections",
            "description": "Draft the profile sections of a CV.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                    "expertise": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "technologies", "expertise"],
            },
        },
    }
]

experienceSectionTools = [
    {
        "type": "function",
        "function": {
            "name": "rewrite_experience_section",
            "description": "Rewrite one CV experience section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "rewrite_notes": {"type": "string"},
                },
                "required": ["bullets", "rewrite_notes"],
            },
        },
    }
]

reviewTools = [
    {
        "type": "function",
        "function": {
            "name": "review_cv_draft",
            "description": "Review whether the tailored CV draft is strong enough to save.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["pass", "revise"]},
                    "reviewer_summary": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "revision_targets": {"type": "array", "items": {"type": "string"}},
                    "stop_reason": {"type": "string"},
                },
                "required": [
                    "decision",
                    "reviewer_summary",
                    "issues",
                    "revision_targets",
                    "stop_reason",
                ],
            },
        },
    }
]

async def run_cv_package(
    application_context: ApplicationContext,
    config: SkillPackageConfig,
    worker_model: Model,
    review_model: Model,
    model_manager: ModelManager,
    progress_callback: Callable[[str, str, dict | None], Awaitable[None]] | None = None,
) -> SkillResult:
    missing_inputs = []
    if not application_context.job_description_text:
        missing_inputs.append("job description")
    if not application_context.experience_text:
        missing_inputs.append("experience notes")
    if not application_context.cv_template_text:
        missing_inputs.append("cv template")
    if application_context.job_requirements is None:
        missing_inputs.append("job requirements artifact")
    if application_context.candidate_evidence is None:
        missing_inputs.append("candidate evidence artifact")

    if missing_inputs:
        return SkillResult(
            artifact_type="cv",
            status="blocked",
            summary="Could not generate a CV because required inputs were missing.",
            missing_inputs=missing_inputs,
            review_notes=["Provide the missing CV inputs and rerun the workflow."],
        )

    await report_progress(
        progress_callback,
        "analyzing_cv_template",
        "CV package: analyzing current template",
    )
    template_structure = extract_template_structure(application_context.cv_template_text)
    tailoring_plan = build_tailoring_plan(
        template_structure=template_structure,
        job_requirements=application_context.job_requirements,
        candidate_evidence=application_context.candidate_evidence,
        editable_section_limit=config.editable_experience_section_limit,
    )

    await report_progress(
        progress_callback,
        "drafting_profile_sections",
        "CV package: drafting profile summary and skills",
    )
    profile_draft = draft_profile_sections(
        query=application_context.request.query,
        template_structure=template_structure,
        job_requirements=application_context.job_requirements,
        candidate_evidence=application_context.candidate_evidence,
        model=worker_model,
        model_manager=model_manager,
    )
    await report_progress(
        progress_callback,
        "rewriting_experience_sections",
        "CV package: rewriting selected experience sections",
        {
            "sections_selected": len(tailoring_plan.sections_to_rewrite),
        },
    )
    drafted_sections = draft_experience_sections(
        query=application_context.request.query,
        template_structure=template_structure,
        job_requirements=application_context.job_requirements,
        candidate_evidence=application_context.candidate_evidence,
        tailoring_plan=tailoring_plan,
        model=worker_model,
        model_manager=model_manager,
    )
    cv_section_draft = CvSectionDraft(
        summary=profile_draft["summary"],
        technologies=profile_draft["technologies"],
        expertise=profile_draft["expertise"],
        experience_sections=drafted_sections,
    )

    review = DraftReview(
        decision="pass",
        reviewer_summary="Draft created.",
    )

    iteration_count = 1
    while iteration_count <= config.max_review_iterations:
        await report_progress(
            progress_callback,
            "reviewing_cv_draft",
            f"CV package: review pass {iteration_count}",
            {
                "review_pass": iteration_count,
            },
        )
        review = review_cv_draft(
            query=application_context.request.query,
            job_requirements=application_context.job_requirements,
            candidate_evidence=application_context.candidate_evidence,
            cv_section_draft=cv_section_draft,
            model=review_model,
            model_manager=model_manager,
        )

        if review.decision == "pass":
            break

        if iteration_count >= config.max_review_iterations:
            break

        await report_progress(
            progress_callback,
            "revising_cv_draft",
            f"CV package: revising draft after review pass {iteration_count}",
            {
                "review_pass": iteration_count,
            },
        )
        profile_draft = draft_profile_sections(
            query=application_context.request.query,
            template_structure=template_structure,
            job_requirements=application_context.job_requirements,
            candidate_evidence=application_context.candidate_evidence,
            model=worker_model,
            model_manager=model_manager,
            previous_draft=cv_section_draft,
            review=review,
        )
        drafted_sections = draft_experience_sections(
            query=application_context.request.query,
            template_structure=template_structure,
            job_requirements=application_context.job_requirements,
            candidate_evidence=application_context.candidate_evidence,
            tailoring_plan=tailoring_plan,
            model=worker_model,
            model_manager=model_manager,
            previous_draft=cv_section_draft,
            review=review,
        )
        cv_section_draft = CvSectionDraft(
            summary=profile_draft["summary"],
            technologies=profile_draft["technologies"],
            expertise=profile_draft["expertise"],
            experience_sections=drafted_sections,
        )
        iteration_count += 1

    await report_progress(
        progress_callback,
        "saving_cv_outputs",
        "CV package: saving final CV outputs",
    )
    final_html = apply_cv_draft_to_template(
        application_context.cv_template_text,
        cv_section_draft,
        template_structure,
    )
    output_target = application_context.request.output_targets["cv"]
    output_path = Path(output_target.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding="utf-8")

    output_paths = [str(output_path)]
    pdf_output_path = ""
    if output_target.mode == "html_document":
        pdf_output_path, _ = export_html_to_pdf(output_path)
        if pdf_output_path:
            output_paths.append(pdf_output_path)

    change_summary, unchanged_summary = build_change_summary(
        template_structure=template_structure,
        cv_section_draft=cv_section_draft,
    )
    review_notes = [review.reviewer_summary]
    review_notes.extend(unchanged_summary)

    return SkillResult(
        artifact_type="cv",
        status="completed",
        output_paths=output_paths,
        output_mode=output_target.mode,
        summary=f"Saved a tailored CV draft to {output_path}.",
        review_notes=review_notes,
        change_summary=change_summary,
    )


def build_tailoring_plan(
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    editable_section_limit: int,
) -> TailoringPlanArtifact:
    selected_sections = rank_experience_sections(
        template_structure=template_structure,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        editable_section_limit=editable_section_limit,
    )
    return TailoringPlanArtifact(
        summary_focus=job_requirements.role_summary,
        technologies=build_supported_technologies(
            candidate_evidence,
            template_structure.current_technologies,
        ),
        expertise=build_supported_expertise(
            candidate_evidence,
            template_structure.current_expertise,
        ),
        sections_to_rewrite=selected_sections,
        keep_unchanged=[
            "preserve non-selected experience sections",
            "preserve education",
            "preserve extracurricular",
        ],
    )


def draft_experience_sections(
    query: str,
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    tailoring_plan: TailoringPlanArtifact,
    model: Model,
    model_manager: ModelManager,
    previous_draft: CvSectionDraft | None = None,
    review: DraftReview | None = None,
) -> list[ExperienceSectionDraft]:
    drafted_sections = []
    for section in template_structure.experience_sections:
        section_plan = find_section_plan(tailoring_plan.sections_to_rewrite, section.identifier)
        previous_section = None if previous_draft is None else find_drafted_section(previous_draft.experience_sections, section.identifier)

        if section_plan is None:
            drafted_sections.append(
                ExperienceSectionDraft(
                    identifier=section.identifier,
                    heading=section.heading,
                    bullets=section.current_bullets,
                ),
            )
            continue

        drafted_sections.append(
            rewrite_experience_section(
                query=query,
                section=section,
                section_plan=section_plan,
                job_requirements=job_requirements,
                candidate_evidence=candidate_evidence,
                model=model,
                model_manager=model_manager,
                previous_section=previous_section,
                review=review,
            ),
        )

    return drafted_sections


def draft_profile_sections(
    query: str,
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    model: Model,
    model_manager: ModelManager,
    previous_draft: CvSectionDraft | None = None,
    review: DraftReview | None = None,
) -> dict:
    candidate_evidence_text = build_candidate_evidence_text(candidate_evidence)
    summary_support_text = " ".join(
        [
            candidate_evidence_text,
            template_structure.current_summary,
            " ".join(template_structure.current_technologies),
            " ".join(template_structure.current_expertise),
        ],
    )
    arguments = call_required_function(
        model=model,
        model_manager=model_manager,
        prompt=build_profile_draft_prompt(
            query=query,
            job_requirements_text=build_job_requirements_text(job_requirements),
            candidate_evidence_text=candidate_evidence_text,
            summary_word_limit=template_structure.summary_word_limit,
            technology_item_limit=template_structure.technology_item_limit,
            expertise_item_limit=template_structure.expertise_item_limit,
            current_summary=template_structure.current_summary,
            current_technologies=template_structure.current_technologies,
            current_expertise=template_structure.current_expertise,
            previous_summary="" if previous_draft is None else previous_draft.summary,
            previous_technologies=[] if previous_draft is None else previous_draft.technologies,
            previous_expertise=[] if previous_draft is None else previous_draft.expertise,
            review_targets=[] if review is None else review.revision_targets,
        ),
        tools=profileDraftTools,
        function_name="draft_profile_sections",
    )
    return {
        "summary": trim_to_word_limit(
            choose_supported_text(
                proposed_text=arguments["summary"].strip(),
                fallback_text=template_structure.current_summary,
                allowed_text=summary_support_text,
                minimum_overlap=3,
                unsupported_token_limit=2,
            ),
            template_structure.summary_word_limit,
        ),
        "technologies": limit_list(
            filter_supported_items(
                normalize_list(arguments["technologies"]),
                allowed_text=candidate_evidence_text,
                fallback_items=template_structure.current_technologies,
                minimum_overlap=1,
            )
            or build_supported_technologies(
                candidate_evidence,
                template_structure.current_technologies,
            ),
            template_structure.technology_item_limit,
        ),
        "expertise": limit_list(
            filter_supported_items(
                normalize_list(arguments["expertise"]),
                allowed_text=candidate_evidence_text,
                fallback_items=template_structure.current_expertise,
                minimum_overlap=2,
            )
            or build_supported_expertise(
                candidate_evidence,
                template_structure.current_expertise,
            ),
            template_structure.expertise_item_limit,
        ),
    }


def rewrite_experience_section(
    query: str,
    section,
    section_plan: ExperienceSectionPlan,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    model: Model,
    model_manager: ModelManager,
    previous_section: ExperienceSectionDraft | None,
    review: DraftReview | None,
) -> ExperienceSectionDraft:
    source_section = find_best_source_experience_section(
        section,
        candidate_evidence.source_experience_sections,
    )
    if source_section is None:
        return ExperienceSectionDraft(
            identifier=section.identifier,
            heading=section.heading,
            bullets=section.current_bullets,
        )

    arguments = call_required_function(
        model=model,
        model_manager=model_manager,
        prompt=build_experience_rewrite_prompt(
            query=query,
            job_requirements_text=build_job_requirements_text(job_requirements),
            candidate_evidence_text=build_candidate_evidence_text(candidate_evidence),
            section_heading=section.heading,
            role_title=section.role_title,
            current_bullets=section.current_bullets,
            source_bullets=source_section.bullets,
            bullet_limit=section.bullet_limit,
            bullet_word_limit=section.bullet_word_limit,
            priority_reason=section_plan.priority_reason,
            bullet_goals=section_plan.bullet_goals,
            previous_bullets=[] if previous_section is None else previous_section.bullets,
            review_targets=[] if review is None else review.revision_targets,
        ),
        tools=experienceSectionTools,
        function_name="rewrite_experience_section",
    )
    rewritten_bullets = select_experience_bullets(
        proposed_bullets=normalize_list(arguments["bullets"]),
        current_bullets=section.current_bullets,
        source_bullets=source_section.bullets,
        bullet_limit=section.bullet_limit,
        bullet_word_limit=section.bullet_word_limit,
        candidate_evidence=candidate_evidence,
    )
    return ExperienceSectionDraft(
        identifier=section.identifier,
        heading=section.heading,
        bullets=rewritten_bullets,
    )


def review_cv_draft(
    query: str,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    cv_section_draft: CvSectionDraft,
    model: Model,
    model_manager: ModelManager,
) -> DraftReview:
    rewritten_sections = [
        f"{section.heading}: {section.bullets}"
        for section in cv_section_draft.experience_sections
    ]
    arguments = call_required_function(
        model=model,
        model_manager=model_manager,
        prompt=build_review_prompt(
            query=query,
            job_requirements_text=build_job_requirements_text(job_requirements),
            candidate_evidence_text=build_candidate_evidence_text(candidate_evidence),
            draft_summary=cv_section_draft.summary,
            draft_technologies=cv_section_draft.technologies,
            draft_expertise=cv_section_draft.expertise,
            rewritten_sections=rewritten_sections,
        ),
        tools=reviewTools,
        function_name="review_cv_draft",
    )
    return DraftReview(
        decision=arguments["decision"],
        reviewer_summary=arguments["reviewer_summary"].strip(),
        issues=normalize_list(arguments["issues"]),
        revision_targets=normalize_list(arguments["revision_targets"]),
        stop_reason=arguments["stop_reason"].strip(),
    )


def rank_experience_sections(
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    editable_section_limit: int,
) -> list[ExperienceSectionPlan]:
    keyword_text = build_job_requirements_text(job_requirements) + " " + build_candidate_evidence_text(candidate_evidence)
    scored_sections = []
    for section in template_structure.experience_sections:
        section_text = f"{section.heading} {section.role_title} {' '.join(section.current_bullets)}"
        scored_sections.append((len(overlap_tokens(section_text, keyword_text)), section))

    scored_sections.sort(key=lambda item: item[0], reverse=True)
    selected_sections = [item[1] for item in scored_sections[:editable_section_limit]]

    return [
        ExperienceSectionPlan(
            identifier=section.identifier,
            heading=section.heading,
            priority_reason=f"Most relevant overlap score for this request: {len(overlap_tokens(' '.join(section.current_bullets), keyword_text))}",
            bullet_goals=build_section_goals(job_requirements),
        )
        for section in selected_sections
    ]


def build_section_goals(job_requirements: JobRequirementsArtifact) -> list[str]:
    goals = [
        f"Surface truthful overlap with {keyword}"
        for keyword in (job_requirements.must_have_skills + job_requirements.responsibilities)[:3]
    ]
    if goals:
        return goals

    return ["Keep the strongest commercially meaningful outcomes"]


def build_supported_technologies(
    candidate_evidence: CandidateEvidenceArtifact,
    fallback_items: list[str],
) -> list[str]:
    evidence_text = build_candidate_evidence_text(candidate_evidence)
    supported_items = filter_supported_items(
        items=candidate_evidence.core_skills,
        allowed_text=evidence_text,
        fallback_items=fallback_items,
        minimum_overlap=1,
    )
    return supported_items or fallback_items


def build_supported_expertise(
    candidate_evidence: CandidateEvidenceArtifact,
    fallback_items: list[str],
) -> list[str]:
    evidence_text = build_candidate_evidence_text(candidate_evidence)
    supported_items = filter_supported_items(
        items=fallback_items,
        allowed_text=evidence_text,
        fallback_items=fallback_items,
        minimum_overlap=1,
    )
    return supported_items or fallback_items


def build_job_requirements_text(job_requirements: JobRequirementsArtifact) -> str:
    return " ".join(
        [job_requirements.role_summary]
        + job_requirements.must_have_skills
        + job_requirements.responsibilities
        + job_requirements.ats_keywords
        + job_requirements.company_context,
    )


def build_candidate_evidence_text(candidate_evidence: CandidateEvidenceArtifact) -> str:
    return " ".join(
        candidate_evidence.core_skills
        + candidate_evidence.relevant_experience
        + candidate_evidence.strongest_points
        + candidate_evidence.truth_constraints,
    )


def select_experience_bullets(
    proposed_bullets: list[str],
    current_bullets: list[str],
    source_bullets: list[str],
    bullet_limit: int,
    bullet_word_limit: int,
    candidate_evidence: CandidateEvidenceArtifact,
) -> list[str]:
    section_support_text = " ".join(
        source_bullets
        + current_bullets
        + candidate_evidence.truth_constraints
        + candidate_evidence.strongest_points,
    )
    cleaned_bullets = []

    for index, bullet in enumerate(proposed_bullets[:bullet_limit]):
        if not bullet.strip():
            continue

        trimmed_bullet = trim_to_word_limit(bullet, bullet_word_limit)
        fallback_bullet = current_bullets[min(index, len(current_bullets) - 1)]
        cleaned_bullets.append(
            choose_supported_text(
                proposed_text=trimmed_bullet,
                fallback_text=fallback_bullet,
                allowed_text=section_support_text,
                minimum_overlap=2,
                unsupported_token_limit=2,
            ),
        )

    if not cleaned_bullets:
        cleaned_bullets = [
            trim_to_word_limit(bullet, bullet_word_limit)
            for bullet in current_bullets[:bullet_limit]
        ]

    while len(cleaned_bullets) < min(bullet_limit, len(current_bullets)):
        cleaned_bullets.append(
            trim_to_word_limit(current_bullets[len(cleaned_bullets)], bullet_word_limit),
        )

    return cleaned_bullets[:bullet_limit]


def build_change_summary(
    template_structure,
    cv_section_draft: CvSectionDraft,
) -> tuple[list[str], list[str]]:
    change_summary = []
    unchanged_summary = []

    if normalize_text(template_structure.current_summary) != normalize_text(cv_section_draft.summary):
        change_summary.append("updated the opening summary")
    else:
        unchanged_summary.append("kept the opening summary")

    if normalize_text(", ".join(template_structure.current_technologies)) != normalize_text(", ".join(cv_section_draft.technologies)):
        change_summary.append("updated the technologies list")
    else:
        unchanged_summary.append("kept the technologies list")

    if normalize_text(", ".join(template_structure.current_expertise)) != normalize_text(", ".join(cv_section_draft.expertise)):
        change_summary.append("updated the expertise list")
    else:
        unchanged_summary.append("kept the expertise list")

    rewritten_sections = []
    unchanged_sections = []
    for section in template_structure.experience_sections:
        drafted_section = find_drafted_section(cv_section_draft.experience_sections, section.identifier)
        if drafted_section is None:
            continue

        changed_count = count_changed_bullets(section.current_bullets, drafted_section.bullets)
        if changed_count > 0:
            rewritten_sections.append(f"{section.heading} ({changed_count}/{len(section.current_bullets)} bullets)")
            continue

        unchanged_sections.append(section.heading)

    if rewritten_sections:
        change_summary.append("rewrote experience sections: " + ", ".join(rewritten_sections))

    if unchanged_sections:
        unchanged_summary.append("kept experience sections: " + ", ".join(unchanged_sections))

    return change_summary, unchanged_summary


def count_changed_bullets(current_bullets: list[str], drafted_bullets: list[str]) -> int:
    return sum(
        1
        for current_bullet, drafted_bullet in zip(current_bullets, drafted_bullets)
        if normalize_text(current_bullet) != normalize_text(drafted_bullet)
    )


def find_section_plan(
    section_plans: list[ExperienceSectionPlan],
    identifier: str,
) -> ExperienceSectionPlan | None:
    for section_plan in section_plans:
        if section_plan.identifier != identifier:
            continue

        return section_plan

    return None


def normalize_list(values) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def trim_to_word_limit(text: str, word_limit: int) -> str:
    words = text.split()
    if len(words) <= word_limit:
        return text.strip()

    return " ".join(words[:word_limit]).rstrip(".") + "."


def limit_list(items: list[str], item_limit: int) -> list[str]:
    return items[:item_limit]


async def report_progress(
    progress_callback: Callable[[str, str, dict | None], Awaitable[None]] | None,
    current_task: str,
    step_label: str,
    details: dict | None = None,
):
    if progress_callback is None:
        return

    await progress_callback(current_task, step_label, details)
