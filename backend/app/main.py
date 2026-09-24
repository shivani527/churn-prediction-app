"""
FastAPI app exposing the churn model.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for the interactive OpenAPI UI,
or serve frontend/index.html and point it at this server.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.model import (
    MONTHLY_INCOMES,
    OCCUPATIONS,
    RATING_FIELD_MAP,
    RATING_SCALE,
    churn_model,
)
from app.schemas import ChurnRequest, ChurnResponse, HealthResponse, OptionsResponse

app = FastAPI(
    title="Food Delivery Churn Prediction API",
    description=(
        "Predicts whether a food-delivery customer is likely to churn, "
        "based on the logistic regression model trained in the companion "
        "notebook. Falls back to a transparent rule-based heuristic if no "
        "trained model artifacts are present."
    ),
    version="1.0.0",
)

# In local dev, ALLOWED_ORIGINS is unset, so we fall back to "*" and any
# frontend on any port can call the API. In production, set the
# ALLOWED_ORIGINS environment variable to a comma-separated list of the
# real frontend origin(s), e.g.:
#   ALLOWED_ORIGINS=https://your-frontend.netlify.app
# This keeps the same code working in both environments with no edits.
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    ["*"] if _allowed_origins_env == "*" else [o.strip() for o in _allowed_origins_env.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "service": "churn-prediction-api",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=churn_model.is_ready,
        demo_mode=not churn_model.is_ready,
        feature_count=churn_model.feature_count,
    )


@app.get("/options", response_model=OptionsResponse, tags=["meta"])
def options() -> OptionsResponse:
    """
    Single source of truth for valid dropdown/rating values, so the
    frontend never has to hardcode (and risk drifting from) categories
    the model was actually trained on.
    """
    return OptionsResponse(
        occupations=OCCUPATIONS,
        monthly_incomes=MONTHLY_INCOMES,
        rating_scale=RATING_SCALE,
        rating_fields=[
            {"field": field_name, "label": column_name}
            for field_name, column_name in RATING_FIELD_MAP
        ],
    )


@app.post("/predict", response_model=ChurnResponse, tags=["prediction"])
def predict(request: ChurnRequest) -> ChurnResponse:
    result = churn_model.predict(request)
    return ChurnResponse(**result)
