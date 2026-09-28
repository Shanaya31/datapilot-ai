"""Builds the incident timeline shown in the UI from monitoring tables (no LLM needed)."""
from __future__ import annotations

from .. import bq


def build_timeline(run_id: str) -> list[dict]:
    run = bq.run_query(
        f"SELECT * FROM {bq.fq('monitoring', 'pipeline_runs')} WHERE run_id = @r LIMIT 1", {"r": run_id}
    )
    tasks = bq.run_query(
        f"SELECT task_id, state, end_time, error_message FROM {bq.fq('monitoring', 'task_events')} "
        "WHERE run_id = @r ORDER BY end_time", {"r": run_id},
    )
    dq = bq.run_query(
        f"SELECT check_name, column_name, detail, checked_at FROM {bq.fq('monitoring', 'dq_results')} "
        "WHERE run_id = @r AND NOT passed ORDER BY checked_at", {"r": run_id},
    )
    inc = bq.run_query(
        f"SELECT created_at, latency_seconds FROM {bq.fq('monitoring', 'incidents')} "
        "WHERE run_id = @r ORDER BY created_at DESC LIMIT 1", {"r": run_id},
    )

    events: list[dict] = []
    if run:
        events.append({"time": run[0]["start_time"], "text": f"Pipeline {run[0]['pipeline_name']} started"})
    for t in tasks:
        label = "completed" if t["state"] == "success" else "FAILED"
        text = f"Task {t['task_id']} {label}"
        if t["state"] == "failed" and t["error_message"]:
            text += f": {t['error_message'][:200]}"
        events.append({"time": t["end_time"], "text": text})
    for d in dq:
        events.append({"time": d["checked_at"], "text": f"Check failed — {d['detail']}"})
    if run and run[0]["end_time"]:
        events.append({"time": run[0]["end_time"], "text": f"Pipeline stopped with status {run[0]['status']}"})
    if inc:
        events.append({"time": inc[0]["created_at"], "text": f"AI investigation finished in {inc[0]['latency_seconds']:.1f}s"})

    events.sort(key=lambda e: e["time"] or 0)
    for e in events:
        e["time"] = e["time"].isoformat() if e["time"] else None
    return events
