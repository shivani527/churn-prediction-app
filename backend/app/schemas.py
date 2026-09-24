"""
Request/response contracts for the churn-prediction API.

Using Literal types (instead of bare `str`) means FastAPI/Pydantic reject
any value that isn't one of the exact categories the model was trained on,
*before* the request ever reaches the model. That validation is documented
automatically in the OpenAPI schema (visible at /docs), so the frontend
and the model can never silently drift out of sync.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RatingScale = Literal[
    "Strongly agree",
    "Agree",
    "Neutral",
    "Disagree",
    "Strongly disagree",
]

Occupation = Literal["Student", "Employee", "Self Employed", "House wife"]

MonthlyIncome = Literal[
    "No Income",
    "Below Rs.10000",
    "10001-25000",
    "25001 to 50000",
    "More than 50000",
]


class ChurnRequest(BaseModel):
    occupation: Occupation = Field(..., description="Customer's occupation")
    monthly_income: MonthlyIncome = Field(..., description="Monthly income bracket")

    ease_and_convenient: RatingScale = Field(
        ..., description="Agreement: the app is easy and convenient to use"
    )
    good_food_quality: RatingScale = Field(
        ..., description="Agreement: food quality has been good"
    )
    more_offers_and_discount: RatingScale = Field(
        ..., description="Agreement: offers/discounts are a draw"
    )
    good_tracking_system: RatingScale = Field(
        ..., description="Agreement: order tracking works well"
    )
    late_delivery: RatingScale = Field(
        ..., description="Agreement: deliveries have arrived late"
    )
    bad_past_experience: RatingScale = Field(
        ..., description="Agreement: customer has had a bad past experience"
    )
    wrong_order_delivered: RatingScale = Field(
        ..., description="Agreement: wrong orders have been delivered"
    )
    unaffordable: RatingScale = Field(
        ..., description="Agreement: the service feels unaffordable"
    )
    long_delivery_time: RatingScale = Field(
        ..., description="Agreement: delivery times are too long"
    )
    missing_item: RatingScale = Field(
        ..., description="Agreement: items have gone missing from orders"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "occupation": "Employee",
                "monthly_income": "25001 to 50000",
                "ease_and_convenient": "Agree",
                "good_food_quality": "Agree",
                "more_offers_and_discount": "Neutral",
                "good_tracking_system": "Agree",
                "late_delivery": "Disagree",
                "bad_past_experience": "Disagree",
                "wrong_order_delivered": "Strongly disagree",
                "unaffordable": "Disagree",
                "long_delivery_time": "Disagree",
                "missing_item": "Strongly disagree",
            }
        }
    )


class ChurnResponse(BaseModel):
    prediction: Literal["CHURN", "LOYAL"]
    churn_probability: float = Field(..., ge=0.0, le=1.0)
    loyal_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: Literal["Low", "Moderate", "High", "Critical"]
    demo_mode: bool = Field(
        ..., description="True if served by the rule-based fallback, not the trained model"
    )


class OptionsResponse(BaseModel):
    occupations: list[str]
    monthly_incomes: list[str]
    rating_scale: list[str]
    rating_fields: list[dict[str, str]]


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"]
    model_loaded: bool
    demo_mode: bool
    feature_count: int | None
