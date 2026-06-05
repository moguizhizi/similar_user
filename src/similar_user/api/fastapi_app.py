"""FastAPI entrypoint for external training-task prediction."""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path
import threading
from typing import Any

from fastapi import FastAPI, HTTPException

from config.settings import DEFAULT_CONFIG_PATH, load_yaml_config
from scripts.predict_training_tasks_unified import predict_training_tasks_unified

from .app import build_neo4j_health_payload
from .cache_cleanup_scheduler import run_user_cache_cleanup_daily
from .cache_refresh_scheduler import run_user_cache_refresh_jobs_daily
from .external_task_prediction import (
    build_external_prediction_response,
    build_unified_prediction_input,
)
from .schemas import ExternalTrainingTaskPredictRequest


DEFAULT_MAX_CONCURRENT_PREDICTIONS = 4
CONFIG_PATH = DEFAULT_CONFIG_PATH


def _load_max_concurrent_predictions(config_path: str | Path) -> int:
    try:
        data = load_yaml_config(config_path)
    except Exception:
        return DEFAULT_MAX_CONCURRENT_PREDICTIONS

    api_data = data.get("api")
    if not isinstance(api_data, dict):
        return DEFAULT_MAX_CONCURRENT_PREDICTIONS
    value = api_data.get(
        "max_concurrent_predictions",
        DEFAULT_MAX_CONCURRENT_PREDICTIONS,
    )
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return DEFAULT_MAX_CONCURRENT_PREDICTIONS
    return value


_prediction_semaphore = threading.BoundedSemaphore(
    _load_max_concurrent_predictions(CONFIG_PATH)
)

app = FastAPI(title="similar_user API")


@app.on_event("startup")
async def startup_cache_cleanup() -> None:
    """Start user-cache background loops for this worker."""
    app.state.user_cache_cleanup_task = asyncio.create_task(
        run_user_cache_cleanup_daily(CONFIG_PATH)
    )
    app.state.user_cache_refresh_task = asyncio.create_task(
        run_user_cache_refresh_jobs_daily(CONFIG_PATH)
    )


@app.on_event("shutdown")
async def shutdown_cache_cleanup() -> None:
    """Cancel user-cache background loops during app shutdown."""
    for task_name in ("user_cache_cleanup_task", "user_cache_refresh_task"):
        task = getattr(app.state, task_name, None)
        if task is None:
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight process health payload."""
    return {"status": "ok"}


@app.get("/health/neo4j")
def neo4j_health() -> dict[str, Any]:
    """Return Neo4j reachability using the existing health implementation."""
    payload, status = build_neo4j_health_payload(CONFIG_PATH)
    if status != HTTPStatus.OK:
        raise HTTPException(status_code=status.value, detail=payload)
    return payload


@app.post("/training-task/predict")
def predict_training_task(
    request: ExternalTrainingTaskPredictRequest,
) -> dict[str, Any]:
    """Predict training tasks for one external user request."""
    payload = (
        request.model_dump()
        if hasattr(request, "model_dump")
        else request.dict()
    )
    try:
        prediction_input = build_unified_prediction_input(
            payload,
            config_path=CONFIG_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        with _prediction_semaphore:
            result = predict_training_tasks_unified(
                patient_id=prediction_input.patient_id,
                base_date=prediction_input.base_date,
                config_path=prediction_input.config_path,
                query_family=prediction_input.query_family,
                age=prediction_input.age,
                education=prediction_input.education,
                gender=prediction_input.gender,
                disease_ids=prediction_input.disease_ids,
                disease_names=prediction_input.disease_names,
                symptom_ids=prediction_input.symptom_ids,
                unknown_ids=prediction_input.unknown_ids,
                task_top_k=prediction_input.task_top_k,
                use_llm=prediction_input.use_llm,
                include_prompt=prediction_input.include_prompt,
            )
            response_payload = build_external_prediction_response(
                result,
                source_payload=payload,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return response_payload
