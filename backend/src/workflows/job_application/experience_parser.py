import re

from src.workflows.job_application.models import (
    ExperienceSectionArtifact,
    SourceExperienceArtifact,
)

separatorPattern = re.compile(r"^\s*---\s*$", re.MULTILINE)
headingPattern = re.compile(
    r"^\s*(?P<role_title>[^|]+?)\s*\|\s*(?P<company>[^|]+?)\s*\|\s*(?P<date_range>.+?)\s*$",
)


def parse_source_experience_sections(experience_text: str) -> list[SourceExperienceArtifact]:
    source_sections = []

    for raw_block in separatorPattern.split(experience_text):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if not lines:
            continue

        heading_match = headingPattern.match(lines[0])
        if heading_match is None:
            continue

        bullets = [clean_bullet_line(line) for line in lines[1:] if is_bullet_line(line)]
        if not bullets:
            continue

        source_sections.append(
            SourceExperienceArtifact(
                identifier=f"source_experience_{len(source_sections) + 1}",
                company=heading_match.group("company").strip(),
                role_title=heading_match.group("role_title").strip(),
                date_range=heading_match.group("date_range").strip(),
                bullets=bullets,
            ),
        )

    return source_sections


def find_best_source_experience_section(
    template_section: ExperienceSectionArtifact,
    source_sections: list[SourceExperienceArtifact],
) -> SourceExperienceArtifact | None:
    best_section = None
    best_score = 0

    template_company = normalize_name(template_section.heading)
    template_role_title = normalize_name(template_section.role_title)
    template_bullet_text = " ".join(template_section.current_bullets)

    for source_section in source_sections:
        score = 0
        source_company = normalize_name(source_section.company)
        source_role_title = normalize_name(source_section.role_title)

        if template_company and template_company == source_company:
            score += 100
        elif template_company and (
            template_company in source_company or source_company in template_company
        ):
            score += 60

        score += len(overlap_tokens(template_role_title, source_role_title)) * 10
        score += min(
            len(overlap_tokens(template_bullet_text, " ".join(source_section.bullets))),
            5,
        )

        if score <= best_score:
            continue

        best_score = score
        best_section = source_section

    if best_score < 45:
        return None

    return best_section


def is_bullet_line(line: str) -> bool:
    stripped_line = line.lstrip()
    return stripped_line.startswith("-") or stripped_line.startswith("•")


def clean_bullet_line(line: str) -> str:
    stripped_line = line.strip()
    if stripped_line.startswith("-"):
        return stripped_line[1:].strip()

    if stripped_line.startswith("•"):
        return stripped_line[1:].strip()

    return stripped_line


def normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def overlap_tokens(left_text: str, right_text: str) -> set[str]:
    return set(tokenize_text(left_text)) & set(tokenize_text(right_text))


def tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#/]+", text.lower())
