import re
from urllib.parse import urlparse

from src.workflows.job_application.models import ApplicationField, JobPageArtifact


def parse_job_page(markdown: str, source_url: str) -> JobPageArtifact:
    if not markdown:
        return JobPageArtifact(
            source_url=source_url,
            raw_page_markdown="",
            fetch_status="failed",
        )

    lines = normalize_markdown_lines(markdown)
    title = extract_role_title(lines)
    location = extract_location(lines)
    company_name = extract_company_name(source_url, lines)
    application_fields = extract_application_fields(lines)
    job_description_text = extract_job_description(lines)

    return JobPageArtifact(
        source_url=source_url,
        platform=detect_platform(source_url),
        role_title=title,
        company_name=company_name,
        location=location,
        job_description_text=job_description_text,
        application_fields=application_fields,
        raw_page_markdown=markdown,
        fetch_status="success",
    )


def normalize_markdown_lines(markdown: str) -> list[str]:
    lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = re.sub(r"\s+", " ", line)
        lines.append(line)

    return lines


def detect_platform(source_url: str) -> str:
    lowered_url = source_url.lower()
    if "greenhouse.io" in lowered_url:
        return "greenhouse"

    if "lever.co" in lowered_url:
        return "lever"

    return "generic"


def extract_role_title(lines: list[str]) -> str:
    for line in lines:
        if not line.startswith("#"):
            continue

        return line.lstrip("#").strip()

    return ""


def extract_location(lines: list[str]) -> str:
    title_found = False

    for line in lines:
        if line.startswith("#"):
            title_found = True
            continue

        if not title_found:
            continue

        if line.lower() == "apply":
            break

        if len(line) <= 120:
            return line

    return ""


def extract_company_name(source_url: str, lines: list[str]) -> str:
    for line in lines:
        match = re.search(r"Interested in building your career at (.+?)\?", line)
        if match is not None:
            return match.group(1).strip()

    parsed_url = urlparse(source_url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if "greenhouse.io" in parsed_url.netloc and path_parts:
        return format_slug_name(path_parts[0])

    if path_parts:
        return format_slug_name(path_parts[0])

    return ""


def extract_job_description(lines: list[str]) -> str:
    description_lines = []
    collect = False

    for line in lines:
        lowered_line = line.lower()
        if line == "Apply":
            collect = True
            continue

        if lowered_line.startswith("## apply for this job"):
            break

        if not collect:
            continue

        description_lines.append(line)

    return "\n".join(description_lines).strip()


def extract_application_fields(lines: list[str]) -> list[ApplicationField]:
    fields = []
    in_apply_section = False

    for line in lines:
        lowered_line = line.lower()
        if lowered_line.startswith("## apply for this job"):
            in_apply_section = True
            continue

        if not in_apply_section:
            continue

        if lowered_line.startswith("submit application") or lowered_line.startswith("powered by"):
            break

        if should_skip_field_line(lowered_line):
            continue

        required = line.endswith("*")
        label = line.rstrip("*").strip()
        if not label:
            continue

        fields.append(
            ApplicationField(
                identifier=f"field_{len(fields) + 1}",
                label=label,
                required=required,
                field_type=infer_field_type(label),
            ),
        )

    return fields


def should_skip_field_line(lowered_line: str) -> bool:
    skip_prefixes = [
        "*",
        "indicates a required field",
        "autofill with mygreenhouse",
        "attach",
        "dropbox",
        "google drive",
        "enter manually",
        "accepted file types",
    ]
    if lowered_line in {"* * *"}:
        return True

    for prefix in skip_prefixes:
        if lowered_line.startswith(prefix):
            return True

    return False


def infer_field_type(label: str) -> str:
    lowered_label = label.lower()
    if "resume" in lowered_label or "cv" in lowered_label:
        return "file_upload"

    if "cover letter" in lowered_label:
        return "file_upload"

    if lowered_label.startswith("do you"):
        return "boolean"

    if any(token in lowered_label for token in ["salary", "notice period"]):
        return "short_text"

    if "linkedin" in lowered_label or "email" in lowered_label or "phone" in lowered_label:
        return "short_text"

    if "why" in lowered_label or "describe" in lowered_label or "tell us" in lowered_label:
        return "long_text"

    if label.endswith("?"):
        return "question"

    return "text"


def format_slug_name(slug: str) -> str:
    cleaned_slug = slug.replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in cleaned_slug.split())
