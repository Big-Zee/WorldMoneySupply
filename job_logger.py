"""Shared audit logger for M2 scraper jobs.

Writes to output/job_status.json always (local dev + production).
Also writes to Azure Table Storage when AZURE_STORAGE_CONNECTION_STRING is set.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

JSON_PATH = Path("output/job_status.json")
MAX_ENTRIES = 100
TABLE_NAME = "ScraperJobStatus"


def log(
    scraper: str,
    status: str,
    rows_added: int,
    latest_date: str | None,
    duration_seconds: float,
    error: str | None = None,
) -> None:
    """Record a scraper run result.

    Args:
        scraper: Scraper identifier — "US", "ALL", "JP", etc.
        status: "success" or "error"
        rows_added: Number of new rows written to CSV (0 on error or no new data)
        latest_date: Most recent data date in CSV after run ("YYYY-MM-DD"), or None on error
        duration_seconds: Wall-clock seconds the run took
        error: Error message string, or None on success
    """
    entry = {
        "scraper": scraper,
        "run_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "rows_added": rows_added,
        "latest_date": latest_date,
        "duration_seconds": round(duration_seconds, 1),
        "error": error,
    }
    _write_json(entry)
    _write_table(entry)


def _write_json(entry: dict) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if JSON_PATH.exists():
        try:
            entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(entry)
    entries = entries[-MAX_ENTRIES:]
    JSON_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    logger.info("Job status logged: %s → %s", entry["scraper"], entry["status"])


def _write_table(entry: dict) -> None:
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        return
    try:
        from azure.data.tables import TableServiceClient
    except ImportError:
        logger.debug("azure-data-tables not installed; skipping Table Storage write")
        return
    try:
        service = TableServiceClient.from_connection_string(conn_str)
        table = service.create_table_if_not_exists(TABLE_NAME)
        entity = {
            "PartitionKey": entry["scraper"],
            "RowKey": entry["run_at"],
            "status": entry["status"],
            "rows_added": entry["rows_added"],
            "latest_date": entry["latest_date"] or "",
            "duration_seconds": entry["duration_seconds"],
            "error": entry["error"] or "",
        }
        table.upsert_entity(entity)
        logger.debug("Table Storage updated: %s/%s", entry["scraper"], entry["run_at"])
    except Exception as exc:
        logger.warning("Failed to write to Table Storage: %s", exc)
