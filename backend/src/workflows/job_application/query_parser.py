import re
from pathlib import PureWindowsPath

from src.workflows.job_application.models import ApplicationRequest, OutputTarget

BACKTICK_PATH_PATTERN = re.compile(r"`([^`]+)`")
URL_PATTERN = re.compile(r"https?://\S+")
KNOWN_COMPANY_ALIASES = {
    "kestrix": "Kestrix",
    "kstrix": "Kestrix",
}


def parse_job_application_request(query: str) -> ApplicationRequest:
    lowered_query = query.lower()
    candidate_paths = [path.strip() for path in BACKTICK_PATH_PATTERN.findall(query)]
    output_paths = find_save_paths(query, candidate_paths)
    source_paths = [candidate_path for candidate_path in candidate_paths if candidate_path not in output_paths]
    output_targets = build_output_targets(output_paths)

    return ApplicationRequest(
        query=query,
        requested_artifacts=find_requested_artifacts(lowered_query),
        has_explicit_output_targets=bool(output_targets),
        job_description_path=find_path(source_paths, ["job", "description"]),
        experience_path=find_path(source_paths, ["experience"]),
        cv_template_path=find_path(source_paths, ["cv_template", ".html"]),
        cover_letter_template_path=find_path(source_paths, ["cover", "template"]),
        motivations_path=find_path(source_paths, ["motivation"]),
        questions_path=find_path(source_paths, ["question"]),
        application_url=find_application_url(query),
        company_name=find_company_name(query),
        company_address="",
        output_targets=output_targets,
    )


def find_requested_artifacts(lowered_query: str) -> list[str]:
    requested_artifacts = []

    if any(token in lowered_query for token in ["cv", "resume"]):
        requested_artifacts.append("cv")

    if "cover letter" in lowered_query:
        requested_artifacts.append("cover_letter")

    if any(token in lowered_query for token in ["application question", "bespoke question", "answer question", "answers"]):
        requested_artifacts.append("application_answers")

    if requested_artifacts:
        return requested_artifacts

    if any(token in lowered_query for token in ["prepare an application", "prepare application", "apply for this job", "application for this job"]):
        return []

    return ["cv"]


def find_path(candidate_paths: list[str], keywords: list[str]) -> str:
    for candidate_path in candidate_paths:
        normalized_path = str(PureWindowsPath(candidate_path)).lower()
        if all(keyword in normalized_path for keyword in keywords):
            return candidate_path

    for candidate_path in candidate_paths:
        normalized_path = str(PureWindowsPath(candidate_path)).lower()
        if any(keyword in normalized_path for keyword in keywords):
            return candidate_path

    return ""


def build_output_targets(output_paths: list[str]) -> dict[str, OutputTarget]:
    if not output_paths:
        return {}

    output_targets = {}

    for artifact_type, output_path in find_output_paths_by_artifact(output_paths).items():
        output_targets[artifact_type] = OutputTarget(
            path=output_path,
            mode=infer_output_mode(output_path),
        )

    return output_targets


def find_save_paths(query: str, candidate_paths: list[str]) -> list[str]:
    lowered_query = query.lower()
    save_index = lowered_query.find("save to")
    if save_index == -1:
        return []

    save_section = query[save_index:]
    return [
        candidate_path
        for candidate_path in candidate_paths
        if candidate_path in save_section
    ]


def find_output_paths_by_artifact(output_paths: list[str]) -> dict[str, str]:
    explicit_paths = {}

    for candidate_path in reversed(output_paths):
        normalized_name = PureWindowsPath(candidate_path).name.lower()

        if normalized_name.endswith(".html") and "cv" in normalized_name and "cv" not in explicit_paths:
            explicit_paths["cv"] = candidate_path
            continue

        if normalized_name.endswith((".html", ".txt", ".md")) and "cover" in normalized_name and "cover_letter" not in explicit_paths:
            explicit_paths["cover_letter"] = candidate_path
            continue

        if normalized_name.endswith((".txt", ".md", ".json")) and any(token in normalized_name for token in ["question", "answer"]):
            explicit_paths["application_answers"] = candidate_path

    for candidate_path in reversed(output_paths):
        normalized_name = PureWindowsPath(candidate_path).name.lower()
        if normalized_name.endswith(".html") and "cv" not in explicit_paths:
            explicit_paths["cv"] = candidate_path

    return explicit_paths


def infer_output_mode(output_path: str) -> str:
    normalized_name = PureWindowsPath(output_path).name.lower()

    if normalized_name.endswith(".html"):
        return "html_document"

    if normalized_name.endswith(".pdf"):
        return "pdf_document"

    if normalized_name.endswith(".md"):
        return "markdown"

    return "plain_text"


def find_application_url(query: str) -> str:
    match = URL_PATTERN.search(query)
    if match is None:
        return ""

    return match.group(0)


def find_company_name(query: str) -> str:
    lowered_query = query.lower()

    for alias, company_name in KNOWN_COMPANY_ALIASES.items():
        if alias in lowered_query:
            return company_name

    company_match = re.search(r"apply to\s+([A-Z][A-Za-z0-9&.\- ]+)", query)
    if company_match is None:
        return ""

    return company_match.group(1).strip()
