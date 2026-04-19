import json
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
MONITORING_DIRECTORY = REPO_ROOT / "generated" / "monitoring"
MONITORING_FILE = MONITORING_DIRECTORY / "run_summaries.jsonl"

_current_run_recorder: ContextVar["RunTelemetryRecorder | None"] = ContextVar(
    "current_run_recorder",
    default=None,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso8601(value: datetime | None) -> str:
    if value is None:
        return ""

    return value.isoformat()


def elapsed_ms(started_at: datetime | None, ended_at: datetime | None = None) -> int:
    if started_at is None:
        return 0

    if ended_at is None:
        ended_at = now_utc()

    return max(0, int((ended_at - started_at).total_seconds() * 1000))


def set_current_run_recorder(recorder: "RunTelemetryRecorder | None"):
    return _current_run_recorder.set(recorder)


def reset_current_run_recorder(token) -> None:
    _current_run_recorder.reset(token)


def get_current_run_recorder() -> "RunTelemetryRecorder | None":
    return _current_run_recorder.get()


@dataclass(frozen=True)
class ModelTelemetrySnapshot:
    model_id: str
    display_name: str
    role: str = ""
    gguf_filename: str = ""
    mmproj_filename: str = ""
    supports_vision: bool = False
    quantization: str = ""
    provider: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TimingTelemetrySnapshot:
    started_at: str = ""
    ended_at: str = ""
    elapsed_ms: int = 0
    queue_ms: int = 0
    first_token_ms: int = 0
    prompt_eval_ms: int = 0
    decode_ms: int = 0

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class UsageTelemetrySnapshot:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ActivityTelemetrySnapshot:
    activity_key: str = ""
    label: str = ""
    state: str = ""
    slot_id: str = ""
    parent_activity_key: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass
class PhaseTelemetryRecord:
    phase: str
    detail: str
    started_at: datetime
    ended_at: datetime | None = None

    def to_payload(self) -> dict:
        payload = asdict(self)
        payload["started_at"] = to_iso8601(self.started_at)
        payload["ended_at"] = to_iso8601(self.ended_at)
        payload["elapsed_ms"] = elapsed_ms(self.started_at, self.ended_at)
        return payload


@dataclass
class ModelInvocationTelemetryRecord:
    kind: str
    model: ModelTelemetrySnapshot
    activity_label: str
    phase: str
    started_at: datetime
    ended_at: datetime | None = None
    first_token_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    prompt_eval_ms: int = 0
    decode_ms: int = 0
    queue_ms: int = 0
    status: str = "completed"

    def to_payload(self) -> dict:
        payload = asdict(self)
        payload["model"] = self.model.to_payload()
        payload["started_at"] = to_iso8601(self.started_at)
        payload["ended_at"] = to_iso8601(self.ended_at)
        payload["first_token_at"] = to_iso8601(self.first_token_at)
        payload["elapsed_ms"] = elapsed_ms(self.started_at, self.ended_at)
        payload["first_token_ms"] = elapsed_ms(self.started_at, self.first_token_at)

        duration_seconds = max(0.001, elapsed_ms(self.started_at, self.ended_at) / 1000)
        if self.output_tokens > 0:
            payload["tokens_per_second"] = round(self.output_tokens / duration_seconds, 3)
        else:
            payload["tokens_per_second"] = 0.0

        return payload


@dataclass
class ResultTelemetryRecord:
    result_type: str
    payload: dict[str, Any]
    recorded_at: datetime

    def to_payload(self) -> dict:
        return {
            "result_type": self.result_type,
            "payload": self.payload,
            "recorded_at": to_iso8601(self.recorded_at),
        }


@dataclass
class ArtifactTelemetryRecord:
    artifact_type: str
    path: str
    status: str
    label: str
    recorded_at: datetime

    def to_payload(self) -> dict:
        return {
            "artifact_type": self.artifact_type,
            "path": self.path,
            "status": self.status,
            "label": self.label,
            "recorded_at": to_iso8601(self.recorded_at),
        }


class RunTelemetryRecorder:
    def __init__(
        self,
        run_id: str,
        session_id: int,
        user_message: str,
    ):
        self.run_id = run_id
        self.session_id = session_id
        self.user_message = user_message
        self.started_at = now_utc()
        self.finished_at: datetime | None = None
        self.status = "running"

        self.current_phase = ""
        self.current_phase_detail = ""
        self.current_phase_started_at: datetime | None = None
        self.phase_history: list[PhaseTelemetryRecord] = []

        self.current_activity = ""
        self.current_activity_state = ""
        self.current_slot_id = ""
        self.current_activity_key = ""
        self.parent_activity_key = ""

        self.invocations: list[ModelInvocationTelemetryRecord] = []
        self.results: list[ResultTelemetryRecord] = []
        self.artifacts: list[ArtifactTelemetryRecord] = []
        self.event_kinds: list[str] = []
        self.persisted = False

    @property
    def elapsed_ms(self) -> int:
        return elapsed_ms(self.started_at, self.finished_at)

    def record_event_kind(self, event_kind: str) -> None:
        if not event_kind:
            return

        self.event_kinds.append(event_kind)

    def note_phase_change(self, phase: str, detail: str = "") -> None:
        current_time = now_utc()
        if self.current_phase_started_at is not None:
            self.phase_history.append(
                PhaseTelemetryRecord(
                    phase=self.current_phase,
                    detail=self.current_phase_detail,
                    started_at=self.current_phase_started_at,
                    ended_at=current_time,
                ),
            )

        self.current_phase = phase
        self.current_phase_detail = detail
        self.current_phase_started_at = current_time

    def note_progress(self, status: str, details: dict | None = None) -> None:
        details = details or {}
        self.current_activity = (
            details.get("step_label")
            or details.get("current_task")
            or details.get("label")
            or status
        )
        self.current_activity_state = status
        self.current_slot_id = str(details.get("slot_id") or self.current_slot_id or "")
        self.current_activity_key = str(
            details.get("activity_key")
            or details.get("current_task")
            or self.current_activity_key
            or "",
        )
        self.parent_activity_key = str(details.get("parent_activity_key") or self.parent_activity_key or "")

    def note_result(self, result_type: str, payload: dict[str, Any]) -> None:
        self.results.append(
            ResultTelemetryRecord(
                result_type=result_type,
                payload=payload,
                recorded_at=now_utc(),
            ),
        )

    def note_artifact(self, artifact_type: str, path: str, status: str, label: str) -> None:
        self.artifacts.append(
            ArtifactTelemetryRecord(
                artifact_type=artifact_type,
                path=path,
                status=status,
                label=label,
                recorded_at=now_utc(),
            ),
        )

    def start_model_invocation(self, model, kind: str) -> int:
        invocation = ModelInvocationTelemetryRecord(
            kind=kind,
            model=model_to_snapshot(model),
            activity_label=self.current_activity or self.current_phase or kind,
            phase=self.current_phase,
            started_at=now_utc(),
        )
        self.invocations.append(invocation)
        return len(self.invocations) - 1

    def finish_model_invocation(
        self,
        index: int,
        usage: dict[str, Any] | None = None,
        first_token_at: datetime | None = None,
        status: str = "completed",
    ) -> None:
        if index < 0 or index >= len(self.invocations):
            return

        invocation = self.invocations[index]
        invocation.ended_at = now_utc()
        invocation.first_token_at = first_token_at
        invocation.status = status

        usage = usage or {}
        invocation.input_tokens = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or 0,
        )
        invocation.output_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or 0,
        )
        invocation.total_tokens = int(
            usage.get("total_tokens")
            or invocation.input_tokens + invocation.output_tokens
            or 0,
        )
        invocation.prompt_eval_ms = int(usage.get("prompt_eval_ms") or usage.get("prompt_ms") or 0)
        invocation.decode_ms = int(usage.get("decode_ms") or usage.get("completion_ms") or 0)
        invocation.queue_ms = int(usage.get("queue_ms") or 0)

    def build_snapshot(self, event_kind: str = "") -> dict:
        current_invocation = self.invocations[-1] if self.invocations else None
        activity = ActivityTelemetrySnapshot(
            activity_key=self.current_activity_key,
            label=self.current_activity or self.current_phase_detail or self.current_phase,
            state=self.current_activity_state,
            slot_id=self.current_slot_id,
            parent_activity_key=self.parent_activity_key,
        )
        phase_elapsed = elapsed_ms(self.current_phase_started_at)
        phase_snapshot = {
            "phase": self.current_phase,
            "detail": self.current_phase_detail,
            "started_at": to_iso8601(self.current_phase_started_at),
            "elapsed_ms": phase_elapsed,
        }

        invocation_payload = {}
        model_payload = {}
        timing_payload = TimingTelemetrySnapshot(
            started_at=to_iso8601(self.started_at),
            ended_at=to_iso8601(self.finished_at),
            elapsed_ms=self.elapsed_ms,
            queue_ms=current_invocation.queue_ms if current_invocation else 0,
            first_token_ms=elapsed_ms(current_invocation.started_at, current_invocation.first_token_at)
            if current_invocation and current_invocation.first_token_at
            else 0,
            prompt_eval_ms=current_invocation.prompt_eval_ms if current_invocation else 0,
            decode_ms=current_invocation.decode_ms if current_invocation else 0,
        ).to_payload()
        usage_payload = UsageTelemetrySnapshot(
            input_tokens=current_invocation.input_tokens if current_invocation else 0,
            output_tokens=current_invocation.output_tokens if current_invocation else 0,
            total_tokens=current_invocation.total_tokens if current_invocation else 0,
            tokens_per_second=current_invocation.to_payload().get("tokens_per_second", 0.0)
            if current_invocation
            else 0.0,
        ).to_payload()

        if current_invocation is not None:
            invocation_payload = current_invocation.to_payload()
            model_payload = current_invocation.model.to_payload()

        return {
            "run": {
                "run_id": self.run_id,
                "session_id": self.session_id,
                "status": self.status,
                "started_at": to_iso8601(self.started_at),
                "elapsed_ms": self.elapsed_ms,
                "event_count": len(self.event_kinds),
            },
            "event_kind": event_kind,
            "phase": phase_snapshot,
            "activity": activity.to_payload(),
            "model": model_payload,
            "timing": timing_payload,
            "usage": usage_payload,
            "invocation": invocation_payload,
            "counts": {
                "phases": len(self.phase_history) + (1 if self.current_phase_started_at is not None else 0),
                "results": len(self.results),
                "artifacts": len(self.artifacts),
                "model_invocations": len(self.invocations),
            },
        }

    def mark_finished(self, status: str, final_message: str = "") -> None:
        if self.finished_at is not None:
            return

        self.status = status
        self.finished_at = now_utc()

        if self.current_phase_started_at is None:
            return

        self.phase_history.append(
            PhaseTelemetryRecord(
                phase=self.current_phase,
                detail=self.current_phase_detail,
                started_at=self.current_phase_started_at,
                ended_at=self.finished_at,
            ),
        )
        self.current_phase_started_at = None

    def summary_payload(self) -> dict:
        completed_at = self.finished_at or now_utc()
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "status": self.status,
            "user_message": self.user_message,
            "started_at": to_iso8601(self.started_at),
            "finished_at": to_iso8601(self.finished_at),
            "elapsed_ms": elapsed_ms(self.started_at, completed_at),
            "phase_history": [record.to_payload() for record in self.phase_history],
            "current_phase": self.current_phase,
            "current_phase_detail": self.current_phase_detail,
            "activity": ActivityTelemetrySnapshot(
                activity_key=self.current_activity_key,
                label=self.current_activity or self.current_phase_detail or self.current_phase,
                state=self.current_activity_state,
                slot_id=self.current_slot_id,
                parent_activity_key=self.parent_activity_key,
            ).to_payload(),
            "invocations": [record.to_payload() for record in self.invocations],
            "results": [record.to_payload() for record in self.results],
            "artifacts": [record.to_payload() for record in self.artifacts],
            "event_kinds": self.event_kinds,
        }

    def persist(self) -> None:
        if self.persisted:
            return

        if self.finished_at is None:
            return

        MONITORING_DIRECTORY.mkdir(parents=True, exist_ok=True)
        with MONITORING_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(self.summary_payload(), ensure_ascii=False))
            file.write("\n")

        self.persisted = True


def model_to_snapshot(model) -> ModelTelemetrySnapshot:
    readable_name = getattr(model, "readable_name", None)
    if callable(readable_name):
        display_name = readable_name()
    else:
        display_name = getattr(model, "display_name", "") or getattr(model, "name", "")
    role = getattr(model, "role", "")
    if hasattr(role, "name"):
        role = role.name

    quantization = getattr(model, "quantization", "") or getattr(model, "quant", "")
    if not quantization and hasattr(model, "path"):
        quantization = infer_quantization_from_path(model.path)

    provider = getattr(model, "provider", "")
    if hasattr(provider, "name"):
        provider = provider.name

    return ModelTelemetrySnapshot(
        model_id=getattr(model, "id", ""),
        display_name=display_name,
        role=str(role),
        gguf_filename=Path(getattr(model, "path", "")).name if getattr(model, "path", "") else "",
        mmproj_filename=Path(getattr(model, "mmproj_path", "")).name if getattr(model, "mmproj_path", "") else "",
        supports_vision=bool(getattr(model, "supports_vision", False)),
        quantization=str(quantization),
        provider=str(provider),
    )


def infer_quantization_from_path(path: str) -> str:
    if not path:
        return ""

    filename = Path(path).name
    stem = Path(filename).stem
    parts = stem.split("-")
    if not parts:
        return ""

    return parts[-1]
