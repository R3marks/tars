import asyncio
import logging
import html as html_module
import re
import sys

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("uvicorn.error")


async def fetch_page_markdown(url: str) -> str:
    if not url:
        return ""

    fallback_markdown = fetch_page_markdown_fallback(url)
    if page_text_is_usable(fallback_markdown):
        return fallback_markdown

    if not browser_fetch_is_supported():
        return fallback_markdown

    try:
        from search.web_search import crawl_page_markdown
    except Exception:
        logger.exception("Could not import crawl_page_markdown for web fetch")
        return fallback_markdown

    try:
        browser_markdown = await crawl_page_markdown(url)
        if page_text_is_usable(browser_markdown):
            return browser_markdown
    except Exception:
        logger.exception("Web fetch failed for %s", url)

    return fallback_markdown


def fetch_page_markdown_fallback(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
            },
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Fallback web fetch failed for %s", url)
        return ""

    return html_to_markdownish_text(response.text)


def browser_fetch_is_supported() -> bool:
    if sys.platform != "win32":
        return True

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        return False

    return running_loop.__class__.__name__ == "ProactorEventLoop"


def page_text_is_usable(page_text: str) -> bool:
    if not page_text:
        return False

    meaningful_lines = [line for line in page_text.splitlines() if line.strip()]
    return len(meaningful_lines) >= 8


def html_to_markdownish_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript", "svg", "path"]):
        tag.decompose()

    lines = []

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "li", "p", "div", "section", "label", "button"]):
        if tag.find(["h1", "h2", "h3", "h4", "li", "p", "div", "section", "label", "button"]) is not None:
            continue

        line_text = tag.get_text(" ", strip=True)
        if not line_text:
            continue

        if tag.name == "h1":
            lines.append(f"# {line_text}")
            continue

        if tag.name == "h2":
            lines.append(f"## {line_text}")
            continue

        if tag.name in {"h3", "h4"}:
            lines.append(f"### {line_text}")
            continue

        if tag.name == "li":
            lines.append(f"- {line_text}")
            continue

        lines.append(line_text)

    if not lines:
        lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]

    text = "\n".join(lines)
    text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()
