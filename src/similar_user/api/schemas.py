"""Request and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExternalTrainingTaskPredictRequest(BaseModel):
    """External module payload for single-user task prediction."""

    group: str | None = None
    age: int | str | None = None
    sex: int | str | None = None
    education: int | str | None = None
    user_id: int | str
    sicksName: list[str] = Field(default_factory=list)
    ba: list[float] = Field(default_factory=list)
    unlock_train: dict[str, int | float] = Field(default_factory=dict)
    pre_tt_list: list[list[int | str]] = Field(default_factory=list)
    second_ba_id: int | str | None = None
    second_ba_name: str | None = None
    train_ctn: int | float | None = None
    pre_score_ba: list[float] = Field(default_factory=list)
    behavior_data: dict[str, Any] = Field(default_factory=dict)

    disease_ids: list[str] = Field(default_factory=list)
    symptom_ids: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
