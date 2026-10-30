"""API REST de inspección de botellas de 600ml.

La decisión combina dos capas:
  1. Regla de especificación: 600 ml +/- 2 % (588-612 ml) y etiqueta presente.
  2. Modelo XGBoost con el umbral guardado en model/model_metadata.json.

Una botella se rechaza si cualquiera de las dos capas lo indica. La regla es
necesaria porque el dataset no tiene ejemplos cerca de 588 y 612 ml, y con su
umbral el modelo por sí solo acepta defectos de llenado
(ver docs/evidencia/evaluacion_modelo.txt).
"""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import List, Literal

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "model" / "xgb_model.joblib"
METADATA_PATH = ROOT / "model" / "model_metadata.json"
FRONTEND_DIR = ROOT / "frontend"

FILL_MIN_ML = 588.0
FILL_MAX_ML = 612.0

logger = logging.getLogger("uvicorn.error")
state = {"model": None, "metadata": None}


class BottleInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"fill_level_ml": 598.5, "label_present_num": 1}]},
    )

    fill_level_ml: float = Field(ge=0, le=2000, allow_inf_nan=False, description="Nivel de llenado en ml")
    label_present_num: Literal[0, 1] = Field(description="1 = etiqueta presente, 0 = sin etiqueta")


class PredictionOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ACEPTADO", "RECHAZADO"]
    target: Literal[0, 1]
    probability_reject: float
    threshold: float
    rule_rejected: bool
    model_rejected: bool
    rejection_reasons: List[str]
    model_version: str
    inference_ms: float


def spec_reasons(bottle: BottleInput) -> List[str]:
    reasons = []
    if bottle.fill_level_ml < FILL_MIN_ML:
        reasons.append("BAJO_LLENADO")
    elif bottle.fill_level_ml > FILL_MAX_ML:
        reasons.append("ALTO_LLENADO")
    if bottle.label_present_num == 0:
        reasons.append("SIN_ETIQUETA")
    return reasons


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        model = joblib.load(MODEL_PATH)
        model.set_params(n_jobs=1)
        state["model"] = model
        state["metadata"] = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("No se pudo cargar el modelo: %s", exc)
    yield
    state["model"] = None
    state["metadata"] = None


app = FastAPI(
    title="Inspección de Botellas 600ml",
    description="Clasifica botellas como ACEPTADO o RECHAZADO por nivel de llenado y etiqueta.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_: Request, exc: RequestValidationError):
    # Sin el campo "input": un NaN recibido no se puede serializar de vuelta a JSON
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health():
    loaded = state["model"] is not None
    return JSONResponse(
        status_code=200 if loaded else 503,
        content={"status": "healthy" if loaded else "unhealthy", "model_loaded": loaded},
    )


@app.post("/predict", response_model=PredictionOutput)
def predict(bottle: BottleInput):
    model, metadata = state["model"], state["metadata"]
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")

    start = perf_counter()
    features = np.array([[bottle.fill_level_ml, bottle.label_present_num]], dtype=float)
    probability = float(model.predict_proba(features)[0, 1])
    threshold = metadata["threshold"]
    reasons = spec_reasons(bottle)
    rule_rejected = bool(reasons)
    model_rejected = probability >= threshold
    if model_rejected and not rule_rejected:
        reasons.append("ALERTA_MODELO")
    rejected = rule_rejected or model_rejected
    elapsed_ms = (perf_counter() - start) * 1000

    logger.info(
        "inspeccion status=%s fill=%s label=%s p=%.6f",
        "RECHAZADO" if rejected else "ACEPTADO",
        bottle.fill_level_ml,
        bottle.label_present_num,
        probability,
    )
    return PredictionOutput(
        status="RECHAZADO" if rejected else "ACEPTADO",
        target=1 if rejected else 0,
        probability_reject=round(probability, 6),
        threshold=threshold,
        rule_rejected=rule_rejected,
        model_rejected=model_rejected,
        rejection_reasons=reasons,
        model_version=metadata["model_version"],
        inference_ms=round(elapsed_ms, 3),
    )


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
