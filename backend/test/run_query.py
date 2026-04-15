import argparse
import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.app.api import model_manager  # noqa: E402
from src.app.router import handle_query  # noqa: E402
from src.message_structures.conversation import Conversation  # noqa: E402
from src.message_structures.message import Message  # noqa: E402


class RecordingWebSocket:
    def __init__(self):
        self.payloads = []

    async def send_json(self, payload):
        self.payloads.append(payload)

        payload_type = payload.get("type", "message")
        message = payload.get("message", "")
        print(f"[{payload_type}] {message}")

        if payload_type != "workflow_summary":
            return

        for changed_item in payload.get("changed", []):
            print(f"  changed: {changed_item}")

        for unchanged_item in payload.get("unchanged", []):
            print(f"  kept:    {unchanged_item}")

        for blocked_item in payload.get("blocked", []):
            print(f"  blocked: {blocked_item}")

        for review_item in payload.get("needs_review", []):
            print(f"  review:  {review_item}")

        if payload.get("output_path"):
            print(f"  html:    {payload['output_path']}")

        if payload.get("pdf_output_path"):
            page_count = payload.get("pdf_page_count")
            page_suffix = ""
            if page_count is not None:
                page_suffix = f" ({page_count} pages)"

            print(f"  pdf:     {payload['pdf_output_path']}{page_suffix}")

        for output_path in payload.get("output_paths", []):
            print(f"  output:  {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a backend query through the router/workflow path and print websocket messages.",
    )
    parser.add_argument("--message", help="Inline query text to send.")
    parser.add_argument(
        "--query-file",
        help="Path to a text file containing the query.",
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

    raise ValueError("Provide either --message or --query-file.")


async def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    query = load_query(args)

    websocket = RecordingWebSocket()
    conversation = Conversation(999)
    conversation.append_message(Message(role="user", content=query))

    await handle_query(
        query=query,
        websocket=websocket,
        conversation_history=conversation,
        model_manager=model_manager,
    )


if __name__ == "__main__":
    asyncio.run(main())
