"""
Basic API tests. Run from backend/ with:
    pytest

These pass whether or not the real trained model artifacts are present --
in either case /predict must return a well-formed, schema-valid response.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_LOYAL_LEANING = {
    "occupation": "Employee",
    "monthly_income": "25001 to 50000",
    "ease_and_convenient": "Strongly agree",
    "good_food_quality": "Strongly agree",
    "more_offers_and_discount": "Agree",
    "good_tracking_system": "Strongly agree",
    "late_delivery": "Strongly disagree",
    "bad_past_experience": "Strongly disagree",
    "wrong_order_delivered": "Strongly disagree",
    "unaffordable": "Strongly disagree",
    "long_delivery_time": "Strongly disagree",
    "missing_item": "Strongly disagree",
}

SAMPLE_CHURN_LEANING = {
    "occupation": "Student",
    "monthly_income": "No Income",
    "ease_and_convenient": "Strongly disagree",
    "good_food_quality": "Strongly disagree",
    "more_offers_and_discount": "Strongly disagree",
    "good_tracking_system": "Strongly disagree",
    "late_delivery": "Strongly agree",
    "bad_past_experience": "Strongly agree",
    "wrong_order_delivered": "Strongly agree",
    "unaffordable": "Strongly agree",
    "long_delivery_time": "Strongly agree",
    "missing_item": "Strongly agree",
}


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "model_loaded" in body


def test_options_returns_valid_categories():
    resp = client.get("/options")
    assert resp.status_code == 200
    body = resp.json()
    assert "Employee" in body["occupations"]
    assert len(body["rating_fields"]) == 10
    assert "Strongly agree" in body["rating_scale"]


def test_predict_rejects_invalid_category():
    payload = dict(SAMPLE_LOYAL_LEANING)
    payload["occupation"] = "Astronaut"  # not a trained category
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_loyal_leaning_customer():
    resp = client.post("/predict", json=SAMPLE_LOYAL_LEANING)
    assert resp.status_code == 200
    body = resp.json()
    assert body["prediction"] in ("LOYAL", "CHURN")
    assert 0.0 <= body["churn_probability"] <= 1.0
    assert abs(body["churn_probability"] + body["loyal_probability"] - 1.0) < 1e-6


def test_predict_churn_leaning_customer_scores_higher_risk():
    loyal_resp = client.post("/predict", json=SAMPLE_LOYAL_LEANING).json()
    churn_resp = client.post("/predict", json=SAMPLE_CHURN_LEANING).json()
    # Regardless of demo-mode vs. real model, a customer who agrees with
    # every complaint and disagrees with every positive statement should
    # score a higher churn probability than the opposite customer.
    assert churn_resp["churn_probability"] > loyal_resp["churn_probability"]
