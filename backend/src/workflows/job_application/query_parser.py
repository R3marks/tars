import re
from pathlib import PureWindowsPath

from src.workflows.job_application.models import JobApplicationRequest

BACKTICK_PATH_PATTERN = re.compile(r"`([^`]+)`")


def parse_job_application_request(query: str) -> JobApplicationRequest:
    request_type = "cv"
    if "cover letter" in query.lower():
        request_type = "cover_letter"

    candidate_paths = [path.strip() for path in BACKTICK_PATH_PATTERN.findall(query)]

    job_description_path = find_path(candidate_paths, ["job", "description"])
    experience_path = find_path(candidate_paths, ["experience"])
    template_path = find_path(candidate_paths, ["cv_template", ".html"])
    output_path = find_output_path(query, candidate_paths)

    return JobApplicationRequest(
        query=query,
        request_type=request_type,
        job_description_path=job_description_path,
        experience_path=experience_path,
        template_path=template_path,
        output_path=output_path,
    )


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


def find_output_path(query: str, candidate_paths: list[str]) -> str:
    lowered_query = query.lower()

    if "save to" in lowered_query:
        for candidate_path in reversed(candidate_paths):
            normalized_name = PureWindowsPath(candidate_path).name.lower()
            if normalized_name.endswith(".html"):
                return candidate_path

    for candidate_path in reversed(candidate_paths):
        normalized_name = PureWindowsPath(candidate_path).name.lower()
        if "generated" in normalized_name:
            return candidate_path

    return r"T:\Code\Apps\Tars\generated_cv.html"
