import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from tqdm import tqdm

# === CONFIG ===
SOURCE_DIR = Path("android_docs_markdown")
MAX_FILES = 1000
MAX_WORKERS = 8

# === MARKERS FOR HEADER/FOOTER STRIPPING ===
HEADER_MARKERS = [
    r"developer\.android\.com uses cookies",
    r"\* Essentials",
    r"Android platform\n",
    r"^\s*AgreeNo thanks",  # cookie banner
]

FOOTER_MARKERS = [
    r"Please help us improve the Android Developer experience",
    r"Follow @AndroidDev on X",
    r"Manage cookies",
    r"Subscribe",
    r"Last updated \d{4}-\d{2}-\d{2} UTC\.",
    r"\[\[\[.*?\]\]\]",  # footer metadata
]

# === FILTERING ===
def should_skip(file_path: Path) -> bool:
    return "api_diff" in file_path.name.lower()

# === CLEANING FUNCTIONS ===
def strip_header_footer(content: str) -> str:
    for marker in HEADER_MARKERS:
        content = re.split(marker, content, maxsplit=1)[-1]
    for marker in FOOTER_MARKERS:
        content = re.split(marker, content, maxsplit=1)[0]
    return content

def remove_urls(content: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

def remove_images(content: str) -> str:
    return re.sub(r"!\[.*?\]\(.*?\)", "", content)

def remove_navigation_blocks(content: str) -> str:
    nav_sections = [
        r"\*\s+Develop\s+\*.*?\*\s+Libraries",  # Big nav list
        r"\*\s+Home\s+\*.*?\*\s+Android Studio",  # Main nav
        r"(?s)UI Design\s+[*]+\s+Design for Android.*?Android TV",  # Design nav
    ]
    for pattern in nav_sections:
        content = re.sub(pattern, "", content)
    return content

def clean_content(content: str) -> str:
    content = strip_header_footer(content)
    content = remove_navigation_blocks(content)
    content = remove_urls(content)
    content = remove_images(content)
    content = re.sub(r"\*{2,}", "*", content)  # simplify multiple asterisks
    content = re.sub(r"\n{2,}", "\n\n", content)  # normalize line breaks
    content = re.sub(r"\s+\n", "\n", content)  # trim trailing spaces before newlines
    return content.strip()

# === FILE PROCESSING ===
def process_file(file_path: Path, out_dir: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned = clean_content(content)

        out_path = out_dir / file_path.name
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        return f"✅ {file_path.name}"
    except Exception as e:
        return f"❌ Error processing {file_path.name}: {e}"

# === MAIN CLEANING DRIVER ===
def clean_files_concurrently(source_dir: Path, limit: int, max_workers: int = 8):
    all_files = [f for f in source_dir.glob("**/*.md") if not should_skip(f)]
    files_to_process = all_files # [:limit]
    out_dir = source_dir.parent / (source_dir.name + "_cleaned")
    out_dir.mkdir(exist_ok=True)

    print(f"🧹 Cleaning {len(files_to_process)} files...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, file, out_dir): file for file in files_to_process}
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Progress"):
            pass  # progress only

if __name__ == "__main__":
    clean_files_concurrently(SOURCE_DIR, MAX_FILES, MAX_WORKERS)
