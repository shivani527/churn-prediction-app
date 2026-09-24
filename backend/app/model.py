"""
Bridges the trained notebook artifacts (churn_model.pkl / selected_cols.pkl)
to the API.

Design notes for anyone reading this in an interview:

1. The feature-building logic here mirrors the notebook's
   `predict_customer()` function exactly: the 12 fields the user actually
   fills in, plus a fixed dict of defaults for every other column the
   model was trained on. That keeps the API's behaviour identical to the
   notebook it came from -- no re-derivation, no drift.

2. `ChurnModel.is_ready` is False until real artifacts are found. Rather
   than crash the whole service when the pickle files are missing (e.g.
   right after cloning the repo, before you've trained anything), the
   API falls back to a transparent, rule-based heuristic and marks every
   response with `demo_mode: true`. That means the full stack -- backend,
   frontend, tests -- is always runnable and demoable, and swapping in a
   real model is a drop-in file copy with zero code changes.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.schemas import ChurnRequest

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_PATH = MODEL_DIR / "churn_model.pkl"
COLUMNS_PATH = MODEL_DIR / "selected_cols.pkl"

RATING_SCALE = ["Strongly agree", "Agree", "Neutral", "Disagree", "Strongly disagree"]
OCCUPATIONS = ["Student", "Employee", "Self Employed", "House wife"]
MONTHLY_INCOMES = [
    "No Income",
    "Below Rs.10000",
    "10001-25000",
    "25001 to 50000",
    "More than 50000",
]

# (request field name) -> (original dataframe column name from the notebook)
RATING_FIELD_MAP: list[tuple[str, str]] = [
    ("ease_and_convenient", "ease and convenient"),
    ("good_food_quality", "good food quality"),
    ("more_offers_and_discount", "more offers and discount"),
    ("good_tracking_system", "good tracking system"),
    ("late_delivery", "late delivery"),
    ("bad_past_experience", "bad past experience"),
    ("wrong_order_delivered", "wrong order delivered"),
    ("unaffordable", "unaffordable"),
    ("long_delivery_time", "long delivery time"),
    ("missing_item", "missing item"),
]

# Every other column the notebook's model was trained on gets a fixed,
# neutral-ish default -- matching predict_customer() in the notebook.
DEFAULTS: dict[str, Any] = {
    "age": 25,
    "gender": "Male",
    "marital status": "Single",
    "educational qualifications": "Graduate",
    "family size": 3,
    "medium (p1)": "Food delivery apps",
    "medium (p2)": "Food delivery apps",
    "meal(p1)": "Dinner",
    "meal(p2)": "Snacks",
    "perference(p1)": "Veg",
    "perference(p2)": "Veg",
    "time saving": "Agree",
    "more restaurant choices": "Agree",
    "easy payment option": "Agree",
    "influence of rating": "Agree",
    "freshness": "Agree",
    "temperature": "Agree",
    "good quantity": "Agree",
    "good road condition": "Agree",
    "self cooking": "Disagree",
    "health concern": "Disagree",
    "poor hygiene": "Disagree",
    "delay of delivery person getting assigned": "Disagree",
    "delay of delivery person picking up food": "Disagree",
    "order placed by mistake": "Disagree",
    "maximum wait time": "30 minutes",
    "number of calls": "No",
}

# Direction each rating field pushes churn risk, used only by the demo
# heuristic below -- derived from the correlation analysis in the notebook
# (e.g. "wrong_order_delivered_Strongly agree" was one of the strongest
# positive correlations with churn; "ease_and_convenient_Strongly agree"
# one of the strongest negative ones).
COMPLAINT_FIELDS = {
    "late_delivery",
    "bad_past_experience",
    "wrong_order_delivered",
    "unaffordable",
    "long_delivery_time",
    "missing_item",
}
POSITIVE_FIELDS = {
    "ease_and_convenient",
    "good_food_quality",
    "more_offers_and_discount",
    "good_tracking_system",
}

_SCALE_WEIGHT = {
    "Strongly agree": 2,
    "Agree": 1,
    "Neutral": 0,
    "Disagree": -1,
    "Strongly disagree": -2,
}


def _risk_level(probability: float) -> str:
    if probability < 0.35:
        return "Low"
    if probability < 0.6:
        return "Moderate"
    if probability < 0.8:
        return "High"
    return "Critical"


class ChurnModel:
    """Wraps the trained model, or a transparent fallback if it isn't present."""

    def __init__(self) -> None:
        self.model = None
        self.selected_cols: list[str] | None = None
        self.is_ready = False
        self._load()

    def _load(self) -> None:
        if MODEL_PATH.exists() and COLUMNS_PATH.exists():
            try:
                self.model = joblib.load(MODEL_PATH)
                self.selected_cols = joblib.load(COLUMNS_PATH)
                self.is_ready = True
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[model] Found artifacts but failed to load them: {exc}")
                self.model = None
                self.selected_cols = None
                self.is_ready = False
        else:
            print(
                "[model] No trained artifacts found in backend/model/ -- "
                "serving predictions from the rule-based demo fallback. "
                "Copy churn_model.pkl and selected_cols.pkl from the notebook "
                "into backend/model/ to use the real model."
            )

    @property
    def feature_count(self) -> int | None:
        return len(self.selected_cols) if self.selected_cols else None

    def predict(self, req: ChurnRequest) -> dict[str, Any]:
        if self.is_ready:
            return self._predict_with_model(req)
        return self._predict_with_heuristic(req)

    # -- real model path -----------------------------------------------

    def _predict_with_model(self, req: ChurnRequest) -> dict[str, Any]:
        row: dict[str, Any] = dict(DEFAULTS)
        row["occupation"] = req.occupation
        row["monthly income"] = req.monthly_income
        for field_name, column_name in RATING_FIELD_MAP:
            row[column_name] = getattr(req, field_name)

        df = pd.DataFrame([row])
        encoded = pd.get_dummies(df)
        aligned = encoded.reindex(columns=self.selected_cols, fill_value=0)

        proba = self.model.predict_proba(aligned)[0]
        churn_probability = float(proba[1])
        return self._package(churn_probability, demo_mode=False)

    # -- fallback path ---------------------------------------------------

    def _predict_with_heuristic(self, req: ChurnRequest) -> dict[str, Any]:
        score = 0.0
        for field_name, _ in RATING_FIELD_MAP:
            weight = _SCALE_WEIGHT[getattr(req, field_name)]
            if field_name in COMPLAINT_FIELDS:
                score += weight
            elif field_name in POSITIVE_FIELDS:
                score -= weight

        # Small, honest nudges from occupation/income -- students and
        # no-income customers skew slightly more price-sensitive in the
        # source data; this is illustrative only, not a fitted effect.
        if req.occupation == "Student":
            score += 0.5
        if req.monthly_income == "No Income":
            score += 0.5
        elif req.monthly_income == "More than 50000":
            score -= 0.5

        # Logistic squashing into a 0..1 probability.
        churn_probability = 1 / (1 + math.exp(-0.35 * score))
        return self._package(churn_probability, demo_mode=True)

    @staticmethod
    def _package(churn_probability: float, demo_mode: bool) -> dict[str, Any]:
        churn_probability = max(0.0, min(1.0, churn_probability))
        return {
            "prediction": "CHURN" if churn_probability >= 0.5 else "LOYAL",
            "churn_probability": round(churn_probability, 4),
            "loyal_probability": round(1 - churn_probability, 4),
            "risk_level": _risk_level(churn_probability),
            "demo_mode": demo_mode,
        }


churn_model = ChurnModel()
