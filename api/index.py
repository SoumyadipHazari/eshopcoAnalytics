
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import json
import numpy as np
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Ensure q-vercel-latency.json is included in the deployment.
DATA_PATH = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    TELEMETRY_DATA = json.load(f)


@app.get("/")
def root():
    return {"status": "ok"}


@app.options("/api/latency")
async def options_handler():
    return Response(
        status_code=200,
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.post("/api/latency")
async def latency_analytics(request: Request):
    body = await request.json()
    regions = body.get("regions", [])
    threshold_ms = float(body.get("threshold_ms", 180))

    results = []

    for region in regions:
        records = [
            row for row in TELEMETRY_DATA
            if row["region"].lower() == region.lower()
        ]

        if not records:
            continue

        latencies = [float(row["latency_ms"]) for row in records]
        uptimes = [float(row["uptime_pct"]) for row in records]

        results.append({
            "region": region,
            "avg_latency": round(float(np.mean(latencies)), 2),
            "p95_latency": round(float(np.percentile(latencies, 95)), 2),
            "avg_uptime": round(float(np.mean(uptimes)), 3),
            "breaches": int(sum(x > threshold_ms for x in latencies)),
        })

    return {"regions": results}
