import json
import re
from dataclasses import replace
from pathlib import Path

from src.workflows.job_application.models import ApplicationRequest, OutputTarget

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
CONFIG_ROOT = BACKEND_ROOT / "config"


def resolve_application_request_defaults(
    request: ApplicationRequest,
    company_name: str = "",
    role_title: str = "",
) -> tuple[ApplicationRequest, dict[str, str]]:
    profile_config = load_json_file(CONFIG_ROOT / "application_profile.json")
    stub_values = load_json_file(CONFIG_ROOT / "default_application_stub.json")

    experience_path = choose_path(
        explicit_path=request.experience_path,
        configured_path=profile_config.get("experience_path", ""),
        fallback_paths=[PROJECT_ROOT / "experience.txt"],
    )
    cv_template_path = choose_path(
        explicit_path=request.cv_template_path,
        configured_path=profile_config.get("cv_template_path", ""),
        fallback_paths=[PROJECT_ROOT / "cv_template.html"],
    )
    motivations_path = choose_path(
        explicit_path=request.motivations_path,
        configured_path=profile_config.get("motivations_path", ""),
        fallback_paths=[PROJECT_ROOT / "motivations.txt"],
    )
    cover_letter_template_path = choose_path(
        explicit_path=request.cover_letter_template_path,
        configured_path=profile_config.get("cover_letter_template_path", ""),
        fallback_paths=[PROJECT_ROOT / "cover_letter_template.txt"],
    )
    questions_path = choose_path(
        explicit_path=request.questions_path,
        configured_path=profile_config.get("questions_path", ""),
        fallback_paths=[],
    )

    output_root = profile_config.get(
        "output_root",
        str(PROJECT_ROOT / "generated" / "applications"),
    )
    output_targets = build_output_targets(
        explicit_targets=request.output_targets,
        output_root=output_root,
        company_name=company_name or request.company_name or "application",
        role_title=role_title or "package",
    )

    resolved_request = replace(
        request,
        experience_path=experience_path,
        cv_template_path=cv_template_path,
        motivations_path=motivations_path,
        cover_letter_template_path=cover_letter_template_path,
        questions_path=questions_path,
        output_targets=output_targets,
    )
    return resolved_request, normalize_stub_values(stub_values)


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def choose_path(
    explicit_path: str,
    configured_path: str,
    fallback_paths: list[Path],
) -> str:
    if explicit_path:
        return explicit_path

    if configured_path and Path(configured_path).exists():
        return configured_path

    for fallback_path in fallback_paths:
        if fallback_path.exists():
            return str(fallback_path)

    return ""


def build_output_targets(
    explicit_targets: dict[str, OutputTarget],
    output_root: str,
    company_name: str,
    role_title: str,
) -> dict[str, OutputTarget]:
    output_targets = dict(explicit_targets)
    output_folder = Path(output_root) / build_application_slug(company_name, role_title)

    defaults = {
        "cv": OutputTarget(str(output_folder / "generated_cv.html"), "html_document"),
        "cover_letter": OutputTarget(str(output_folder / "generated_cover_letter.txt"), "plain_text"),
        "application_answers": OutputTarget(str(output_folder / "generated_application_answers.md"), "markdown"),
        "form_field_answers": OutputTarget(str(output_folder / "application_form_answers.md"), "markdown"),
        "review_package": OutputTarget(str(output_folder / "review_package.md"), "markdown"),
        "job_posting": OutputTarget(str(output_folder / "job_posting.md"), "markdown"),
        "application_fields": OutputTarget(str(output_folder / "application_fields.json"), "json"),
    }

    for artifact_type, output_target in defaults.items():
        if artifact_type in output_targets:
            continue

        output_targets[artifact_type] = output_target

    return output_targets


def build_application_slug(company_name: str, role_title: str) -> str:
    company_slug = slugify_text(company_name)
    role_slug = slugify_text(role_title)

    if company_slug and role_slug:
        return f"{company_slug}-{role_slug}"

    if company_slug:
        return company_slug

    if role_slug:
        return role_slug

    return "application-package"


def slugify_text(text: str) -> str:
    normalized_text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return normalized_text


def normalize_stub_values(stub_values: dict) -> dict[str, str]:
    normalized_values = {}

    for key, value in stub_values.items():
        if value is None:
            continue

        normalized_values[key] = str(value)

    return normalized_values
