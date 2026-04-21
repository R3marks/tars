import asyncio
import hashlib
import json
import logging
import re
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import WebSocket

from src.app.result_payloads import JobActionPayload, JobSearchMatchPayload, JobSearchResultsPayload, SearchSpecPayload, ViewBlockPayload
from src.app.ws_events import send_job_search_results, send_phase_changed, send_progress_update, send_response_delta, send_run_completed
from src.infer.ModelManager import ModelManager
from src.message_structures.conversation import Conversation
from src.message_structures.message import Message
from src.orchestration.model_roles import OrchestrationModels
from src.services.web_content_service import fetch_page_markdown
from src.workflows.job_application.job_page_parser import parse_job_page
from src.workflows.job_search.job_state_service import JobStateService
from src.workflows.job_search.models import JobLead, JobSearchWorkflowResult, SearchSpec

logger = logging.getLogger("uvicorn.error")

ATS_DOMAINS = [
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
]

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"
HIMALAYAS_API_URL = "https://himalayas.app/jobs/api/search"

SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "apply",
    "can",
    "for",
    "from",
    "in",
    "job",
    "jobs",
    "looking",
    "of",
    "or",
    "role",
    "roles",
    "search",
    "senior",
    "staff",
    "junior",
    "lead",
    "principal",
    "the",
    "to",
    "with",
    "work",
    "remote",
    "hybrid",
    "show",
    "me",
    "please",
}

BOARD_TO_DOMAIN = {
    "greenhouse": "boards.greenhouse.io",
    "lever": "jobs.lever.co",
    "ashby": "jobs.ashbyhq.com",
}

TITLE_HINT_KEYWORDS = {
    "engineer",
    "engineering",
    "developer",
    "backend",
    "frontend",
    "fullstack",
    "platform",
    "python",
    "data",
    "sre",
    "devops",
    "architect",
    "software",
    "solutions",
    "implementation",
    "forward",
    "deployed",
    "lawyer",
    "legal",
    "counsel",
}

KNOWN_LOCATION_ALIASES = {
    "london": "London",
    "poland": "Poland",
    "warsaw": "Warsaw",
    "krakow": "Krakow",
    "munich": "Munich",
    "berlin": "Berlin",
    "germany": "Germany",
    "uk": "UK",
    "united kingdom": "United Kingdom",
    "remote": "Remote",
}

SEARCH_INTENT_EXPANSIONS = {
    "fdse": ["forward deployed", "solutions engineer", "implementation engineer", "customer engineer", "field engineer"],
    "forward deployed": ["fdse", "solutions engineer", "implementation engineer", "customer engineer", "field engineer"],
    "lawyer": ["legal counsel", "solicitor", "attorney", "legal"],
}

PROFILE_KEYWORD_CANDIDATES = [
    "python",
    "backend",
    "software",
    "engineer",
    "java",
    "react",
    "javascript",
    "llm",
    "ai",
    "data",
    "simulation",
]

PROFILE_EXPERIENCE_PATH = Path("personal/inputs/job_application/experience.txt")


async def run_job_search_workflow(
    query: str,
    websocket: WebSocket,
    run_id: str,
    session_id: int,
    conversation_history: Conversation,
    model_manager: ModelManager,
    orchestration_models: OrchestrationModels,
) -> JobSearchWorkflowResult:
    state_service = JobStateService()

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="parsing_job_search_brief",
        detail="Parsing the search brief into a normalized search spec.",
    )
    await send_progress_update(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        status="Parsing job search brief",
        details={"current_task": "parse_search_spec"},
    )

    search_spec = parse_search_spec(query)

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="discovering_ats_jobs",
        detail="Discovering ATS-board-first role pages.",
    )
    await send_progress_update(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        status="Discovering ATS roles",
        details={
            "current_task": "discover_ats_urls",
            "preferred_boards": search_spec.preferred_boards,
        },
    )

    discovered_urls = await discover_job_urls(search_spec)
    discovered_jobs = await normalize_discovered_jobs(search_spec, discovered_urls)
    if not discovered_jobs:
        await send_progress_update(
            websocket = websocket,
            run_id = run_id,
            session_id = session_id,
            status = "Falling back to public job feeds",
            details = {
                "current_task": "discover_public_job_feeds",
            },
        )
        discovered_jobs = await discover_fallback_jobs(search_spec)

    catalog_matches = build_catalog_matches(search_spec, state_service)

    merged_jobs = merge_job_leads([*catalog_matches, *discovered_jobs])
    scored_jobs = score_job_leads(search_spec, merged_jobs)
    scored_jobs = prioritize_hard_requirement_matches(search_spec, scored_jobs)
    persisted_jobs = persist_job_leads(state_service, scored_jobs)

    job_matches = build_match_payloads(persisted_jobs)
    recommendation_summary = build_recommendation_summary(search_spec, persisted_jobs)
    job_search_results = JobSearchResultsPayload(
        query_summary=search_spec.summary or query,
        search_spec=SearchSpecPayload(
            query=search_spec.query,
            summary=search_spec.summary,
            keywords=search_spec.keywords,
            location=search_spec.location,
            remote_preference=search_spec.remote_preference,
            seniority=search_spec.seniority,
            company_names=search_spec.company_names,
            exact_urls=search_spec.exact_urls,
            preferred_boards=search_spec.preferred_boards,
            limit=search_spec.limit,
        ),
        matches=job_matches,
        total_matches=len(job_matches),
        recommendation_summary=recommendation_summary,
        actions=build_result_actions(job_matches),
        view_blocks=build_result_view_blocks(job_matches, search_spec, recommendation_summary),
    )

    await send_phase_changed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        phase="publishing_job_search_results",
        detail="Persisting results and emitting selectable job cards.",
    )
    await send_job_search_results(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        job_search_results=job_search_results,
    )

    final_response = build_final_response(search_spec, persisted_jobs, recommendation_summary)
    conversation_history.append_message(Message(role="assistant", content=final_response))
    await send_response_delta(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
        text=final_response,
    )
    await send_run_completed(
        websocket=websocket,
        run_id=run_id,
        session_id=session_id,
    )

    output_paths = []
    for job_lead in persisted_jobs:
        output_paths.extend(job_lead.output_paths)

    return JobSearchWorkflowResult(
        status="completed" if persisted_jobs else "partial",
        final_response=final_response,
        search_spec=search_spec,
        matches=persisted_jobs,
        output_paths=output_paths,
        recommendation_summary=recommendation_summary,
    )


def parse_search_spec(query: str) -> SearchSpec:
    lowered_query = query.lower()
    location = infer_location(query)
    keywords = remove_location_keywords(infer_keywords(query), location)
    remote_preference = infer_remote_preference(lowered_query)
    seniority = infer_seniority(lowered_query)
    company_names = infer_company_names(query)
    exact_urls = extract_urls(query)
    preferred_boards = infer_preferred_boards(lowered_query)
    summary = summarize_query(query, keywords, location, remote_preference, seniority)

    search_spec = SearchSpec(
        query=query,
        summary=summary,
        keywords=keywords,
        location=location,
        remote_preference=remote_preference,
        seniority=seniority,
        company_names=company_names,
        exact_urls=exact_urls,
        preferred_boards=preferred_boards,
        limit=10,
    )

    return apply_profile_defaults(search_spec)


def infer_keywords(query: str) -> list[str]:
    candidates = []
    for raw_token in re.split(r"[\s,;/|]+", query):
        token = raw_token.strip(" .:;()[]{}\"'").lower()
        if len(token) < 3:
            continue
        if token in SEARCH_STOPWORDS:
            continue
        if token.isdigit():
            continue
        candidates.append(token)

    lowered_query = query.lower()
    for trigger, expanded_terms in SEARCH_INTENT_EXPANSIONS.items():
        if trigger not in lowered_query:
            continue

        for expanded_term in expanded_terms:
            candidates.extend(expanded_term.split())

    seen = set()
    keywords = []
    for token in candidates:
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)

    return keywords[:12]


def remove_location_keywords(keywords: list[str], location: str) -> list[str]:
    if not location:
        return keywords

    location_tokens = {token.lower() for token in re.split(r"[\s,;/|]+", location) if token.strip()}
    filtered_keywords = [keyword for keyword in keywords if keyword.lower() not in location_tokens]
    return filtered_keywords


def infer_location(query: str) -> str:
    location_patterns = [
        r"\bin\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+)*)",
        r"\bbased in\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+)*)",
        r"\bfrom\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+)*)",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, query)
        if match is not None:
            raw_location = match.group(1).strip().rstrip(".,")
            cleaned_location = clean_location(raw_location)
            if cleaned_location:
                return cleaned_location

    lowered_query = query.lower()
    for alias, location in KNOWN_LOCATION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered_query):
            return location

    return ""


def clean_location(raw_location: str) -> str:
    location = re.sub(r"\b(please|thanks|thank you|with|for|and|or)\b.*$", "", raw_location, flags=re.IGNORECASE).strip()
    if not location:
        return ""

    lowered_location = location.lower()
    return KNOWN_LOCATION_ALIASES.get(lowered_location, location)


def infer_remote_preference(lowered_query: str) -> str:
    if "fully remote" in lowered_query or "remote only" in lowered_query:
        return "remote_only"

    if "remote" in lowered_query:
        return "remote"

    if "hybrid" in lowered_query:
        return "hybrid"

    return ""


def infer_seniority(lowered_query: str) -> str:
    for seniority in ["principal", "staff", "senior", "lead", "junior", "mid", "entry"]:
        if seniority in lowered_query:
            return seniority

    return ""


def infer_company_names(query: str) -> list[str]:
    company_names = []
    for pattern in [r"\bat\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+)*)"]:
        match = re.search(pattern, query)
        if match is not None:
            company_names.append(match.group(1).strip())

    return deduplicate_strings(company_names)


def extract_urls(query: str) -> list[str]:
    return deduplicate_strings(re.findall(r"https?://[^\s<>)\]]+", query))


def infer_preferred_boards(lowered_query: str) -> list[str]:
    boards = []
    for board_name, domain in BOARD_TO_DOMAIN.items():
        if board_name in lowered_query or domain in lowered_query:
            boards.append(board_name)

    if boards:
        return deduplicate_strings(boards)

    return ["greenhouse", "lever", "ashby"]


def summarize_query(
    query: str,
    keywords: list[str],
    location: str,
    remote_preference: str,
    seniority: str,
) -> str:
    parts = []
    if seniority:
        parts.append(f"{seniority} ")

    parts.append("job search")

    if keywords:
        parts.append("for " + ", ".join(keywords[:4]))

    if location:
        parts.append(f"in {location}")

    if remote_preference:
        parts.append(f"({remote_preference.replace('_', ' ')})")

    summary = " ".join(parts).strip()
    if summary:
        return summary[0].upper() + summary[1:]

    return query.strip()


def apply_profile_defaults(search_spec: SearchSpec) -> SearchSpec:
    if search_spec.keywords:
        return search_spec

    profile_keywords = infer_profile_keywords()
    summary = summarize_query(
        query = search_spec.query,
        keywords = profile_keywords,
        location = search_spec.location,
        remote_preference = search_spec.remote_preference,
        seniority = search_spec.seniority,
    )

    return replace(
        search_spec,
        keywords = profile_keywords,
        summary = summary,
    )


def infer_profile_keywords() -> list[str]:
    if not PROFILE_EXPERIENCE_PATH.exists():
        return ["python", "backend", "software", "engineer"]

    experience_text = PROFILE_EXPERIENCE_PATH.read_text(encoding = "utf-8").lower()
    profile_keywords = []
    for candidate in PROFILE_KEYWORD_CANDIDATES:
        if candidate not in experience_text:
            continue

        profile_keywords.append(candidate)

    if profile_keywords:
        return profile_keywords[:6]

    return ["python", "backend", "software", "engineer"]


async def discover_job_urls(search_spec: SearchSpec) -> list[str]:
    urls = list(search_spec.exact_urls)
    search_queries = build_discovery_queries(search_spec)

    discovered_results = await asyncio.gather(
        *[asyncio.to_thread(search_duckduckgo, query) for query in search_queries],
        return_exceptions=True,
    )

    for result in discovered_results:
        if isinstance(result, Exception):
            continue

        urls.extend(result)

    if not urls and search_spec.company_names:
        urls.extend(guess_ats_urls(search_spec.company_names, search_spec.preferred_boards))

    return filter_ats_urls(deduplicate_strings(urls))


def build_discovery_queries(search_spec: SearchSpec) -> list[str]:
    query_terms = " ".join(search_spec.keywords[:6])
    if search_spec.location:
        query_terms = f"{query_terms} {search_spec.location}".strip()

    search_queries = []
    for board_name in search_spec.preferred_boards:
        domain = BOARD_TO_DOMAIN.get(board_name)
        if not domain:
            continue

        board_query = f"{query_terms} site:{domain}"
        search_queries.append(board_query.strip())

    return search_queries


def search_duckduckgo(query: str) -> list[str]:
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        response = requests.get(
            search_url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
            },
        )
        response.raise_for_status()
    except Exception:
        logger.exception("ATS discovery search failed for query %s", query)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    for anchor in soup.select("a.result__a"):
        href = anchor.get("href", "")
        if href:
            urls.append(normalize_search_result_url(href))

    return urls


def normalize_search_result_url(url: str) -> str:
    if not url:
        return ""

    absolute_url = urljoin("https://duckduckgo.com", url)
    parsed_url = urlparse(absolute_url)
    query_values = parse_qs(parsed_url.query)
    uddg_values = query_values.get("uddg", [])
    if uddg_values:
        return unquote(uddg_values[0])

    return absolute_url


def guess_ats_urls(company_names: list[str], preferred_boards: list[str]) -> list[str]:
    urls = []
    for company_name in company_names:
        slug = slugify(company_name)
        if not slug:
            continue

        for board_name in preferred_boards:
            domain = BOARD_TO_DOMAIN.get(board_name)
            if not domain:
                continue

            if board_name == "greenhouse":
                urls.append(f"https://boards.greenhouse.io/{slug}")
                urls.append(f"https://boards.greenhouse.io/{slug}/jobs")
                continue

            if board_name == "lever":
                urls.append(f"https://jobs.lever.co/{slug}")
                continue

            if board_name == "ashby":
                urls.append(f"https://jobs.ashbyhq.com/{slug}")

    return urls


def filter_ats_urls(urls: list[str]) -> list[str]:
    filtered_urls = []
    for url in urls:
        url = normalize_search_result_url(url)
        lowered_url = url.lower()
        if any(domain in lowered_url for domain in ATS_DOMAINS):
            filtered_urls.append(url)

    return deduplicate_strings(filtered_urls)


async def normalize_discovered_jobs(search_spec: SearchSpec, urls: list[str]) -> list[JobLead]:
    discovered_jobs = []

    for url in urls[: max(search_spec.limit, 5)]:
        job_lead = await build_job_lead_from_url(search_spec, url)
        if job_lead is not None:
            discovered_jobs.append(job_lead)

    return discovered_jobs


async def discover_fallback_jobs(search_spec: SearchSpec) -> list[JobLead]:
    fallback_results = await asyncio.gather(
        asyncio.to_thread(fetch_remotive_jobs, search_spec),
        asyncio.to_thread(fetch_arbeitnow_jobs, search_spec),
        asyncio.to_thread(fetch_himalayas_jobs, search_spec),
        return_exceptions = True,
    )

    discovered_jobs = []
    for result in fallback_results:
        if isinstance(result, Exception):
            logger.exception("Public job feed fallback failed.")
            continue

        discovered_jobs.extend(result)

    return discovered_jobs[: max(search_spec.limit * 2, 10)]


def fetch_remotive_jobs(search_spec: SearchSpec) -> list[JobLead]:
    discovered_jobs = []
    for search_query in build_fallback_search_queries(search_spec):
        try:
            response = requests.get(
                REMOTIVE_API_URL,
                params = {"search": search_query},
                timeout = 20,
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            logger.exception("Remotive fallback search failed for query %s", search_query)
            continue

        for raw_job in payload.get("jobs", [])[:30]:
            title = str(raw_job.get("title", "")).strip()
            company = str(raw_job.get("company_name", "")).strip()
            source_url = str(raw_job.get("url", "")).strip()
            location = normalize_job_location(
                str(raw_job.get("candidate_required_location", "")).strip(),
                search_spec,
            )
            description = strip_html(str(raw_job.get("description", "")))
            if not fallback_job_matches_search_spec(
                search_spec = search_spec,
                title = title,
                company = company,
                location = location,
                description = description,
            ):
                continue

            discovered_jobs.append(
                JobLead(
                    job_slug = slugify_job_lead(company, title, location, source_url),
                    title = title or "Unknown role",
                    company = company or "Unknown company",
                    location = location,
                    source = "remotive",
                    source_url = source_url,
                    summary = summarize_posting(description),
                    state = "discovered",
                    job_posting_text = description,
                    board = "remotive",
                    search_keywords = search_spec.keywords,
                    result_origin = "new",
                ),
            )

    return merge_job_leads(discovered_jobs)


def fetch_arbeitnow_jobs(search_spec: SearchSpec) -> list[JobLead]:
    try:
        response = requests.get(
            ARBEITNOW_API_URL,
            timeout = 20,
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
            },
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logger.exception("Arbeitnow fallback search failed for query %s", search_spec.query)
        return []

    discovered_jobs = []
    for raw_job in payload.get("data", [])[:60]:
        title = str(raw_job.get("title", "")).strip()
        company = str(raw_job.get("company_name", "")).strip()
        source_url = str(raw_job.get("url", "")).strip()
        location = normalize_job_location(
            str(raw_job.get("location", "")).strip(),
            search_spec,
        )
        description = strip_html(str(raw_job.get("description", "")))
        if not fallback_job_matches_search_spec(
            search_spec = search_spec,
            title = title,
            company = company,
            location = location,
            description = description,
        ):
            continue

        discovered_jobs.append(
            JobLead(
                job_slug = slugify_job_lead(company, title, location, source_url),
                title = title or "Unknown role",
                company = company or "Unknown company",
                location = location,
                source = "arbeitnow",
                source_url = source_url,
                summary = summarize_posting(description),
                state = "discovered",
                job_posting_text = description,
                board = "arbeitnow",
                search_keywords = search_spec.keywords,
                result_origin = "new",
            ),
        )

    return discovered_jobs


def fetch_himalayas_jobs(search_spec: SearchSpec) -> list[JobLead]:
    discovered_jobs = []
    for search_query in build_fallback_search_queries(search_spec):
        try:
            response = requests.get(
                HIMALAYAS_API_URL,
                params = {"q": search_query, "sort": "recent"},
                timeout = 20,
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            logger.exception("Himalayas fallback search failed for query %s", search_query)
            continue

        for raw_job in payload.get("jobs", [])[:20]:
            title = str(raw_job.get("title", "")).strip()
            company = str(raw_job.get("companyName", "")).strip()
            source_url = str(raw_job.get("applicationLink", "") or raw_job.get("url", "")).strip()
            location = format_himalayas_location(raw_job, search_spec)
            description = strip_html(str(raw_job.get("description", "") or raw_job.get("excerpt", "")))
            if not fallback_job_matches_search_spec(
                search_spec = search_spec,
                title = title,
                company = company,
                location = location,
                description = description,
            ):
                continue

            discovered_jobs.append(
                JobLead(
                    job_slug = slugify_job_lead(company, title, location, source_url),
                    title = title or "Unknown role",
                    company = company or "Unknown company",
                    location = location,
                    source = "himalayas",
                    source_url = source_url,
                    summary = summarize_posting(description),
                    state = "discovered",
                    job_posting_text = description,
                    board = "himalayas",
                    search_keywords = search_spec.keywords,
                    result_origin = "new",
                ),
            )

    return merge_job_leads(discovered_jobs)


def build_fallback_search_queries(search_spec: SearchSpec) -> list[str]:
    title_queries = []
    lowered_keywords = [keyword.lower() for keyword in search_spec.keywords]

    if "fdse" in lowered_keywords or "forward" in lowered_keywords or "deployed" in lowered_keywords:
        title_queries.extend(
            [
                "forward deployed software engineer",
                "solutions engineer",
                "implementation engineer",
                "customer engineer",
                "field engineer",
            ],
        )
    elif "lawyer" in lowered_keywords or "legal" in lowered_keywords:
        title_queries.extend(["lawyer", "legal counsel", "solicitor"])
    else:
        title_keywords = [keyword for keyword in search_spec.keywords if keyword.lower() in TITLE_HINT_KEYWORDS]
        if title_keywords:
            title_queries.append(" ".join(title_keywords[:4]))

    if search_spec.keywords:
        title_queries.append(" ".join(search_spec.keywords[:5]))

    title_queries.append(search_spec.query)
    return deduplicate_strings(title_queries)[:6]


def format_himalayas_location(raw_job: dict, search_spec: SearchSpec) -> str:
    location_restrictions = raw_job.get("locationRestrictions", [])
    if location_restrictions:
        location_names = []
        for location in location_restrictions:
            if not isinstance(location, dict):
                continue

            location_name = str(location.get("name", "")).strip()
            if location_name:
                location_names.append(location_name)

        if location_names:
            return ", ".join(location_names)

    return "Remote worldwide"


def fallback_job_matches_search_spec(
    search_spec: SearchSpec,
    title: str,
    company: str,
    location: str,
    description: str,
) -> bool:
    search_text = " ".join([title, company, location, description]).lower()
    title_text = title.lower()
    location_text = location.lower()
    description_text = description.lower()
    keyword_hits = 0

    for keyword in search_spec.keywords:
        if keyword.lower() in search_text:
            keyword_hits += 1

    title_keywords = [keyword for keyword in search_spec.keywords if keyword.lower() in TITLE_HINT_KEYWORDS]
    if title_keywords:
        title_keyword_hits = 0
        for keyword in title_keywords:
            if keyword.lower() in title_text:
                title_keyword_hits += 1

        if title_keyword_hits == 0:
            return False

    if search_spec.company_names:
        company_hit = any(company_name.lower() in search_text for company_name in search_spec.company_names)
        if not company_hit:
            return False

    if len(search_spec.keywords) >= 3 and keyword_hits < 2:
        return False

    return keyword_hits >= 1


def normalize_job_location(location: str, search_spec: SearchSpec) -> str:
    if location:
        return location

    if search_spec.remote_preference:
        return search_spec.remote_preference.replace("_", " ")

    return search_spec.location


def strip_html(value: str) -> str:
    if not value:
        return ""

    return BeautifulSoup(value, "html.parser").get_text(separator = " ", strip = True)


async def build_job_lead_from_url(search_spec: SearchSpec, source_url: str) -> JobLead | None:
    page_markdown = await fetch_page_markdown(source_url)
    if not page_markdown:
        return None

    job_page = parse_job_page(page_markdown, source_url)
    if not job_page.raw_page_markdown:
        return None

    title = job_page.role_title or infer_title_from_url(source_url)
    company = job_page.company_name or infer_company_from_url(source_url)
    location = job_page.location or search_spec.location
    summary = summarize_posting(page_markdown)
    source = job_page.platform or infer_source_from_url(source_url)

    return JobLead(
        job_slug=slugify_job_lead(company, title, location, source_url),
        title=title or "Unknown role",
        company=company or "Unknown company",
        location=location,
        source=source,
        source_url=source_url,
        summary=summary,
        state="discovered",
        job_posting_text=page_markdown,
        board=source,
        search_keywords=search_spec.keywords,
        result_origin="new",
    )


def build_catalog_matches(search_spec: SearchSpec, state_service: JobStateService) -> list[JobLead]:
    catalog_records = state_service.find_matching_records(search_spec)
    catalog_jobs = []

    for record in catalog_records:
        catalog_jobs.append(
            JobLead(
                job_slug=record.get("job_slug", ""),
                title=record.get("title", ""),
                company=record.get("company", ""),
                location=record.get("location", ""),
                source=record.get("source", ""),
                source_url=record.get("source_url", ""),
                summary=record.get("summary", ""),
                state=record.get("state", "saved"),
                score=float(record.get("score", 0.0)),
                suitability_label=record.get("suitability_label", ""),
                suitability_rationale=record.get("suitability_rationale", ""),
                job_posting_text=record.get("job_posting_text", ""),
                board=record.get("board", ""),
                search_keywords=search_spec.keywords,
                output_paths=record.get("output_paths", []),
                result_origin=record.get("result_origin", "catalog") or "catalog",
            ),
        )

    return catalog_jobs


def merge_job_leads(job_leads: list[JobLead]) -> list[JobLead]:
    merged = {}
    for job_lead in job_leads:
        if not job_lead.job_slug:
            continue

        existing = merged.get(job_lead.job_slug)
        if existing is None or job_lead.score > existing.score:
            merged[job_lead.job_slug] = job_lead

    return list(merged.values())


def score_job_leads(search_spec: SearchSpec, job_leads: list[JobLead]) -> list[JobLead]:
    scored_jobs = []
    for job_lead in job_leads:
        score, label, rationale = score_job_lead(search_spec, job_lead)
        scored_jobs.append(
            replace(
                job_lead,
                score=score,
                suitability_label=label,
                suitability_rationale=rationale,
            ),
        )

    scored_jobs.sort(key=lambda job: job.score, reverse=True)
    return scored_jobs[: search_spec.limit]


def filter_job_leads_by_hard_requirements(search_spec: SearchSpec, job_leads: list[JobLead]) -> list[JobLead]:
    filtered_jobs = []
    for job_lead in job_leads:
        if not job_satisfies_hard_search_spec(search_spec, job_lead):
            continue

        filtered_jobs.append(job_lead)

    return filtered_jobs


def prioritize_hard_requirement_matches(search_spec: SearchSpec, job_leads: list[JobLead]) -> list[JobLead]:
    hard_matches = filter_job_leads_by_hard_requirements(search_spec, job_leads)
    if hard_matches:
        return hard_matches[: search_spec.limit]

    return job_leads[: search_spec.limit]


def job_satisfies_hard_search_spec(search_spec: SearchSpec, job_lead: JobLead) -> bool:
    title_text = job_lead.title.lower()
    location_text = job_lead.location.lower()
    posting_text = " ".join([job_lead.summary, job_lead.job_posting_text]).lower()

    title_keywords = [keyword for keyword in search_spec.keywords if keyword.lower() in TITLE_HINT_KEYWORDS]
    if title_keywords:
        title_matches = any(keyword.lower() in title_text for keyword in title_keywords)
        if not title_matches:
            return False

    if search_spec.location:
        normalized_location = search_spec.location.lower()
        location_matches = location_satisfies_search(location_text, search_spec.location)
        remote_matches = search_spec.remote_preference and ("remote" in location_text or "remote" in posting_text)
        if not location_matches and not remote_matches:
            return False

    return True


def score_job_lead(search_spec: SearchSpec, job_lead: JobLead) -> tuple[float, str, str]:
    title_text = job_lead.title.lower()
    location_text = job_lead.location.lower()
    search_text = " ".join(
        [
            job_lead.title,
            job_lead.company,
            job_lead.location,
            job_lead.summary,
            job_lead.source,
            job_lead.job_posting_text,
        ],
    ).lower()

    score = 0.0
    matched_keywords = []
    matched_location = False
    matched_remote_preference = False
    location_required = bool(search_spec.location)
    title_keywords = [keyword for keyword in search_spec.keywords if keyword.lower() in TITLE_HINT_KEYWORDS]
    for keyword in search_spec.keywords:
        if keyword.lower() in search_text:
            score += 1.0
            matched_keywords.append(keyword)

    for keyword in title_keywords:
        if keyword.lower() in title_text:
            score += 1.0

    if search_spec.location and location_satisfies_search(location_text, search_spec.location):
        score += 1.5
        matched_location = True

    if search_spec.remote_preference and search_spec.remote_preference.lower() in location_text:
        score += 0.75
        matched_remote_preference = True

    if search_spec.seniority and search_spec.seniority.lower() in search_text:
        score += 0.75

    if location_required and not matched_location and not matched_remote_preference:
        score = max(0.25, score - 2.0)

    if location_required and not matched_location and not matched_remote_preference:
        label = "weak_match"
    elif score >= 3.0:
        label = "strong_match"
    elif score >= 1.5:
        label = "medium_match"
    elif score > 0:
        label = "light_match"
    else:
        label = "weak_match"

    rationale_parts = []
    if matched_keywords:
        rationale_parts.append("matched " + ", ".join(matched_keywords[:4]))
    if matched_location:
        rationale_parts.append(f"location fit: {search_spec.location}")
    if matched_remote_preference:
        rationale_parts.append(f"remote preference: {search_spec.remote_preference.replace('_', ' ')}")
    if location_required and not matched_location and not matched_remote_preference:
        rationale_parts.append(f"location mismatch: wanted {search_spec.location}")
    if not rationale_parts:
        rationale_parts.append("board-first discovery matched the search brief loosely.")

    return round(score, 2), label, "; ".join(rationale_parts)


def location_satisfies_search(location_text: str, requested_location: str) -> bool:
    normalized_location = requested_location.lower()
    if normalized_location in location_text:
        return True

    if "remote worldwide" in location_text:
        return True

    return False


def persist_job_leads(state_service: JobStateService, job_leads: list[JobLead]) -> list[JobLead]:
    persisted_jobs = []
    for job_lead in job_leads:
        saved_state, output_paths = state_service.save_job_lead(job_lead)
        persisted_jobs.append(
            replace(
                job_lead,
                state=saved_state.state,
                output_paths=output_paths,
            ),
        )

    return persisted_jobs


def build_match_payloads(job_leads: list[JobLead]) -> list[JobSearchMatchPayload]:
    matches = []
    for job_lead in job_leads:
        matches.append(
            JobSearchMatchPayload(
                job_slug=job_lead.job_slug,
                title=job_lead.title,
                company=job_lead.company,
                location=job_lead.location,
                source=job_lead.source,
                summary=job_lead.summary,
                url=job_lead.source_url,
                source_url=job_lead.source_url,
                state=job_lead.state,
                score=job_lead.score,
                suitability_label=job_lead.suitability_label,
                suitability_rationale=job_lead.suitability_rationale,
                result_origin=job_lead.result_origin,
                actions=build_job_actions(job_lead),
                view_blocks=build_job_view_blocks(job_lead),
            ),
        )

    return matches


def build_job_actions(job_lead: JobLead) -> list[JobActionPayload]:
    return [
        JobActionPayload(
            action_type="job.save",
            label="Save job",
            job_slug=job_lead.job_slug,
            source_url=job_lead.source_url,
            view_block_type="job_card",
        ),
        JobActionPayload(
            action_type="job.select_for_draft",
            label="Select for draft",
            job_slug=job_lead.job_slug,
            source_url=job_lead.source_url,
            view_block_type="job_card",
        ),
        JobActionPayload(
            action_type="job.prepare_application",
            label="Prepare application",
            job_slug=job_lead.job_slug,
            source_url=job_lead.source_url,
            artifact_types=["cv", "cover_letter", "application_answers", "form_field_answers"],
            view_block_type="selection_panel",
        ),
        JobActionPayload(
            action_type="job.open_source",
            label="Open posting",
            job_slug=job_lead.job_slug,
            source_url=job_lead.source_url,
            view_block_type="job_card",
        ),
    ]


def build_job_view_blocks(job_lead: JobLead) -> list[ViewBlockPayload]:
    return [
        ViewBlockPayload(
            block_type="job_card",
            title=job_lead.title,
            summary=job_lead.summary,
            data={
                "job_slug": job_lead.job_slug,
                "company": job_lead.company,
                "location": job_lead.location,
                "source": job_lead.source,
                "source_url": job_lead.source_url,
                "state": job_lead.state,
                "score": job_lead.score,
                "suitability_label": job_lead.suitability_label,
                "result_origin": job_lead.result_origin,
            },
            actions=[
                {
                    "action_type": "job.save",
                    "label": "Save job",
                    "job_slug": job_lead.job_slug,
                },
            ],
        ),
    ]


def build_result_actions(job_leads: list[JobLead]) -> list[JobActionPayload]:
    if not job_leads:
        return []

    job_slugs = [job_lead.job_slug for job_lead in job_leads]
    return [
        JobActionPayload(
            action_type="job.save",
            label="Save all",
            job_slugs=job_slugs,
        ),
        JobActionPayload(
            action_type="job.select_for_draft",
            label="Select shortlist",
            job_slugs=job_slugs,
        ),
    ]


def build_result_view_blocks(
    job_leads: list[JobLead],
    search_spec: SearchSpec,
    recommendation_summary: str,
) -> list[ViewBlockPayload]:
    job_slugs = [job_lead.job_slug for job_lead in job_leads]
    blocks = [
        ViewBlockPayload(
            block_type = "status_summary",
            title = "Job Search Summary",
            summary = recommendation_summary,
            data = {
                "query": search_spec.query,
                "keywords": search_spec.keywords,
                "location": search_spec.location,
                "remote_preference": search_spec.remote_preference,
                "seniority": search_spec.seniority,
                "result_count": len(job_leads),
            },
        ),
    ]

    if job_slugs:
        blocks.append(
            ViewBlockPayload(
                block_type = "selection_panel",
                title = "Selection Actions",
                summary = "Save or shortlist the discovered jobs.",
                actions = [
                    {
                        "action_type": "job.save",
                        "label": "Save all",
                        "job_slugs": job_slugs,
                    },
                    {
                        "action_type": "job.select_for_draft",
                        "label": "Select shortlist",
                        "job_slugs": job_slugs,
                    },
                ],
            ),
        )

    if job_leads:
        blocks.append(
            ViewBlockPayload(
                block_type = "job_list",
                title = "Matches",
                items = [job_lead.to_payload() for job_lead in job_leads],
            ),
        )

    return blocks


def build_recommendation_summary(search_spec: SearchSpec, job_leads: list[JobLead]) -> str:
    if not job_leads:
        return "No job matches were discovered yet."

    top_job = job_leads[0]
    hard_match_count = len(filter_job_leads_by_hard_requirements(search_spec, job_leads))
    if hard_match_count:
        return f"Found {len(job_leads)} job(s), including {hard_match_count} strict title/location match(es). Best initial fit: {top_job.title} at {top_job.company}."

    return f"Found {len(job_leads)} near-miss job(s), but none matched all hard title/location requirements. Best initial candidate: {top_job.title} at {top_job.company}."


def build_final_response(
    search_spec: SearchSpec,
    job_leads: list[JobLead],
    recommendation_summary: str,
) -> str:
    if not job_leads:
        return (
            f"Quiet scan. I normalized the brief into '{search_spec.summary or search_spec.query}' "
            f"and didn't find any job pages worth saving yet. "
            "Try a narrower company, a specific board URL, or a more concrete title/location combo."
        )

    top_job = job_leads[0]
    return (
        f"Found {len(job_leads)} job candidate(s) for '{search_spec.summary or search_spec.query}'. "
        f"Top match is {top_job.title} at {top_job.company}. "
        f"{recommendation_summary}"
    )


def deduplicate_strings(values: list[str]) -> list[str]:
    deduplicated = []
    seen = set()
    for value in values:
        cleaned_value = value.strip()
        lowered_value = cleaned_value.lower()
        if not cleaned_value or lowered_value in seen:
            continue

        seen.add(lowered_value)
        deduplicated.append(cleaned_value)

    return deduplicated


def slugify_job_lead(company: str, title: str, location: str, source_url: str) -> str:
    base_value = " ".join([company, title, location]).strip()
    if not base_value:
        base_value = source_url

    slug = slugify(base_value)
    if slug:
        return slug

    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
    return f"job-{digest}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:80]


def infer_title_from_url(source_url: str) -> str:
    parsed_url = urlparse(source_url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if not path_parts:
        return ""

    return format_slug_name(path_parts[-1])


def infer_company_from_url(source_url: str) -> str:
    parsed_url = urlparse(source_url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if not path_parts:
        return ""

    if parsed_url.netloc.endswith("greenhouse.io") and path_parts:
        return format_slug_name(path_parts[0])

    return format_slug_name(path_parts[0])


def infer_source_from_url(source_url: str) -> str:
    lowered_url = source_url.lower()
    if "greenhouse.io" in lowered_url:
        return "greenhouse"
    if "lever.co" in lowered_url:
        return "lever"
    if "ashbyhq.com" in lowered_url:
        return "ashby"
    return "ats"


def summarize_posting(markdown: str) -> str:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        return ""

    summary_lines = []
    for line in lines:
        if line.startswith("#"):
            continue
        if len(line) > 220:
            continue
        summary_lines.append(line)
        if len(summary_lines) >= 3:
            break

    if not summary_lines:
        summary_lines = lines[:3]

    summary = " ".join(summary_lines)
    return summary[:400].strip()


def format_slug_name(slug: str) -> str:
    cleaned_slug = slug.replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in cleaned_slug.split())
