import json
import logging
import re
from pathlib import Path

from fastapi import WebSocket

from src.agents.agent_utils import read_file
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.model_roles import OrchestrationModels
from src.workflows.job_application.experience_parser import (
    find_best_source_experience_section,
    parse_source_experience_sections,
)
from src.workflows.job_application.models import (
    CandidateEvidenceArtifact,
    CvSectionDraft,
    DraftReview,
    ExperienceSectionDraft,
    ExperienceSectionPlan,
    JobRequirementsArtifact,
    TailoringPlanArtifact,
    WorkflowRunResult,
)
from src.workflows.job_application.pdf_exporter import export_html_to_pdf
from src.workflows.job_application.query_parser import parse_job_application_request
from src.workflows.job_application.skill import (
    build_candidate_evidence_prompt,
    build_experience_rewrite_prompt,
    build_job_requirements_prompt,
    build_profile_draft_prompt,
    build_review_prompt,
    get_job_application_skill_package,
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

logger = logging.getLogger("uvicorn.error")

jobRequirementsTools = [
    {
        "type": "function",
        "function": {
            "name": "save_job_requirements",
            "description": "Capture the most important job requirements for CV tailoring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role_summary": {"type": "string"},
                    "must_have_skills": {"type": "array", "items": {"type": "string"}},
                    "responsibilities": {"type": "array", "items": {"type": "string"}},
                    "ats_keywords": {"type": "array", "items": {"type": "string"}},
                    "company_context": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "role_summary",
                    "must_have_skills",
                    "responsibilities",
                    "ats_keywords",
                    "company_context",
                ],
            },
        },
    }
]

candidateEvidenceTools = [
    {
        "type": "function",
        "function": {
            "name": "save_candidate_evidence",
            "description": "Capture truthful reusable evidence for CV tailoring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "core_skills": {"type": "array", "items": {"type": "string"}},
                    "relevant_experience": {"type": "array", "items": {"type": "string"}},
                    "strongest_points": {"type": "array", "items": {"type": "string"}},
                    "truth_constraints": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "core_skills",
                    "relevant_experience",
                    "strongest_points",
                    "truth_constraints",
                ],
            },
        },
    }
]

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


async def run_job_application_workflow(
    query: str,
    websocket: WebSocket,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
) -> WorkflowRunResult:
    skillPackage = get_job_application_skill_package()
    request = parse_job_application_request(query)

    if request.request_type != "cv":
        review = DraftReview(
            decision="revise",
            reviewer_summary="Only CV generation is currently supported in this workflow.",
            stop_reason="Unsupported request type.",
        )
        return WorkflowRunResult(
            status="unsupported",
            output_path="",
            iteration_count=0,
            final_response="I can route CV generation through this workflow, but cover letters still need the next pass.",
            review=review,
        )

    await sendStatus(websocket, "Reading job application source files")
    job_description_text = read_file(request.job_description_path)
    experience_text = read_file(request.experience_path)
    template_html = read_file(request.template_path)

    for file_content in [job_description_text, experience_text, template_html]:
        if not file_content.startswith("Error"):
            continue

        review = DraftReview(
            decision="revise",
            reviewer_summary=file_content,
            stop_reason="A required workflow input file could not be read.",
        )
        return WorkflowRunResult(
            status="error",
            output_path="",
            iteration_count=0,
            final_response=file_content,
            review=review,
        )

    template_structure = extract_template_structure(template_html)

    await sendStatus(websocket, "Extracting role requirements")
    job_requirements = extractJobRequirements(
        query=query,
        job_description_text=job_description_text,
        model=orchestration_models.planner_model,
        model_manager=model_manager,
    )

    await sendStatus(websocket, "Extracting truthful candidate evidence")
    candidate_evidence = extractCandidateEvidence(
        query=query,
        experience_text=experience_text,
        template_structure=template_structure,
        model=orchestration_models.worker_model,
        model_manager=model_manager,
    )

    tailoring_plan = buildTailoringPlan(
        template_structure=template_structure,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        editable_section_limit=skillPackage.editable_experience_section_limit,
    )

    await sendStatus(websocket, "Drafting revised CV sections")
    cv_section_draft = draftCvSections(
        query=query,
        template_structure=template_structure,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        tailoring_plan=tailoring_plan,
        model=orchestration_models.worker_model,
        model_manager=model_manager,
    )

    review = DraftReview(
        decision="pass",
        reviewer_summary="Draft created.",
    )
    iteration_count = 1

    while iteration_count <= skillPackage.max_review_iterations:
        await sendStatus(websocket, f"Reviewing draft pass {iteration_count}")
        review = reviewCvDraft(
            query=query,
            job_requirements=job_requirements,
            candidate_evidence=candidate_evidence,
            cv_section_draft=cv_section_draft,
            model=orchestration_models.review_model,
            model_manager=model_manager,
        )

        if review.decision == "pass":
            break

        if iteration_count >= skillPackage.max_review_iterations:
            break

        await sendStatus(websocket, f"Improving draft pass {iteration_count + 1}")
        cv_section_draft = draftCvSections(
            query=query,
            template_structure=template_structure,
            job_requirements=job_requirements,
            candidate_evidence=candidate_evidence,
            tailoring_plan=tailoring_plan,
            model=orchestration_models.worker_model,
            model_manager=model_manager,
            previous_draft=cv_section_draft,
            review=review,
        )
        iteration_count += 1

    final_html = apply_cv_draft_to_template(
        template_html,
        cv_section_draft,
        template_structure,
    )

    await sendStatus(websocket, "Saving tailored CV")
    output_path = Path(request.output_path)
    output_path.write_text(final_html, encoding="utf-8")

    await sendStatus(websocket, "Generating PDF preview")
    pdf_output_path, pdf_page_count = export_html_to_pdf(output_path)
    change_summary, unchanged_summary = buildChangeSummary(
        template_structure=template_structure,
        cv_section_draft=cv_section_draft,
    )

    await sendWorkflowSummary(
        websocket=websocket,
        output_path=request.output_path,
        pdf_output_path=pdf_output_path,
        pdf_page_count=pdf_page_count,
        change_summary=change_summary,
        unchanged_summary=unchanged_summary,
        review=review,
    )

    final_response = buildFinalResponse(
        output_path=request.output_path,
        pdf_output_path=pdf_output_path,
        pdf_page_count=pdf_page_count,
        change_summary=change_summary,
        unchanged_summary=unchanged_summary,
        review=review,
    )

    conversation_history.append_message(Message(role="assistant", content=final_response))

    return WorkflowRunResult(
        status="completed",
        output_path=request.output_path,
        iteration_count=iteration_count,
        final_response=final_response,
        review=review,
        pdf_output_path=pdf_output_path,
        pdf_page_count=pdf_page_count,
        change_summary=change_summary,
        unchanged_summary=unchanged_summary,
    )


def extractJobRequirements(
    query: str,
    job_description_text: str,
    model: Model,
    model_manager: ModelManager,
) -> JobRequirementsArtifact:
    arguments = callRequiredFunction(
        model=model,
        model_manager=model_manager,
        prompt=build_job_requirements_prompt(query, job_description_text),
        tools=jobRequirementsTools,
        function_name="save_job_requirements",
    )
    return JobRequirementsArtifact(
        role_summary=arguments["role_summary"].strip(),
        must_have_skills=normalizeList(arguments["must_have_skills"]),
        responsibilities=normalizeList(arguments["responsibilities"]),
        ats_keywords=normalizeList(arguments["ats_keywords"]),
        company_context=normalizeList(arguments["company_context"]),
    )


def extractCandidateEvidence(
    query: str,
    experience_text: str,
    template_structure,
    model: Model,
    model_manager: ModelManager,
) -> CandidateEvidenceArtifact:
    source_experience_sections = parse_source_experience_sections(experience_text)
    section_summaries = [
        f"{section.heading}: {section.current_bullets}"
        for section in template_structure.experience_sections
    ]
    arguments = callRequiredFunction(
        model=model,
        model_manager=model_manager,
        prompt=build_candidate_evidence_prompt(query, experience_text, section_summaries),
        tools=candidateEvidenceTools,
        function_name="save_candidate_evidence",
    )
    return CandidateEvidenceArtifact(
        core_skills=normalizeList(arguments["core_skills"]),
        relevant_experience=normalizeList(arguments["relevant_experience"]),
        strongest_points=normalizeList(arguments["strongest_points"]),
        truth_constraints=normalizeList(arguments["truth_constraints"]),
        source_experience_sections=source_experience_sections,
    )


def buildTailoringPlan(
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    editable_section_limit: int,
) -> TailoringPlanArtifact:
    selected_sections = rankExperienceSections(
        template_structure=template_structure,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        editable_section_limit=editable_section_limit,
    )
    return TailoringPlanArtifact(
        summary_focus=job_requirements.role_summary,
        technologies=buildSupportedTechnologies(
            candidate_evidence,
            template_structure.current_technologies,
        ),
        expertise=buildSupportedExpertise(
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


def draftCvSections(
    query: str,
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    tailoring_plan: TailoringPlanArtifact,
    model: Model,
    model_manager: ModelManager,
    previous_draft: CvSectionDraft | None = None,
    review: DraftReview | None = None,
) -> CvSectionDraft:
    profile_draft = draftProfileSections(
        query=query,
        template_structure=template_structure,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        model=model,
        model_manager=model_manager,
        previous_draft=previous_draft,
        review=review,
    )

    drafted_sections = []
    for section in template_structure.experience_sections:
        section_plan = findSectionPlan(tailoring_plan.sections_to_rewrite, section.identifier)
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
            rewriteExperienceSection(
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

    return CvSectionDraft(
        summary=profile_draft["summary"],
        technologies=profile_draft["technologies"],
        expertise=profile_draft["expertise"],
        experience_sections=drafted_sections,
    )


def draftProfileSections(
    query: str,
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    model: Model,
    model_manager: ModelManager,
    previous_draft: CvSectionDraft | None,
    review: DraftReview | None,
) -> dict:
    candidate_evidence_text = buildCandidateEvidenceText(candidate_evidence)
    summary_support_text = " ".join(
        [
            candidate_evidence_text,
            template_structure.current_summary,
            " ".join(template_structure.current_technologies),
            " ".join(template_structure.current_expertise),
        ],
    )
    prompt = build_profile_draft_prompt(
        query=query,
        job_requirements_text=buildJobRequirementsText(job_requirements),
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
    )
    arguments = callRequiredFunction(
        model=model,
        model_manager=model_manager,
        prompt=prompt,
        tools=profileDraftTools,
        function_name="draft_profile_sections",
    )
    return {
        "summary": trimToWordLimit(
            choose_supported_text(
                proposed_text=arguments["summary"].strip(),
                fallback_text=template_structure.current_summary,
                allowed_text=summary_support_text,
                minimum_overlap=3,
                unsupported_token_limit=2,
            ),
            template_structure.summary_word_limit,
        ),
        "technologies": limitList(
            filter_supported_items(
                normalizeList(arguments["technologies"]),
                allowed_text=candidate_evidence_text,
                fallback_items=template_structure.current_technologies,
                minimum_overlap=1,
            )
            or buildSupportedTechnologies(
                candidate_evidence,
                template_structure.current_technologies,
            ),
            template_structure.technology_item_limit,
        ),
        "expertise": limitList(
            filter_supported_items(
                normalizeList(arguments["expertise"]),
                allowed_text=candidate_evidence_text,
                fallback_items=template_structure.current_expertise,
                minimum_overlap=2,
            )
            or buildSupportedExpertise(
                candidate_evidence,
                template_structure.current_expertise,
            ),
            template_structure.expertise_item_limit,
        ),
    }


def rewriteExperienceSection(
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

    source_bullets = source_section.bullets

    prompt = build_experience_rewrite_prompt(
        query=query,
        job_requirements_text=buildJobRequirementsText(job_requirements),
        candidate_evidence_text=buildCandidateEvidenceText(candidate_evidence),
        section_heading=section.heading,
        role_title=section.role_title,
        current_bullets=section.current_bullets,
        source_bullets=source_bullets,
        bullet_limit=section.bullet_limit,
        bullet_word_limit=section.bullet_word_limit,
        priority_reason=section_plan.priority_reason,
        bullet_goals=section_plan.bullet_goals,
        previous_bullets=[] if previous_section is None else previous_section.bullets,
        review_targets=[] if review is None else review.revision_targets,
    )
    arguments = callRequiredFunction(
        model=model,
        model_manager=model_manager,
        prompt=prompt,
        tools=experienceSectionTools,
        function_name="rewrite_experience_section",
    )
    rewritten_bullets = selectExperienceBullets(
        proposed_bullets=normalizeList(arguments["bullets"]),
        current_bullets=section.current_bullets,
        source_bullets=source_bullets,
        bullet_limit=section.bullet_limit,
        bullet_word_limit=section.bullet_word_limit,
        candidate_evidence=candidate_evidence,
    )
    return ExperienceSectionDraft(
        identifier=section.identifier,
        heading=section.heading,
        bullets=rewritten_bullets,
    )


def reviewCvDraft(
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
    arguments = callRequiredFunction(
        model=model,
        model_manager=model_manager,
        prompt=build_review_prompt(
            query=query,
            job_requirements_text=buildJobRequirementsText(job_requirements),
            candidate_evidence_text=buildCandidateEvidenceText(candidate_evidence),
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
        issues=normalizeList(arguments["issues"]),
        revision_targets=normalizeList(arguments["revision_targets"]),
        stop_reason=arguments["stop_reason"].strip(),
    )


def callRequiredFunction(
    model: Model,
    model_manager: ModelManager,
    prompt: str,
    tools,
    function_name: str,
):
    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)],
        tools=tools,
        tool_choice="required",
    )
    for part in response:
        if part.get("type") != "function":
            continue
        function = part["function"]
        if function["name"] != function_name:
            continue
        arguments = function["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return arguments
    raise ValueError(f"Expected tool call '{function_name}' was not returned")


def rankExperienceSections(
    template_structure,
    job_requirements: JobRequirementsArtifact,
    candidate_evidence: CandidateEvidenceArtifact,
    editable_section_limit: int,
) -> list[ExperienceSectionPlan]:
    keyword_text = buildJobRequirementsText(job_requirements) + " " + buildCandidateEvidenceText(candidate_evidence)
    scored_sections = []
    for section in template_structure.experience_sections:
        section_text = f"{section.heading} {section.role_title} {' '.join(section.current_bullets)}"
        scored_sections.append((len(overlapTokens(section_text, keyword_text)), section))
    scored_sections.sort(key=lambda item: item[0], reverse=True)
    selected_sections = [item[1] for item in scored_sections[:editable_section_limit]]
    return [
        ExperienceSectionPlan(
            identifier=section.identifier,
            heading=section.heading,
            priority_reason=f"Most relevant overlap score for this request: {len(overlapTokens(' '.join(section.current_bullets), keyword_text))}",
            bullet_goals=buildSectionGoals(section, job_requirements),
        )
        for section in selected_sections
    ]


def buildSectionGoals(section, job_requirements: JobRequirementsArtifact) -> list[str]:
    goals = [f"Surface truthful overlap with {keyword}" for keyword in (job_requirements.must_have_skills + job_requirements.responsibilities)[:3]]
    if goals:
        return goals
    return ["Keep the strongest commercially meaningful outcomes"]


def buildSupportedTechnologies(
    candidate_evidence: CandidateEvidenceArtifact,
    fallback_items: list[str],
) -> list[str]:
    evidence_text = buildCandidateEvidenceText(candidate_evidence)
    supported_items = filter_supported_items(
        items=candidate_evidence.core_skills,
        allowed_text=evidence_text,
        fallback_items=fallback_items,
        minimum_overlap=1,
    )
    return supported_items or fallback_items


def buildSupportedExpertise(
    candidate_evidence: CandidateEvidenceArtifact,
    fallback_items: list[str],
) -> list[str]:
    evidence_text = buildCandidateEvidenceText(candidate_evidence)
    supported_items = filter_supported_items(
        items=fallback_items,
        allowed_text=evidence_text,
        fallback_items=fallback_items,
        minimum_overlap=1,
    )
    return supported_items or fallback_items


def buildJobRequirementsText(job_requirements: JobRequirementsArtifact) -> str:
    return " ".join(
        [job_requirements.role_summary]
        + job_requirements.must_have_skills
        + job_requirements.responsibilities
        + job_requirements.ats_keywords
        + job_requirements.company_context,
    )


def buildCandidateEvidenceText(candidate_evidence: CandidateEvidenceArtifact) -> str:
    return " ".join(
        candidate_evidence.core_skills
        + candidate_evidence.relevant_experience
        + candidate_evidence.strongest_points
        + candidate_evidence.truth_constraints,
    )


def selectExperienceBullets(
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

        trimmed_bullet = trimToWordLimit(bullet, bullet_word_limit)
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
            trimToWordLimit(bullet, bullet_word_limit)
            for bullet in current_bullets[:bullet_limit]
        ]
    while len(cleaned_bullets) < min(bullet_limit, len(current_bullets)):
        cleaned_bullets.append(
            trimToWordLimit(current_bullets[len(cleaned_bullets)], bullet_word_limit),
        )
    return cleaned_bullets[:bullet_limit]


def buildChangeSummary(
    template_structure,
    cv_section_draft: CvSectionDraft,
) -> tuple[list[str], list[str]]:
    change_summary = []
    unchanged_summary = []

    if normalizeText(template_structure.current_summary) != normalizeText(cv_section_draft.summary):
        change_summary.append("updated the opening summary")
    else:
        unchanged_summary.append("kept the opening summary")

    if normalizeText(", ".join(template_structure.current_technologies)) != normalizeText(", ".join(cv_section_draft.technologies)):
        change_summary.append("updated the technologies list")
    else:
        unchanged_summary.append("kept the technologies list")

    if normalizeText(", ".join(template_structure.current_expertise)) != normalizeText(", ".join(cv_section_draft.expertise)):
        change_summary.append("updated the expertise list")
    else:
        unchanged_summary.append("kept the expertise list")

    rewritten_sections = []
    unchanged_sections = []
    for section in template_structure.experience_sections:
        drafted_section = find_drafted_section(cv_section_draft.experience_sections, section.identifier)
        if drafted_section is None:
            continue

        changed_count = countChangedBullets(section.current_bullets, drafted_section.bullets)
        if changed_count > 0:
            rewritten_sections.append(f"{section.heading} ({changed_count}/{len(section.current_bullets)} bullets)")
            continue

        unchanged_sections.append(section.heading)

    if rewritten_sections:
        change_summary.append("rewrote experience sections: " + ", ".join(rewritten_sections))

    if unchanged_sections:
        unchanged_summary.append("kept experience sections: " + ", ".join(unchanged_sections))

    return change_summary, unchanged_summary


def buildFinalResponse(
    output_path: str,
    pdf_output_path: str,
    pdf_page_count: int | None,
    change_summary: list[str],
    unchanged_summary: list[str],
    review: DraftReview,
) -> str:
    response_parts = [f"Saved a tailored CV draft to {output_path}."]

    if pdf_output_path:
        pdf_message = f"Also exported a PDF preview to {pdf_output_path}"
        if pdf_page_count is not None:
            page_suffix = "page" if pdf_page_count == 1 else "pages"
            pdf_message += f" ({pdf_page_count} {page_suffix} detected)"

        response_parts.append(pdf_message + ".")
    else:
        response_parts.append("PDF preview was not produced because the export could not be validated.")

    if change_summary:
        response_parts.append("Changes made: " + "; ".join(change_summary) + ".")

    if unchanged_summary:
        response_parts.append("Kept as-is: " + "; ".join(unchanged_summary) + ".")

    response_parts.append(f"Self-review: {review.reviewer_summary}")
    return " ".join(response_parts)


def normalizeList(values) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def tokenizeForOverlap(text: str) -> list[str]:
    return tokenize_for_overlap(text)


def overlapTokens(left_text: str, right_text: str) -> set[str]:
    return overlap_tokens(left_text, right_text)


def trimToWordLimit(text: str, word_limit: int) -> str:
    words = text.split()
    if len(words) <= word_limit:
        return text.strip()
    return " ".join(words[:word_limit]).rstrip(".") + "."


def limitList(items: list[str], item_limit: int) -> list[str]:
    return items[:item_limit]


def normalizeText(text: str) -> str:
    return normalize_text(text)


def countChangedBullets(current_bullets: list[str], drafted_bullets: list[str]) -> int:
    return sum(
        1
        for current_bullet, drafted_bullet in zip(current_bullets, drafted_bullets)
        if normalizeText(current_bullet) != normalizeText(drafted_bullet)
    )


def findSectionPlan(
    section_plans: list[ExperienceSectionPlan],
    identifier: str,
) -> ExperienceSectionPlan | None:
    for section_plan in section_plans:
        if section_plan.identifier != identifier:
            continue
        return section_plan
    return None


async def sendStatus(websocket: WebSocket, message: str):
    await websocket.send_json({"type": "status", "message": message})


async def sendWorkflowSummary(
    websocket: WebSocket,
    output_path: str,
    pdf_output_path: str,
    pdf_page_count: int | None,
    change_summary: list[str],
    unchanged_summary: list[str],
    review: DraftReview,
):
    summary_message = "Workflow summary: " + "; ".join(change_summary or ["no major changes"])
    logger.info(summary_message)
    await websocket.send_json({
        "type": "workflow_summary",
        "message": summary_message,
        "changed": change_summary,
        "unchanged": unchanged_summary,
        "output_path": output_path,
        "pdf_output_path": pdf_output_path,
        "pdf_page_count": pdf_page_count,
        "review": review.reviewer_summary,
    })
