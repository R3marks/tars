from pathlib import Path

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.workflows.job_application.models import ApplicationContext, SkillResult
from src.workflows.job_application.shared_context import call_required_function
from src.workflows.job_application.skill import build_application_answers_prompt

applicationAnswerTools = [
    {
        "type": "function",
        "function": {
            "name": "draft_application_answers",
            "description": "Draft answers for bespoke job application questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                                "review_note": {"type": "string"},
                            },
                            "required": ["question", "answer", "review_note"],
                        },
                    }
                },
                "required": ["answers"],
            },
        },
    }
]


def run_application_answers_package(
    application_context: ApplicationContext,
    worker_model: Model,
    model_manager: ModelManager,
) -> SkillResult:
    missing_inputs = []
    if not application_context.job_description_text:
        missing_inputs.append("job description")
    if not application_context.experience_text:
        missing_inputs.append("experience notes")
    if application_context.questions is None:
        missing_inputs.append("questions file")
    if application_context.job_requirements is None:
        missing_inputs.append("job requirements artifact")
    if application_context.candidate_evidence is None:
        missing_inputs.append("candidate evidence artifact")

    if missing_inputs:
        return SkillResult(
            artifact_type="application_answers",
            status="blocked",
            summary="Could not draft bespoke application answers because required inputs were missing.",
            missing_inputs=missing_inputs,
            review_notes=["Provide the missing answers inputs and rerun the workflow."],
        )

    arguments = call_required_function(
        model=worker_model,
        model_manager=model_manager,
        prompt=build_application_answers_prompt(
            query=application_context.request.query,
            job_requirements_text=build_job_requirements_text(application_context),
            candidate_evidence_text=build_candidate_evidence_text(application_context),
            motivation_text=build_motivation_text(application_context),
            research_text=build_research_text(application_context),
            questions=[item.question for item in application_context.questions.questions],
        ),
        tools=applicationAnswerTools,
        function_name="draft_application_answers",
    )

    output_target = application_context.request.output_targets["application_answers"]
    rendered_answers = render_answers_markdown(arguments["answers"])
    output_path = Path(output_target.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_answers, encoding="utf-8")

    review_notes = [answer["review_note"].strip() for answer in arguments["answers"] if answer["review_note"].strip()]
    status = "completed"
    if application_context.motivations is None:
        status = "needs_review"
        review_notes.append("No motivations file was provided, so motivation-heavy answers may need manual refinement.")

    return SkillResult(
        artifact_type="application_answers",
        status=status,
        output_paths=[str(output_path)],
        output_mode=output_target.mode,
        summary=f"Saved bespoke application answers to {output_path}.",
        review_notes=review_notes,
        change_summary=[f"answered {len(arguments['answers'])} application questions"],
    )


def render_answers_markdown(answers: list[dict]) -> str:
    lines = ["# Application Answers", ""]

    for answer in answers:
        lines.append(f"## {answer['question'].strip()}")
        lines.append("")
        lines.append(answer["answer"].strip())
        lines.append("")

        review_note = answer["review_note"].strip()
        if review_note:
            lines.append(f"Review note: {review_note}")
            lines.append("")

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
