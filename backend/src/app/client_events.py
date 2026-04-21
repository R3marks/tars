from src.app.result_payloads import RunActionPayload


def parse_run_action_payload(payload: dict, payload_body: dict) -> RunActionPayload:
    job_slugs = payload_body.get("job_slugs") or payload.get("job_slugs", [])
    artifact_types = payload_body.get("artifact_types") or payload.get("artifact_types", [])

    return RunActionPayload(
        action_type=payload_body.get("action_type") or payload.get("action_type", ""),
        job_slug=payload_body.get("job_slug") or payload.get("job_slug", ""),
        job_slugs=job_slugs if isinstance(job_slugs, list) else [job_slugs],
        target_status=payload_body.get("target_status") or payload.get("target_status", ""),
        artifact_types=artifact_types if isinstance(artifact_types, list) else [artifact_types],
        source_url=payload_body.get("source_url") or payload.get("source_url", ""),
        query=payload_body.get("message") or payload.get("message", ""),
        display_mode=payload_body.get("display_mode") or payload.get("display_mode", ""),
    )


def summarize_run_action(action_request: RunActionPayload) -> str:
    targets = []
    if action_request.job_slug:
        targets.append(action_request.job_slug)

    targets.extend(action_request.job_slugs)
    clean_targets = [target for target in targets if target]

    if clean_targets:
        return f"{action_request.action_type} for {', '.join(clean_targets)}"

    return action_request.action_type or "run action"
