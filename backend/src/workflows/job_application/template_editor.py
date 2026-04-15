import html
import re

from src.workflows.job_application.models import (
    CvSectionDraft,
    ExperienceSectionArtifact,
    ExperienceSectionDraft,
    TemplateStructureArtifact,
)

summaryStart = '<p class="c11"><span class="c0">'
summaryEnd = '</span></p></td></tr><tr class="c23"><td class="c51" colspan="6" rowspan="1"><p class="c7"><span class="c25"></span></p></td></tr><tr class="c71"><td class="c5" colspan="6" rowspan="1"><p class="c41"><span class="c6">KEY SKILLS</span></p></td></tr>'
technologiesStart = 'TECHNOLOGIES</span></p><ul class="c31 lst-kix_ai1acfkgj313-0 start"><li class="c41 c72 li-bullet-0"><span class="c27">'
technologiesEnd = '</span></li></ul><p class="c7"><span class="c27"></span></p><p class="c41"><span class="c17">EXPERTISE</span></p>'
expertiseStart = 'EXPERTISE</span></p><ul class="c31 lst-kix_zddxp2sj4j5z-0 start"><li class="c41 c72 li-bullet-0"><span class="c27">'
expertiseEnd = '</span></li></ul><p class="c7"><span class="c6"></span></p><p class="c41"><span class="c36 c63">PROFESSIONAL EXPERIENCE</span></p>'
experienceStartMarker = "PROFESSIONAL EXPERIENCE"
experienceEndMarker = "EDUCATION"

roleBulletPattern = re.compile(
    r'<li class="c3 li-bullet-[12]"><span class="[^"]+">(.*?)</span>(?:<span class="[^"]+">(.*?)</span>)?</li>',
    re.DOTALL,
)

experienceSectionPattern = re.compile(
    r'(?P<header><tr class="[^"]+">.*?<p class="[^"]+"><span class="[^"]+">(?P<heading>[^<]+)</span></p>\s*<p class="[^"]+"><span class="[^"]+">(?P<role_title>[^<]+)</span></p>.*?</tr>\s*)(?P<bullet_row><tr class="[^"]+"><td class="c51" colspan="6" rowspan="1"><ul class="[^"]+">(?P<bullet_html>.*?)</ul></td></tr>)',
    re.DOTALL,
)


def extract_template_structure(template_html: str) -> TemplateStructureArtifact:
    current_summary = extract_between(template_html, summaryStart, summaryEnd)
    current_technologies = split_csv_line(
        extract_between(template_html, technologiesStart, technologiesEnd),
    )
    current_expertise = split_csv_line(
        extract_between(template_html, expertiseStart, expertiseEnd),
    )
    experience_sections = extract_experience_sections(template_html)

    return TemplateStructureArtifact(
        section_order=[
            "summary",
            "key_skills",
            "professional_experience",
            "education",
            "extracurricular",
        ],
        current_summary=current_summary,
        current_technologies=current_technologies,
        current_expertise=current_expertise,
        experience_sections=experience_sections,
        summary_word_limit=max(len(current_summary.split()) + 6, 38),
        technology_item_limit=max(len(current_technologies), 8),
        expertise_item_limit=max(len(current_expertise), 6),
    )


def apply_cv_draft_to_template(
    template_html: str,
    cv_section_draft: CvSectionDraft,
    template_structure: TemplateStructureArtifact,
) -> str:
    updated_html = template_html
    summary_text = html.escape(cv_section_draft.summary.strip())
    technologies_text = html.escape(", ".join(cv_section_draft.technologies).strip())
    expertise_text = html.escape(", ".join(cv_section_draft.expertise).strip())

    updated_html = replace_between(updated_html, summaryStart, summaryEnd, summary_text)
    updated_html = replace_between(
        updated_html,
        technologiesStart,
        technologiesEnd,
        technologies_text,
    )
    updated_html = replace_between(
        updated_html,
        expertiseStart,
        expertiseEnd,
        expertise_text,
    )

    for drafted_section in cv_section_draft.experience_sections:
        template_section = find_template_section(
            template_structure.experience_sections,
            drafted_section.identifier,
        )
        if template_section is None:
            continue

        updated_html = updated_html.replace(
            template_section.original_bullet_html,
            build_role_list_html(drafted_section.bullets),
            1,
        )

    return updated_html


def extract_experience_sections(template_html: str) -> list[ExperienceSectionArtifact]:
    experience_block = extract_experience_block(template_html)
    experience_sections = []

    for index, match in enumerate(experienceSectionPattern.finditer(experience_block), start=1):
        heading = html.unescape(match.group("heading")).strip()
        role_title = html.unescape(match.group("role_title")).strip()
        bullet_html = match.group("bullet_html")
        current_bullets = extract_bullets_from_block(bullet_html)

        experience_sections.append(
            ExperienceSectionArtifact(
                identifier=f"experience_section_{index}",
                heading=heading,
                role_title=role_title,
                current_bullets=current_bullets,
                original_bullet_html=bullet_html,
                bullet_limit=max(len(current_bullets), 2),
                bullet_word_limit=34 if len(current_bullets) <= 2 else 30,
            ),
        )

    return experience_sections


def find_template_section(
    experience_sections: list[ExperienceSectionArtifact],
    identifier: str,
) -> ExperienceSectionArtifact | None:
    for experience_section in experience_sections:
        if experience_section.identifier != identifier:
            continue

        return experience_section

    return None


def find_drafted_section(
    drafted_sections: list[ExperienceSectionDraft],
    identifier: str,
) -> ExperienceSectionDraft | None:
    for drafted_section in drafted_sections:
        if drafted_section.identifier != identifier:
            continue

        return drafted_section

    return None


def extract_experience_block(template_html: str) -> str:
    start_index = template_html.find(experienceStartMarker)
    if start_index == -1:
        return ""

    end_index = template_html.find(experienceEndMarker, start_index)
    if end_index == -1:
        return template_html[start_index:]

    return template_html[start_index:end_index]


def extract_between(text: str, start_marker: str, end_marker: str) -> str:
    start_index = text.find(start_marker)
    if start_index == -1:
        return ""

    content_start = start_index + len(start_marker)
    end_index = text.find(end_marker, content_start)
    if end_index == -1:
        return ""

    return html.unescape(text[content_start:end_index]).strip()


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start_index = text.find(start_marker)
    if start_index == -1:
        return text

    content_start = start_index + len(start_marker)
    end_index = text.find(end_marker, content_start)
    if end_index == -1:
        return text

    return text[:content_start] + replacement + text[end_index:]


def split_csv_line(text: str) -> list[str]:
    items = []

    for part in text.split(","):
        normalized_part = part.strip()
        if not normalized_part:
            continue

        items.append(normalized_part)

    return items


def extract_bullets_from_block(bullet_block: str) -> list[str]:
    bullets = []

    for match in roleBulletPattern.findall(bullet_block):
        bullet_text = "".join(match).strip()
        if not bullet_text:
            continue

        bullets.append(html.unescape(bullet_text))

    return bullets


def build_role_list_html(bullets: list[str]) -> str:
    rendered_bullets = []

    for bullet in bullets:
        escaped_bullet = html.escape(bullet.strip())
        rendered_bullets.append(
            f'<li class="c3 li-bullet-1"><span class="c27">{escaped_bullet}</span></li>',
        )

    return "".join(rendered_bullets)
