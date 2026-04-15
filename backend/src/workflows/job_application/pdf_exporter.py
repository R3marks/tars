import logging
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("uvicorn.error")
minimumPdfSizeBytes = 5000

BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def export_html_to_pdf(html_path: Path) -> tuple[str, int | None]:
    browser_path = find_available_browser()
    if browser_path is None:
        logger.info("Skipping PDF export because no supported browser was found.")
        return "", None

    source_path = html_path.resolve()
    pdf_path = source_path.with_suffix(".pdf")
    user_data_dir = Path(tempfile.mkdtemp(prefix="tars-browser-"))

    command_variants = [
        [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--disable-crash-reporter",
            "--disable-crashpad",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            f"--user-data-dir={user_data_dir}",
            f"--print-to-pdf={pdf_path}",
            source_path.as_uri(),
        ],
        [
            str(browser_path),
            "--headless",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--disable-crash-reporter",
            "--disable-crashpad",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            f"--user-data-dir={user_data_dir}",
            f"--print-to-pdf={pdf_path}",
            source_path.as_uri(),
        ],
    ]

    for command in command_variants:
        if run_pdf_command(command):
            if not validate_generated_pdf(pdf_path):
                remove_invalid_pdf(pdf_path)
                continue

            page_count = estimate_pdf_page_count(pdf_path)
            return str(pdf_path), page_count

    logger.warning("PDF export failed for %s", source_path)
    remove_invalid_pdf(pdf_path)
    return "", None


def find_available_browser() -> Path | None:
    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def run_pdf_command(command: list[str]) -> bool:
    try:
        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception:
        logger.exception("PDF export command crashed")
        return False

    if completed_process.returncode == 0:
        return True

    logger.warning(
        "PDF export command failed: %s | stderr=%s",
        command[0],
        completed_process.stderr[:500],
    )
    return False


def estimate_pdf_page_count(pdf_path: Path) -> int | None:
    if not pdf_path.exists():
        return None

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError:
        logger.exception("Could not read generated PDF at %s", pdf_path)
        return None

    page_matches = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
    if not page_matches:
        return None

    return len(page_matches)


def validate_generated_pdf(pdf_path: Path) -> bool:
    if not pdf_path.exists():
        logger.warning("Expected PDF was not created at %s", pdf_path)
        return False

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError:
        logger.exception("Could not read generated PDF at %s", pdf_path)
        return False

    if not pdf_bytes.startswith(b"%PDF"):
        logger.warning("Generated file is not a valid PDF header: %s", pdf_path)
        return False

    if len(pdf_bytes) < minimumPdfSizeBytes:
        logger.warning(
            "Generated PDF is suspiciously small (%s bytes): %s",
            len(pdf_bytes),
            pdf_path,
        )
        return False

    if estimate_pdf_page_count(pdf_path) is None:
        logger.warning("Generated PDF does not contain detectable pages: %s", pdf_path)
        return False

    return True


def remove_invalid_pdf(pdf_path: Path):
    if not pdf_path.exists():
        return

    try:
        pdf_path.unlink()
    except OSError:
        logger.exception("Could not remove invalid PDF at %s", pdf_path)
