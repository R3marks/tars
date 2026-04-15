import json
from pathlib import Path

from src.workflows.job_application.models import ApplicationContext, SkillResult


def run_form_field_answers_package(
    application_context: ApplicationContext,
) -> SkillResult:
    application_fields = application_context.application_research.application_fields
    if not application_fields:
        return SkillResult(
            artifact_type="form_field_answers",
            status="blocked",
            summary="No application fields were available to prepare copy-paste answers.",
            missing_inputs=["application fields"],
        )

    output_target = application_context.request.output_targets["form_field_answers"]
    rendered_content, unanswered_fields = render_form_field_answers(
        application_fields=application_fields,
        profile_defaults=application_context.profile_defaults,
    )

    output_path = Path(output_target.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_content, encoding="utf-8")

    review_notes = []
    status = "completed"
    if unanswered_fields:
        status = "needs_review"
        review_notes.append(
            "Some fields still need manual answers: " + ", ".join(unanswered_fields),
        )
    else:
        review_notes.append("Simple application fields were filled using the default stub profile.")

    return SkillResult(
        artifact_type="form_field_answers",
        status=status,
        output_paths=[str(output_path)],
        output_mode=output_target.mode,
        summary=f"Saved form-ready answers to {output_path}.",
        review_notes=review_notes,
        change_summary=[f"prepared answers for {len(application_fields)} application fields"],
    )


def render_form_field_answers(
    application_fields,
    profile_defaults: dict[str, str],
) -> tuple[str, list[str]]:
    lines = ["# Application Form Answers", ""]
    unanswered_fields = []

    for application_field in application_fields:
        if application_field.field_type == "file_upload":
            continue

        answer = infer_field_answer(application_field.label, profile_defaults)
        lines.append(f"## {application_field.label}")
        lines.append("")
        lines.append(answer)
        lines.append("")

        if answer.startswith("TODO:"):
            unanswered_fields.append(application_field.label)

    return "\n".join(lines).strip() + "\n", unanswered_fields


def infer_field_answer(
    label: str,
    profile_defaults: dict[str, str],
) -> str:
    lowered_label = label.lower()

    if "first name" in lowered_label:
        return profile_defaults.get("first_name", "TODO: confirm first name")

    if "last name" in lowered_label:
        return profile_defaults.get("last_name", "TODO: confirm last name")

    if "email" in lowered_label:
        return profile_defaults.get("email", "TODO: confirm email")

    if "phone" in lowered_label:
        return profile_defaults.get("phone", "TODO: confirm phone number")

    if "country" in lowered_label:
        return profile_defaults.get("country", "TODO: confirm country")

    if "linkedin" in lowered_label:
        return profile_defaults.get("linkedin", "TODO: confirm LinkedIn URL")

    if "notice period" in lowered_label:
        return profile_defaults.get("notice_period", "TODO: confirm current notice period")

    if "salary" in lowered_label:
        return profile_defaults.get("salary_expectations", "TODO: confirm salary expectations")

    if "right to work" in lowered_label or "visa sponsorship" in lowered_label:
        return profile_defaults.get("right_to_work_uk", "TODO: confirm UK right-to-work status")

    if label.endswith("?"):
        return "TODO: review and answer this question manually"

    return "TODO: review and answer this field manually"
