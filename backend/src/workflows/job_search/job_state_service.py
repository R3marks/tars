import json
import threading
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.app.result_payloads import SavedJobStatePayload
from src.config.RuntimeEnvironment import runtime_environment
from src.workflows.job_search.models import JobLead, SearchSpec


JOB_STATE_LOCK = threading.Lock()


@dataclass(frozen=True)
class JobCatalogEntry:
    job_slug: str
    title: str
    company: str
    location: str
    source: str
    source_url: str
    state: str = "discovered"
    score: float = 0.0
    suitability_label: str = ""
    suitability_rationale: str = ""
    result_origin: str = "catalog"
    output_paths: list[str] = field(default_factory=list)
    updated_at: str = ""

    def to_payload(self) -> dict:
        return asdict(self)


class JobStateService:
    def __init__(self, jobs_root: Path | None = None):
        self.runtime_environment = runtime_environment()
        self.jobs_root = jobs_root or self.runtime_environment.generated_directory / "jobs"
        self.catalog_path = self.jobs_root / "catalog.json"

    def ensure_root(self) -> None:
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def load_catalog(self) -> dict[str, Any]:
        self.ensure_root()
        if not self.catalog_path.exists():
            return {"jobs": {}, "updated_at": "", "count": 0}

        try:
            with self.catalog_path.open(encoding="utf-8") as file:
                catalog = json.load(file)
        except Exception:
            return {"jobs": {}, "updated_at": "", "count": 0}

        catalog.setdefault("jobs", {})
        catalog.setdefault("updated_at", "")
        catalog.setdefault("count", len(catalog["jobs"]))
        return catalog

    def save_catalog(self, catalog: dict[str, Any]) -> None:
        self.ensure_root()
        catalog["updated_at"] = self.now_iso()
        catalog["count"] = len(catalog.get("jobs", {}))
        with self.catalog_path.open("w", encoding="utf-8") as file:
            json.dump(catalog, file, indent=2, ensure_ascii=False)

    def load_job_record(self, job_slug: str) -> dict[str, Any]:
        record_path = self.job_folder(job_slug) / "job_lead.json"
        if not record_path.exists():
            return {}

        try:
            with record_path.open(encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def job_folder(self, job_slug: str) -> Path:
        return self.jobs_root / job_slug

    def save_job_lead(self, job_lead: JobLead) -> tuple[SavedJobStatePayload, list[str]]:
        with JOB_STATE_LOCK:
            self.ensure_root()
            job_folder = self.job_folder(job_lead.job_slug)
            job_folder.mkdir(parents=True, exist_ok=True)

            output_paths = []
            lead_record = self.build_job_record(job_lead)
            lead_path = job_folder / "job_lead.json"
            lead_path.write_text(
                json.dumps(lead_record, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            output_paths.append(str(lead_path))

            if job_lead.job_posting_text:
                posting_path = job_folder / "job_posting.md"
                posting_path.write_text(job_lead.job_posting_text.strip() + "\n", encoding="utf-8")
                output_paths.append(str(posting_path))

            suitability_path = job_folder / "suitability.json"
            suitability_path.write_text(
                json.dumps(
                    {
                        "job_slug": job_lead.job_slug,
                        "score": job_lead.score,
                        "label": job_lead.suitability_label,
                        "rationale": job_lead.suitability_rationale,
                        "search_keywords": job_lead.search_keywords,
                        "updated_at": self.now_iso(),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_paths.append(str(suitability_path))

            catalog = self.load_catalog()
            catalog["jobs"][job_lead.job_slug] = self.build_catalog_entry(job_lead, output_paths).to_payload()
            self.save_catalog(catalog)

            saved_state = SavedJobStatePayload(
                job_slug=job_lead.job_slug,
                state=job_lead.state,
                title=job_lead.title,
                company=job_lead.company,
                location=job_lead.location,
                source=job_lead.source,
                source_url=job_lead.source_url,
                summary=job_lead.summary,
                output_paths=output_paths,
                job_record=lead_record,
            )
            return saved_state, output_paths

    def update_job_state(
        self,
        job_slug: str,
        state: str,
        previous_state: str = "",
        note: str = "",
        target_artifact_types: list[str] | None = None,
    ) -> SavedJobStatePayload:
        with JOB_STATE_LOCK:
            catalog = self.load_catalog()
            record = self.load_job_record(job_slug) or catalog.get("jobs", {}).get(job_slug, {})
            if not record:
                record = {
                    "job_slug": job_slug,
                    "title": "",
                    "company": "",
                    "location": "",
                    "source": "",
                    "source_url": "",
                    "summary": "",
                }

            previous_state = previous_state or record.get("state", "")
            record["previous_state"] = previous_state
            record["state"] = state
            record["state_note"] = note
            if target_artifact_types:
                record["target_artifact_types"] = target_artifact_types
            record["updated_at"] = self.now_iso()

            job_folder = self.job_folder(job_slug)
            job_folder.mkdir(parents=True, exist_ok=True)
            lead_path = job_folder / "job_lead.json"
            lead_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

            catalog_job = catalog.get("jobs", {}).get(job_slug, {})
            catalog_job.update(
                {
                    "job_slug": job_slug,
                    "title": record.get("title", ""),
                    "company": record.get("company", ""),
                    "location": record.get("location", ""),
                    "source": record.get("source", ""),
                    "source_url": record.get("source_url", ""),
                    "state": state,
                    "updated_at": record["updated_at"],
                },
            )
            catalog.setdefault("jobs", {})[job_slug] = catalog_job
            self.save_catalog(catalog)

            output_paths = [str(lead_path)]
            return SavedJobStatePayload(
                job_slug=job_slug,
                state=state,
                previous_state=previous_state,
                title=record.get("title", ""),
                company=record.get("company", ""),
                location=record.get("location", ""),
                source=record.get("source", ""),
                source_url=record.get("source_url", ""),
                summary=record.get("summary", ""),
                output_paths=output_paths,
                job_record=record,
            )

    def find_matching_records(self, search_spec: SearchSpec) -> list[dict[str, Any]]:
        catalog = self.load_catalog()
        records = list(catalog.get("jobs", {}).values())
        if not records:
            return []

        scored_records = []
        for record in records:
            if str(record.get("state", "")).strip().lower() == "discovered":
                continue

            score = self.score_record(record, search_spec)
            if score <= 0:
                continue

            record_copy = dict(record)
            record_copy["score"] = score
            scored_records.append(record_copy)

        scored_records.sort(key=lambda item: item.get("score", 0), reverse=True)
        return scored_records[: search_spec.limit]

    def score_record(self, record: dict[str, Any], search_spec: SearchSpec) -> float:
        search_text = " ".join(
            [
                record.get("title", ""),
                record.get("company", ""),
                record.get("location", ""),
                record.get("summary", ""),
                record.get("source", ""),
            ],
        ).lower()
        score = 0.0

        for keyword in search_spec.keywords:
            if keyword.lower() in search_text:
                score += 1.0

        if search_spec.location and search_spec.location.lower() in search_text:
            score += 2.0

        if search_spec.remote_preference and search_spec.remote_preference.lower() in search_text:
            score += 1.0

        for company_name in search_spec.company_names:
            if company_name.lower() in search_text:
                score += 2.0

        return score

    def build_job_record(self, job_lead: JobLead) -> dict[str, Any]:
        record = job_lead.to_payload()
        record["updated_at"] = self.now_iso()
        return record

    def build_catalog_entry(self, job_lead: JobLead, output_paths: list[str]) -> JobCatalogEntry:
        return JobCatalogEntry(
            job_slug=job_lead.job_slug,
            title=job_lead.title,
            company=job_lead.company,
            location=job_lead.location,
            source=job_lead.source,
            source_url=job_lead.source_url,
            state=job_lead.state,
            score=job_lead.score,
            suitability_label=job_lead.suitability_label,
            suitability_rationale=job_lead.suitability_rationale,
            result_origin="catalog",
            output_paths=output_paths,
            updated_at=self.now_iso(),
        )

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def build_saved_state_for_record(self, record: dict[str, Any]) -> SavedJobStatePayload:
        return SavedJobStatePayload(
            job_slug=record.get("job_slug", ""),
            state=record.get("state", ""),
            previous_state=record.get("previous_state", ""),
            title=record.get("title", ""),
            company=record.get("company", ""),
            location=record.get("location", ""),
            source=record.get("source", ""),
            source_url=record.get("source_url", ""),
            summary=record.get("summary", ""),
            output_paths=record.get("output_paths", []),
            job_record=record,
        )
