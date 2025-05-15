import requests
from bs4 import BeautifulSoup
import trafilatura
import os
import time
from urllib.parse import urljoin

BASE_URL = "https://developer.android.com"
START_PATH = "/guide"
visited = set()
OUTPUT_DIR = "android_docs_text"
MAX_PAGES = 50  # to avoid crawling too much at once

def clean_text(html: str) -> str:
    return trafilatura.extract(html, include_comments=False, include_tables=False)

def is_valid_link(href: str) -> bool:
    return href and href.startswith("/guide") and not any(x in href for x in ["#","mailto:",".jpg",".png",".zip"])

def crawl(url_path: str, depth=0):
    if url_path in visited or len(visited) >= MAX_PAGES:
        return
    visited.add(url_path)
    
    full_url = urljoin(BASE_URL, url_path)
    print(f"Crawling: {full_url}")
    
    try:
        res = requests.get(full_url, timeout=10)
        if res.status_code != 200:
            print(f"Failed to fetch {full_url}")
            return
    except Exception as e:
        print(f"Request error: {e}")
        return

    html = res.text
    text = clean_text(html)

    if text:
        filename = url_path.strip("/").replace("/", "_") + ".txt"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if is_valid_link(href):
            crawl(href, depth + 1)
            time.sleep(0.5)  # avoid hammering the server

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    crawl(START_PATH)
    print(f"Done. Crawled {len(visited)} pages.")
