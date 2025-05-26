import os
import asyncio
import hashlib
from pathlib import Path
import random
from urllib.parse import urlparse, quote
from typing import List
import aiohttp
from xml.etree import ElementTree

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerMonitor,
    CrawlerRunConfig,
    CacheMode,
    DisplayMode,
    MemoryAdaptiveDispatcher
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

OUTPUT_DIR = Path("./android_docs_markdown")
OUTPUT_DIR.mkdir(exist_ok=True)

SECTIONS_TO_INCLUDE = [
    "about", "adaptive-apps", "agi", "ai", "assistant",
    "build", "cars", "chrome-os", "compose-camp", "courses",
    "design", "develop", "distribute", "docs", "events",
    "games", "get-started", "guide", "health-and-fitness",
    "identity", "jetpack", "kotlin", "large-screens", "media",
    "modern-android-development", "multi-device-development",
    "ndk", "platform", "privacy", "productivity", "quick-guides",
    "reference", "samples", "sdk", "security", "series",
    "studio", "support", "teach", "tools", "topic", "training",
    "tv", "wear", "work", "xr"
]

def safe_filename_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/").replace("/", "_")
    query = parsed_url.query
    if query:
        query = quote(query, safe='')
        filename = f"{path}_{query}"
    else:
        filename = path or "index"
    filename = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in filename)
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"{filename}_{url_hash}.md"

# Asynchronously fetch a sitemap and return URLs
async def fetch_sitemap(session: aiohttp.ClientSession, url: str) -> List[str]:
    print(f"🔍 Fetching sitemap: {url}")
    try:
        async with session.get(url, timeout=45) as response:
            text = await response.text()
            if response.status != 200:
                print(f"❌ HTTP error: {response.status} — {url}")
                return []

            try:
                root = ElementTree.fromstring(text)
            except ElementTree.ParseError as e:
                print(f"❌ XML ParseError for {url}: {e}")
                print(f"🔧 Partial XML content: {text[:500]}...")
                return []

            # Guess namespace if not default
            nsmap = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [loc.text for loc in root.findall('.//ns:loc', nsmap)]

            print(f"✅ Found {len(urls)} URLs in sitemap: {url}")
            return urls

    except Exception as e:
        print(f"❌ Error fetching sitemap {url}: {e}")
        return []

# Main function to get filtered URLs for a specific section
async def get_filtered_android_doc_urls(
    section_keywords: List[str],
    max_urls: int = 1000
) -> List[str]:
    print("📥 Starting to fetch main sitemap...")
    main_sitemap = "https://developer.android.com/sitemap.xml"

    async with aiohttp.ClientSession() as session:
        sub_sitemaps = await fetch_sitemap(session, main_sitemap)

        print(f"📂 Found {len(sub_sitemaps)} sub-sitemaps. Processing...")
        tasks = [fetch_sitemap(session, sitemap) for sitemap in sub_sitemaps]
        results = await asyncio.gather(*tasks)

    all_urls = set()
    for urls in results:
        all_urls.update(urls)

    sections = {
        urlparse(url).path.strip("/").split("/")[0]
        for url in all_urls
        if urlparse(url).netloc == "developer.android.com"
    }
    print(f"📚 Available top-level sections: {sorted(sections)}")

    # ✅ Multi-section filter
    filtered_urls = [
        url for url in all_urls
        if (
            urlparse(url).path.strip("/").split("/")[0] in section_keywords
            and ('hl=' not in url or 'hl=en' in url)
        )
    ]

    print(f"✅ Found {len(filtered_urls)} URLs matching sections {section_keywords}")

    # Shuffle to mix across sections/sitemaps
    filtered_urls = list(filtered_urls)
    random.shuffle(filtered_urls)

    if max_urls and len(filtered_urls) > max_urls:
        filtered_urls = filtered_urls[:max_urls]

    print(f"✅ Final count: {len(filtered_urls)} URLs selected")
    return filtered_urls

async def crawl_android_docs(
        urls: List[str], 
        max_depth=1, 
        max_pages=1000, 
        max_concurrent=5):
    browser_config = BrowserConfig(headless=True)

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        verbose=False
    )

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=3.0,
        max_session_permit=10,
        monitor=CrawlerMonitor(
            # display_mode=DisplayMode.AGGREGATED
        )
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Get all results at once
        results = await crawler.arun_many(
            urls=urls,
            config=crawl_config,
            dispatcher=dispatcher
        )

        # Process all results after completion
        for result in results:
            if result.success and result.markdown:
                filename = safe_filename_from_url(result.url)
                filepath = OUTPUT_DIR / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(result.markdown if isinstance(result.markdown, str) else result.markdown.markdown)
            else:
                print(f" ❌ Failed to crawl {result.url}: {result.error_message}")

        print(f"✅ Saved: {len(results)} results")


if __name__ == "__main__":
    urls_to_crawl = asyncio.run(get_filtered_android_doc_urls(
        section_keywords=SECTIONS_TO_INCLUDE,
        max_urls=3000
    ))
    print(f"🌐 Ready to crawl {len(urls_to_crawl)} URLs across sections.")

    asyncio.run(crawl_android_docs(urls_to_crawl, max_depth=1, max_pages=1000, max_concurrent=5))
