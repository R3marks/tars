# src/tool_parsers/granite_4.py
import re
import json
import html
import logging

logger = logging.getLogger("uvicorn.error")


def _clean_block_before_json(block: str) -> str:
    """
    Try multiple lightweight cleanups to make the block JSON-parseable:
      - decode HTML entities (done earlier)
      - remove stray '**' inserted into keys (e.g. name**:)
      - collapse repeated commas or stray punctuation
      - ensure property names are double-quoted
      - escape single backslashes in Windows paths
    """
    s = block

    # 1) Remove stray bolding marks or accidental '**' inserted into keys/values
    #    Replace occurrences of word** or **word with word
    s = re.sub(r"\*\*(?=\w)", "", s)
    s = re.sub(r"(?<=\w)\*\*", "", s)
    # Also remove stray `**:` (sometimes returned by model)
    s = s.replace("**:", ":")

    # 2) Make sure typical HTML quotes like &#34; &quot; are resolved
    s = html.unescape(s)

    # 3) Fix “smart quotes” to normal quotes
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    # 4) Ensure JSON property names are double-quoted: try to add quotes for barewords like name: ...
    #    Conservative regex: replace word:  with "word":
    s = re.sub(r'(?m)(^|[\{\s,])([A-Za-z_][A-Za-z0-9_-]*)\s*:', r'\1"\2":', s)

    # 5) Escape backslashes that are unescaped (windows paths)
    #    Replace single backslash that is not already escaped with double backslash
    s = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', s)

    # 6) Remove trailing commas before closing braces/brackets
    s = re.sub(r',\s*([\]\}])', r'\1', s)

    # 7) Trim outer whitespace/newlines
    s = s.strip()

    return s


def parse_granite_tool_call(content: str) -> list[dict]:
    """
    Parse Granite-style <tool_call> blocks into standardized tool call dicts.
    Very defensive: tries multiple cleanups and logs at each step.
    """

    tool_calls = []

    if not content or not isinstance(content, str):
        logger.debug("parse_granite_tool_call: empty or non-string content")
        return tool_calls

    logger.info(f"Raw content (first 300 chars): {content[:300].replace(chr(10),'\\n')}")

    # 1) HTML-unescape to handle &lt; &gt; &quot; etc.
    decoded = html.unescape(content)
    logger.info(f"HTML-decoded content (first 300 chars): {decoded[:300].replace(chr(10),'\\n')}")

    # 2) find all <tool_call>...</tool_call> blocks (non-greedy, allow newlines)
    matches = list(re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", decoded, re.DOTALL))
    logger.info(f"Found {len(matches)} potential tool_call blocks")

    for i, m in enumerate(matches, start=1):
        raw_block = m.group(1).strip()
        logger.info(f"[Block {i}] raw (first 220 chars): {raw_block[:220].replace(chr(10),'\\n')}")

        # Try parsing raw first
        parsed = None
        tried = []

        # Attempt 0: direct json.loads
        try:
            parsed = json.loads(raw_block)
            logger.info(f"[Block {i}] parsed successfully (direct)")
        except Exception as e0:
            tried.append(("direct", str(e0)))
            # Attempt 1: cleaned block
            cleaned = _clean_block_before_json(raw_block)
            tried.append(("cleaned", cleaned[:200].replace("\n", "\\n")))
            try:
                parsed = json.loads(cleaned)
                logger.info(f"[Block {i}] parsed successfully after cleaning")
            except Exception as e1:
                tried.append(("cleaned_err", str(e1)))
                # Attempt 2: try unicode_escape then parse
                try:
                    unescaped = cleaned.encode("utf-8").decode("unicode_escape")
                    try:
                        parsed = json.loads(unescaped)
                        logger.info(f"[Block {i}] parsed after unicode_escape")
                    except Exception as e2:
                        tried.append(("unicode_escape_err", str(e2)))
                except Exception as e_ue:
                    tried.append(("unicode_escape_fail", str(e_ue)))

        if not parsed:
            logger.error(f"[Block {i}] Failed to parse JSON. Attempts: {tried}")
            logger.debug(f"[Block {i}] content snippet: {raw_block[:300].replace(chr(10),'\\n')}")
            continue

        if not isinstance(parsed, dict):
            logger.error(f"[Block {i}] Parsed JSON is not an object: {type(parsed)}")
            continue

        func_name = parsed.get("name")
        args = parsed.get("arguments", {})

        logger.info(f"[Block {i}] Parsed tool call: {func_name}({args})")

        tool_calls.append({
            "function": {
                "name": func_name,
                "arguments": json.dumps(args)
            }
        })

    if not tool_calls:
        logger.debug("No valid tool calls parsed from content (parse_granite_tool_call).")

    return tool_calls
