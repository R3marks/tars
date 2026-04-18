import json
import re
from pathlib import Path
from dataclasses import replace

from src.agents.agent_utils import read_file
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.services.web_content_service import fetch_page_markdown
from src.workflows.job_application.experience_parser import parse_source_experience_sections
from src.workflows.job_application.job_page_parser import parse_job_page
from src.workflows.job_application.models import (
    ApplicationContext,
    ApplicationField,
    ApplicationResearchArtifact,
    ApplicationRequest,
    CandidateEvidenceArtifact,
    JobPageArtifact,
    JobRequirementsArtifact,
    MotivationArtifact,
    QuestionItem,
    QuestionsArtifact,
)
from src.workflows.job_application.profile_resolver import build_output_targets, resolve_application_request_defaults
from src.workflows.job_application.skill import (
    build_candidate_evidence_prompt,
    build_job_requirements_prompt,
)

jobRequirementsTools = [
    {
        "type": "function",
        "function": {
            "name": "save_job_requirements",
            "description": "Capture the most important job requirements for job application tailoring.",
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
            "description": "Capture truthful reusable evidence for job application tailoring.",
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


async def build_application_context(
    request: ApplicationRequest,
    planner_model: Model,
    worker_model: Model,
    model_manager: ModelManager,
) -> ApplicationContext:
    job_page = await fetch_job_page(request)
    resolved_request, profile_defaults = resolve_application_request_defaults(
        request=request,
        company_name="" if job_page is None else job_page.company_name,
        role_title="" if job_page is None else job_page.role_title,
    )
    resolved_request = enrich_requested_artifacts(resolved_request, job_page)

    job_description_text = safe_read_file(resolved_request.job_description_path)
    if not job_description_text and job_page is not None:
        job_description_text = job_page.job_description_text

    experience_text = safe_read_file(resolved_request.experience_path)
    cv_template_text = safe_read_file(resolved_request.cv_template_path)
    cover_letter_template_text = safe_read_file(resolved_request.cover_letter_template_path)
    motivations_text = safe_read_file(resolved_request.motivations_path)
    questions_text = safe_read_file(resolved_request.questions_path)

    job_requirements = None
    if job_description_text:
        job_requirements = extract_job_requirements(
            query=resolved_request.query,
            job_description_text=job_description_text,
            model=planner_model,
            model_manager=model_manager,
        )

    candidate_evidence = None
    if experience_text:
        candidate_evidence = extract_candidate_evidence(
            query=resolved_request.query,
            experience_text=experience_text,
            template_section_summaries=[],
            model=worker_model,
            model_manager=model_manager,
        )

    application_research = build_application_research(
        request=resolved_request,
        job_description_text=job_description_text,
        job_requirements=job_requirements,
        job_page=job_page,
    )
    resolved_request = refresh_default_output_targets(
        request=resolved_request,
        application_research=application_research,
    )
    motivations = parse_motivations(motivations_text, resolved_request.motivations_path)
    questions = parse_questions(questions_text, resolved_request.questions_path)

    return ApplicationContext(
        request=resolved_request,
        job_description_text=job_description_text,
        job_posting_markdown="" if job_page is None else job_page.raw_page_markdown,
        experience_text=experience_text,
        cv_template_text=cv_template_text,
        cover_letter_template_text=cover_letter_template_text,
        motivations_text=motivations_text,
        questions_text=questions_text,
        profile_defaults=profile_defaults,
        job_page=job_page,
        job_requirements=job_requirements,
        candidate_evidence=candidate_evidence,
        application_research=application_research,
        motivations=motivations,
        questions=questions,
    )


async def fetch_job_page(request: ApplicationRequest) -> JobPageArtifact | None:
    if not request.application_url:
        return None

    page_markdown = await fetch_page_markdown(request.application_url)
    if not page_markdown:
        return None

    return parse_job_page(page_markdown, request.application_url)


def enrich_requested_artifacts(
    request: ApplicationRequest,
    job_page: JobPageArtifact | None,
) -> ApplicationRequest:
    requested_artifacts = list(request.requested_artifacts)

    if job_page is not None:
        for application_field in job_page.application_fields:
            lowered_label = application_field.label.lower()

            if application_field.field_type == "file_upload" and any(token in lowered_label for token in ["resume", "cv"]):
                requested_artifacts.append("cv")
                continue

            if application_field.field_type == "file_upload" and "cover letter" in lowered_label:
                requested_artifacts.append("cover_letter")
                continue

            if application_field.field_type in {"short_text", "boolean", "text", "question", "long_text"}:
                requested_artifacts.append("form_field_answers")

    if request.questions_path:
        requested_artifacts.append("application_answers")

    deduplicated_artifacts = []
    seen_artifacts = set()

    for artifact_type in requested_artifacts:
        if artifact_type in seen_artifacts:
            continue

        seen_artifacts.add(artifact_type)
        deduplicated_artifacts.append(artifact_type)

    return replace(
        request,
        requested_artifacts=deduplicated_artifacts or ["cv"],
        company_name=request.company_name or ("" if job_page is None else job_page.company_name),
    )


def extract_job_requirements(
    query: str,
    job_description_text: str,
    model: Model,
    model_manager: ModelManager,
) -> JobRequirementsArtifact:
    arguments = call_required_function(
        model=model,
        model_manager=model_manager,
        prompt=build_job_requirements_prompt(query, job_description_text),
        tools=jobRequirementsTools,
        function_name="save_job_requirements",
    )
    return JobRequirementsArtifact(
        role_summary=arguments["role_summary"].strip(),
        must_have_skills=normalize_list(arguments["must_have_skills"]),
        responsibilities=normalize_list(arguments["responsibilities"]),
        ats_keywords=normalize_list(arguments["ats_keywords"]),
        company_context=normalize_list(arguments["company_context"]),
    )


def extract_candidate_evidence(
    query: str,
    experience_text: str,
    template_section_summaries: list[str],
    model: Model,
    model_manager: ModelManager,
) -> CandidateEvidenceArtifact:
    arguments = call_required_function(
        model=model,
        model_manager=model_manager,
        prompt=build_candidate_evidence_prompt(query, experience_text, template_section_summaries),
        tools=candidateEvidenceTools,
        function_name="save_candidate_evidence",
    )
    return CandidateEvidenceArtifact(
        core_skills=normalize_list(arguments["core_skills"]),
        relevant_experience=normalize_list(arguments["relevant_experience"]),
        strongest_points=normalize_list(arguments["strongest_points"]),
        truth_constraints=normalize_list(arguments["truth_constraints"]),
        source_experience_sections=parse_source_experience_sections(experience_text),
    )


def build_application_research(
    request: ApplicationRequest,
    job_description_text: str,
    job_requirements: JobRequirementsArtifact | None,
    job_page: JobPageArtifact | None,
) -> ApplicationResearchArtifact:
    company_name = request.company_name or infer_company_name(job_description_text, job_requirements)
    company_address = request.company_address or infer_company_address(job_description_text)
    company_context = [] if job_requirements is None else job_requirements.company_context

    return ApplicationResearchArtifact(
        company_name=company_name or ("" if job_page is None else job_page.company_name),
        company_address=company_address,
        application_url=request.application_url,
        role_title=infer_role_title(job_description_text) or ("" if job_page is None else job_page.role_title),
        location="" if job_page is None else job_page.location,
        platform="" if job_page is None else job_page.platform,
        company_context=company_context,
        motivation_hooks=extract_motivation_hooks(job_description_text),
        application_fields=[] if job_page is None else job_page.application_fields,
    )


def refresh_default_output_targets(
    request: ApplicationRequest,
    application_research: ApplicationResearchArtifact,
) -> ApplicationRequest:
    if request.has_explicit_output_targets:
        return request

    company_name = application_research.company_name or request.company_name
    role_title = application_research.role_title
    if not company_name and not role_title:
        return request

    output_root = infer_output_root(request.output_targets)
    rebuilt_targets = build_output_targets(
        explicit_targets={},
        output_root=output_root,
        company_name=company_name or "application",
        role_title=role_title or "package",
    )
    return replace(request, output_targets=rebuilt_targets)


def infer_output_root(output_targets: dict) -> str:
    for output_target in output_targets.values():
        output_path = Path(output_target.path)
        output_folder = output_path.parent
        output_root = output_folder.parent
        return str(output_root)

    return str(Path.cwd() / "generated" / "applications")


def parse_motivations(
    motivations_text: str,
    source_path: str,
) -> MotivationArtifact | None:
    if not motivations_text:
        return None

    motivations = []
    preferences = []
    constraints = []

    for raw_line in motivations_text.splitlines():
        line = clean_list_line(raw_line)
        if not line:
            continue

        lowered_line = line.lower()
        if lowered_line.startswith("prefer"):
            preferences.append(line)
            continue

        if any(token in lowered_line for token in ["avoid", "constraint", "cannot", "can't"]):
            constraints.append(line)
            continue

        motivations.append(line)

    return MotivationArtifact(
        motivations=motivations,
        preferences=preferences,
        constraints=constraints,
        source_path=source_path,
    )


def parse_questions(
    questions_text: str,
    source_path: str,
) -> QuestionsArtifact | None:
    if not questions_text:
        return None

    questions = []
    for raw_line in questions_text.splitlines():
        line = clean_list_line(raw_line)
        if not line:
            continue

        if not line.endswith("?"):
            continue

        questions.append(
            QuestionItem(
                identifier=f"question_{len(questions) + 1}",
                question=line,
            ),
        )

    if not questions:
        return None

    return QuestionsArtifact(
        questions=questions,
        source_path=source_path,
    )


def call_required_function(
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


def safe_read_file(path: str) -> str:
    if not path:
        return ""

    file_text = read_file(path)
    if file_text.startswith("Error"):
        return ""

    return file_text


def normalize_list(values) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def clean_list_line(line: str) -> str:
    cleaned_line = line.strip()
    if cleaned_line.startswith("-"):
        return cleaned_line[1:].strip()

    if cleaned_line.startswith("•"):
        return cleaned_line[1:].strip()

    return cleaned_line


def infer_company_name(
    job_description_text: str,
    job_requirements: JobRequirementsArtifact | None,
) -> str:
    if job_requirements is not None:
        for item in job_requirements.company_context:
            match = re.search(r"\b([A-Z][A-Za-z0-9&.\-]+)\b", item)
            if match is not None:
                return match.group(1)

    for line in job_description_text.splitlines():
        line = line.strip()
        if line.lower().startswith("introducing "):
            return line.split(" ", 1)[1].strip()

    return ""


def infer_company_address(job_description_text: str) -> str:
    for line in job_description_text.splitlines():
        stripped_line = line.strip()
        if not stripped_line.lower().startswith("location:"):
            continue

        return stripped_line.split(":", 1)[1].strip()

    return ""


def infer_role_title(job_description_text: str) -> str:
    for line in job_description_text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if stripped_line.lower() in {"job description", "the role", "job responsibilities"}:
            continue

        if len(stripped_line) > 120:
            continue

        return stripped_line

    return ""


def extract_motivation_hooks(job_description_text: str) -> list[str]:
    hooks = []
    for line in job_description_text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        lowered_line = stripped_line.lower()
        if not any(token in lowered_line for token in ["mission", "problem", "impact", "why", "decarbon", "startup"]):
            continue

        hooks.append(stripped_line)

    return hooks[:6]
