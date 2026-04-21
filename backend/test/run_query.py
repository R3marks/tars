import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.app.api import handle_socket_message  # noqa: E402


class RecordingWebSocket:
    def __init__(self):
        self.payloads = []

    async def send_json(self, payload):
        self.payloads.append(payload)

        payload_type = payload.get("event_kind") or payload.get("type", "message")
        payload_body = payload.get("payload", {})
        message = payload.get("message", "") or payload_body.get("text", "") or payload_body.get("summary", "")
        write_line(f"[{payload_type}] {message}")

        result_type = payload_body.get("result_type", "")
        if result_type != "workflow_summary":
            return

        for changed_item in payload_body.get("changed", []):
            write_line(f"  changed: {changed_item}")

        for unchanged_item in payload_body.get("unchanged", []):
            write_line(f"  kept:    {unchanged_item}")

        for blocked_item in payload_body.get("blocked", []):
            write_line(f"  blocked: {blocked_item}")

        for review_item in payload_body.get("needs_review", []):
            write_line(f"  review:  {review_item}")

        if payload_body.get("output_path"):
            write_line(f"  html:    {payload_body['output_path']}")

        if payload_body.get("pdf_output_path"):
            page_count = payload_body.get("pdf_page_count")
            page_suffix = ""
            if page_count is not None:
                page_suffix = f" ({page_count} pages)"

            write_line(f"  pdf:     {payload_body['pdf_output_path']}{page_suffix}")

        for output_path in payload_body.get("output_paths", []):
            write_line(f"  output:  {output_path}")


def write_line(text: str) -> None:
    encoded_text = (text + "\n").encode("utf-8", errors="replace")
    sys.stdout.buffer.write(encoded_text)
    sys.stdout.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a backend query through the router/workflow path and print websocket messages.",
    )
    parser.add_argument("--message", help="Inline query text to send.")
    parser.add_argument(
        "--query-file",
        help="Path to a text file containing the query.",
    )
    parser.add_argument(
        "--event-kind",
        default="run.create",
        help="Client event kind to send to the backend.",
    )
    parser.add_argument("--action-type", help="Action type for run.action requests.")
    parser.add_argument("--job-slug", help="Single job slug for run.action requests.")
    parser.add_argument(
        "--job-slugs",
        nargs="*",
        default=[],
        help="Multiple job slugs for run.action requests.",
    )
    parser.add_argument("--target-status", help="Desired status for run.action requests.")
    parser.add_argument(
        "--artifact-types",
        nargs="*",
        default=[],
        help="Requested artifact types for run.action requests.",
    )
    return parser.parse_args()


def load_query(args: argparse.Namespace) -> str:
    if args.message:
        return args.message.strip()

    if args.query_file:
        query_path = Path(args.query_file)
        if not query_path.is_absolute():
            query_path = PROJECT_ROOT / query_path

        return query_path.read_text(encoding="utf-8").strip()

    return ""


async def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    query = load_query(args)

    websocket = RecordingWebSocket()
    if args.event_kind == "run.action":
        payload = {
            "event_kind": "run.action",
            "session_id": 999,
            "payload": {
                "action_type": args.action_type or "job.save",
                "job_slug": args.job_slug or "",
                "job_slugs": args.job_slugs,
                "target_status": args.target_status or "",
                "artifact_types": args.artifact_types,
                "message": query,
            },
        }
    else:
        if not query:
            raise ValueError("Provide either --message or --query-file.")

        payload = {
            "event_kind": "run.create",
            "session_id": 999,
            "payload": {
                "message": query,
            },
        }

    await handle_socket_message(websocket, json.dumps(payload))


if __name__ == "__main__":
    asyncio.run(main())
