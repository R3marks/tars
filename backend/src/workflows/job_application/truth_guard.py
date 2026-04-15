import re

commonIgnoredTokens = {
    "across",
    "analysis",
    "application",
    "applications",
    "build",
    "built",
    "client",
    "clients",
    "code",
    "complex",
    "create",
    "created",
    "data",
    "deliver",
    "delivered",
    "design",
    "develop",
    "developed",
    "development",
    "drive",
    "driven",
    "end",
    "engineer",
    "engineering",
    "feature",
    "features",
    "frontend",
    "full",
    "improve",
    "improved",
    "maintain",
    "maintained",
    "model",
    "monitoring",
    "mvp",
    "platform",
    "process",
    "processing",
    "product",
    "production",
    "project",
    "service",
    "services",
    "software",
    "solution",
    "solutions",
    "stakeholder",
    "support",
    "system",
    "systems",
    "team",
    "testing",
    "tool",
    "tools",
    "using",
    "user",
    "users",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def tokenize_for_overlap(text: str) -> list[str]:
    tokens = []

    for token in re.findall(r"[a-z0-9+#/.]+", text.lower()):
        if len(token) >= 4 or token in {"rag", "ci", "cd", "oop", "c#", "sql", "ui"}:
            tokens.append(token)

    return tokens


def overlap_tokens(left_text: str, right_text: str) -> set[str]:
    return set(tokenize_for_overlap(left_text)) & set(tokenize_for_overlap(right_text))


def extract_numeric_values(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?(?:%|\+)?\b", text))


def count_unsupported_tokens(
    text: str,
    allowed_text: str,
    ignored_tokens: set[str] | None = None,
) -> int:
    allowed_tokens = set(tokenize_for_overlap(allowed_text))
    ignored_tokens = commonIgnoredTokens if ignored_tokens is None else ignored_tokens
    unsupported_tokens = []

    for token in tokenize_for_overlap(text):
        if token in allowed_tokens:
            continue

        if token in ignored_tokens:
            continue

        unsupported_tokens.append(token)

    return len(set(unsupported_tokens))


def choose_supported_text(
    proposed_text: str,
    fallback_text: str,
    allowed_text: str,
    minimum_overlap: int,
    unsupported_token_limit: int,
) -> str:
    cleaned_text = proposed_text.strip()
    if not cleaned_text:
        return fallback_text

    if extract_numeric_values(cleaned_text) - extract_numeric_values(allowed_text):
        return fallback_text

    if minimum_overlap > 0 and len(overlap_tokens(cleaned_text, allowed_text)) < minimum_overlap:
        return fallback_text

    if count_unsupported_tokens(cleaned_text, allowed_text) > unsupported_token_limit:
        return fallback_text

    return cleaned_text


def filter_supported_items(
    items: list[str],
    allowed_text: str,
    fallback_items: list[str],
    minimum_overlap: int,
) -> list[str]:
    fallback_lookup = {normalize_text(item) for item in fallback_items}
    supported_items = []

    for item in items:
        cleaned_item = item.strip()
        if not cleaned_item:
            continue

        if normalize_text(cleaned_item) in fallback_lookup:
            supported_items.append(cleaned_item)
            continue

        if len(overlap_tokens(cleaned_item, allowed_text)) < minimum_overlap:
            continue

        if count_unsupported_tokens(cleaned_item, allowed_text) > max(minimum_overlap, 1):
            continue

        supported_items.append(cleaned_item)

    return deduplicate_items(supported_items)


def deduplicate_items(items: list[str]) -> list[str]:
    seen_items = set()
    deduplicated_items = []

    for item in items:
        normalized_item = normalize_text(item)
        if normalized_item in seen_items:
            continue

        seen_items.add(normalized_item)
        deduplicated_items.append(item)

    return deduplicated_items
