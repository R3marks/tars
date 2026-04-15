from pathlib import Path

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.workflows.job_application.models import (
    ApplicationContext,
    SkillResult,
)
from src.workflows.job_application.shared_context import call_required_function
from src.workflows.job_application.skill import build_cover_letter_prompt

coverLetterTools = [
    {
        "type": "function",
        "function": {
            "name": "draft_cover_letter",
            "description": "Draft a cover letter that can be rendered as text or HTML.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opening": {"type": "string"},
                    "body_paragraphs": {"type": "array", "items": {"type": "string"}},
                    "closing": {"type": "string"},
                    "personalization_summary": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "opening",
                    "body_paragraphs",
                    "closing",
                    "personalization_summary",
                ],
            },
        },
    }
]


def run_cover_letter_package(
    application_context: ApplicationContext,
    worker_model: Model,
    model_manager: ModelManager,
) -> SkillResult:
    missing_inputs = []
    if not application_context.job_description_text:
        missing_inputs.append("job description")
    if not application_context.experience_text:
        missing_inputs.append("experience notes")
    if application_context.job_requirements is None:
        missing_inputs.append("job requirements artifact")
    if application_context.candidate_evidence is None:
        missing_inputs.append("candidate evidence artifact")

    if missing_inputs:
        return SkillResult(
            artifact_type="cover_letter",
            status="blocked",
            summary="Could not draft a cover letter because required inputs were missing.",
            missing_inputs=missing_inputs,
            review_notes=["Provide the missing cover letter inputs and rerun the workflow."],
        )

    output_target = application_context.request.output_targets["cover_letter"]
    motivation_text = build_motivation_text(application_context)
    research_text = build_research_text(application_context)

    arguments = call_required_function(
        model=worker_model,
        model_manager=model_manager,
        prompt=build_cover_letter_prompt(
            query=application_context.request.query,
            job_requirements_text=build_job_requirements_text(application_context),
            candidate_evidence_text=build_candidate_evidence_text(application_context),
            motivation_text=motivation_text,
            research_text=research_text,
            cover_letter_template_text=application_context.cover_letter_template_text,
            output_mode=output_target.mode,
            company_name=application_context.application_research.company_name,
            company_address=application_context.application_research.company_address,
        ),
        tools=coverLetterTools,
        function_name="draft_cover_letter",
    )

    rendered_content = render_cover_letter(
        opening=arguments["opening"].strip(),
        body_paragraphs=[paragraph.strip() for paragraph in arguments["body_paragraphs"] if paragraph.strip()],
        closing=arguments["closing"].strip(),
        output_mode=output_target.mode,
        company_name=application_context.application_research.company_name,
        company_address=application_context.application_research.company_address,
    )

    output_path = Path(output_target.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_content, encoding="utf-8")

    review_notes = []
    status = "completed"
    if application_context.motivations is None:
        status = "needs_review"
        review_notes.append("No motivations file was provided, so the cover letter may need stronger personal motivation edits.")

    if not application_context.application_research.company_address and output_target.mode == "html_document":
        review_notes.append("No company address was available, so the address block was omitted.")

    return SkillResult(
        artifact_type="cover_letter",
        status=status,
        output_paths=[str(output_path)],
        output_mode=output_target.mode,
        summary=f"Saved a cover letter draft to {output_path}.",
        review_notes=review_notes,
        change_summary=arguments["personalization_summary"],
    )


def render_cover_letter(
    opening: str,
    body_paragraphs: list[str],
    closing: str,
    output_mode: str,
    company_name: str,
    company_address: str,
) -> str:
    if output_mode == "html_document":
        address_block = ""
        if company_name or company_address:
            address_lines = [line for line in [company_name, company_address] if line]
            address_block = "".join(f"<p>{line}</p>" for line in address_lines)

        paragraphs_html = "".join(f"<p>{paragraph}</p>" for paragraph in [opening] + body_paragraphs + [closing])
        return (
            "<html><body>"
            f"{address_block}"
            f"{paragraphs_html}"
            "</body></html>"
        )

    lines = []
    if company_name:
        lines.append(company_name)
    if company_address:
        lines.append(company_address)
    if lines:
        lines.append("")

    lines.append(opening)
    lines.append("")
    lines.extend(body_paragraphs)
    lines.append("")
    lines.append(closing)
    return "\n".join(lines).strip() + "\n"


def build_job_requirements_text(application_context: ApplicationContext) -> str:
    job_requirements = application_context.job_requirements
    return " ".join(
        [job_requirements.role_summary]
        + job_requirements.must_have_skills
        + job_requirements.responsibilities
        + job_requirements.ats_keywords
        + job_requirements.company_context,
    )


def build_candidate_evidence_text(application_context: ApplicationContext) -> str:
    candidate_evidence = application_context.candidate_evidence
    return " ".join(
        candidate_evidence.core_skills
        + candidate_evidence.relevant_experience
        + candidate_evidence.strongest_points
        + candidate_evidence.truth_constraints,
    )


def build_motivation_text(application_context: ApplicationContext) -> str:
    if application_context.motivations is None:
        return "No motivations file was provided."

    return " ".join(
        application_context.motivations.motivations
        + application_context.motivations.preferences
        + application_context.motivations.constraints,
    )


def build_research_text(application_context: ApplicationContext) -> str:
    application_research = application_context.application_research
    return " ".join(
        [application_research.company_name, application_research.company_address, application_research.application_url]
        + application_research.company_context
        + application_research.motivation_hooks,
    )
