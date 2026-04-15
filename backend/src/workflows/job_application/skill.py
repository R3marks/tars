from src.workflows.job_application.models import SkillPackage


def get_job_application_skill_package() -> SkillPackage:
    return SkillPackage(
        name="job_application",
        editable_experience_section_limit=2,
        max_review_iterations=2,
    )


def build_job_requirements_prompt(query: str, job_description_text: str) -> str:
    return f"""
    Extract only the job requirements that matter for tailoring a one-page CV.

    User request:
    ---
    {query}
    ---

    Job description:
    ---
    {job_description_text}
    ---

    Rules:
    - Capture only the most relevant requirements.
    - Keep company context concise.
    - Focus on skills, responsibilities, and ATS language.
    - Do not invent missing information.
    """


def build_candidate_evidence_prompt(
    query: str,
    experience_text: str,
    template_section_summaries: list[str],
) -> str:
    return f"""
    Extract truthful candidate evidence for tailoring a CV.

    User request:
    ---
    {query}
    ---

    Experience notes:
    ---
    {experience_text}
    ---

    Current experience sections:
    - {template_section_summaries}

    Rules:
    - Treat the experience notes as the source of truth.
    - Prefer quantified achievements and commercially meaningful outcomes.
    - Keep the evidence concise and reusable.
    - Ignore unrelated legacy profile claims from the broader CV template.
    - Focus on the strongest evidence that could be reused across multiple job applications.
    - Do not infer technologies, domains, or achievements that are not clearly supported.
    """


def build_profile_draft_prompt(
    query: str,
    job_requirements_text: str,
    candidate_evidence_text: str,
    summary_word_limit: int,
    technology_item_limit: int,
    expertise_item_limit: int,
    current_summary: str,
    current_technologies: list[str],
    current_expertise: list[str],
    previous_summary: str = "",
    previous_technologies: list[str] | None = None,
    previous_expertise: list[str] | None = None,
    review_targets: list[str] | None = None,
) -> str:
    previous_technologies = previous_technologies or []
    previous_expertise = previous_expertise or []
    review_targets = review_targets or []

    return f"""
    Draft the profile sections of a one-page CV.

    User request:
    ---
    {query}
    ---

    Job requirements:
    - {job_requirements_text}

    Candidate evidence:
    - {candidate_evidence_text}

    Current profile sections:
    - Summary: {current_summary}
    - Technologies: {current_technologies}
    - Expertise: {current_expertise}

    Previous draft profile sections:
    - Summary: {previous_summary}
    - Technologies: {previous_technologies}
    - Expertise: {previous_expertise}

    Review targets:
    - {review_targets}

    Constraints:
    - Summary max words: {summary_word_limit}
    - Technology items max: {technology_item_limit}
    - Expertise items max: {expertise_item_limit}

    Rules:
    - Keep the wording truthful and specific.
    - Favor the strongest real overlap rather than generic job-language.
    - Do not introduce unsupported technologies or specialisms.
    - Only change the current wording when the new wording is clearly better.
    """


def build_experience_rewrite_prompt(
    query: str,
    job_requirements_text: str,
    candidate_evidence_text: str,
    section_heading: str,
    role_title: str,
    current_bullets: list[str],
    source_bullets: list[str],
    bullet_limit: int,
    bullet_word_limit: int,
    priority_reason: str,
    bullet_goals: list[str],
    previous_bullets: list[str] | None = None,
    review_targets: list[str] | None = None,
) -> str:
    previous_bullets = previous_bullets or []
    review_targets = review_targets or []

    return f"""
    Rewrite a single CV experience section.

    User request:
    ---
    {query}
    ---

    Job requirements:
    - {job_requirements_text}

    Candidate evidence:
    - {candidate_evidence_text}

    Experience section:
    - Heading: {section_heading}
    - Role title: {role_title}
    - Current bullets: {current_bullets}
    - Source bullets for this role: {source_bullets}

    Rewrite guidance:
    - Priority reason: {priority_reason}
    - Bullet goals: {bullet_goals}
    - Previous draft bullets: {previous_bullets}
    - Review targets: {review_targets}

    Constraints:
    - Keep exactly {bullet_limit} bullets.
    - Keep each bullet within {bullet_word_limit} words.

    Rules:
    - Treat the source bullets for this role as the factual ground truth.
    - Make each bullet feel stronger only when the evidence supports it.
    - Prefer action + outcome + context.
    - Keep the strongest quantified or commercially meaningful facts.
    - Do not move facts from another role into this section.
    - Do not overclaim.
    """


def build_review_prompt(
    query: str,
    job_requirements_text: str,
    candidate_evidence_text: str,
    draft_summary: str,
    draft_technologies: list[str],
    draft_expertise: list[str],
    rewritten_sections: list[str],
) -> str:
    return f"""
    Review whether this tailored CV draft is good enough to save.

    User request:
    ---
    {query}
    ---

    Job requirements:
    - {job_requirements_text}

    Candidate evidence:
    - {candidate_evidence_text}

    Draft under review:
    - Summary: {draft_summary}
    - Technologies: {draft_technologies}
    - Expertise: {draft_expertise}
    - Rewritten experience sections: {rewritten_sections}

    Rules:
    - Pass if the draft is concise, truthful, and clearly stronger than the starting point.
    - Pass when the draft surfaces the strongest truthful overlap, even if the candidate does not fully match every job-specific requirement.
    - Revise if the wording becomes generic, unsupported, or weaker than the original.
    - Revise if a bullet introduces a number, technology, or business outcome that is not traceable to the candidate evidence.
    - Revise if a rewritten experience section drops a stronger original fact.
    - Do not fail the draft purely because some job requirements are unsupported by the user's experience.
    - Keep the review practical and short.
    """
