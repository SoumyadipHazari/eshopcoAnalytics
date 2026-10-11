
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    telemetry = json.load(f)


class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float = 180


def percentile95(values):
    values = sorted(values)
    if len(values) == 1:
        return values[0]

    position = 0.95 * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)

    return (
        values[lower]
        + (position - lower) * (values[upper] - values[lower])
    )


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/")
def analytics(request: AnalyticsRequest):
    results = {}

    for region in request.regions:
        rows = [
            row for row in telemetry
            if row["region"].lower() == region.lower()
        ]

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No telemetry records found for region: {region}",
            )

        latencies = [float(row["latency_ms"]) for row in rows]

        # The actual dataset field is uptime_pct, not uptime.
        uptimes = [float(row["uptime_pct"]) for row in rows]

        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                latency > request.threshold_ms
                for latency in latencies
            ),
        }

    return results
