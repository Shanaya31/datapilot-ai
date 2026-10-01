"""Day 9: FastAPI incident app.

    uvicorn datapilot.api.main:app --reload --port 8080

Endpoints:
    GET  /health
    GET  /pipelines                         -> latest run of each pipeline (health board)
    GET  /pipelines/{pipeline_name}/runs     -> recent run history
    POST /investigate                        -> run the agent graph on a run_id, save + return the incident
    GET  /incidents/{run_id}                 -> saved diagnosis + timeline for a run
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import bq
from ..agents.investigate import investigate
from ..config import pipelines_config
from ..monitoring import run_logger, timeline as timeline_mod

app = FastAPI(title="DataPilot AI")

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class InvestigateRequest(BaseModel):
    run_id: str
    pipeline_name: str
    batch_date: str  # YYYY-MM-DD


@app.get("/")
def index() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(404, "UI not built — see app/static/index.html")
    return FileResponse(index_file)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/pipelines")
def pipeline_health() -> list[dict]:
    """One row per configured pipeline: status of its most recent run."""
    out = []
    for name in pipelines_config()["pipelines"]:
        rows = bq.run_query(
            f"SELECT run_id, batch_date, status, records_processed, failed_task, error_message "
            f"FROM {bq.fq('monitoring', 'pipeline_runs')} WHERE pipeline_name = @p "
            f"ORDER BY start_time DESC LIMIT 1",
            {"p": name},
        )
        out.append({"pipeline_name": name, "latest_run": rows[0] if rows else None})
    return out


@app.get("/pipelines/{pipeline_name}/runs")
def pipeline_runs(pipeline_name: str, limit: int = 10) -> dict:
    if pipeline_name not in pipelines_config()["pipelines"]:
        raise HTTPException(404, f"Unknown pipeline '{pipeline_name}'")
    rows = bq.run_query(
        f"SELECT run_id, batch_date, status, records_processed, failed_task, error_message "
        f"FROM {bq.fq('monitoring', 'pipeline_runs')} WHERE pipeline_name = @p "
        f"ORDER BY start_time DESC LIMIT @n",
        {"p": pipeline_name, "n": max(1, min(limit, 50))},
    )
    return {"pipeline_name": pipeline_name, "runs": rows}


@app.post("/investigate")
async def run_investigation(req: InvestigateRequest) -> dict:
    result = await investigate(req.run_id, req.pipeline_name, req.batch_date)
    if result.get("diagnosis"):
        incident_id = run_logger.save_incident(
            run_id=req.run_id, pipeline_name=req.pipeline_name, diagnosis=result["diagnosis"],
            tool_trace=result["tool_trace"], latency_seconds=result["latency_seconds"], model=result["model"],
        )
        run_logger.attach_audit_incident(req.run_id, incident_id)
        result["incident_id"] = incident_id
    return result


@app.get("/incidents/{run_id}")
def get_incident(run_id: str) -> dict:
    rows = bq.run_query(
        f"SELECT * FROM {bq.fq('monitoring', 'incidents')} WHERE run_id = @r "
        "ORDER BY created_at DESC LIMIT 1",
        {"r": run_id},
    )
    if not rows:
        raise HTTPException(404, f"No incident found for run_id '{run_id}'")
    incident = rows[0]
    return {
        "incident_id": incident["incident_id"],
        "run_id": run_id,
        "diagnosis": incident.get("diagnosis_json"),
        "timeline": timeline_mod.build_timeline(run_id),
    }
