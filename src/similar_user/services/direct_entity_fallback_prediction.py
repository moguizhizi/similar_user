"""Compatibility exports for direct-entity task prediction fallback."""

from __future__ import annotations

from .task_prediction_fallback import (
    DEFAULT_FALLBACK_TASK_TOP_K,
    DirectEntityFallbackPredictionService,
)

__all__ = (
    "DEFAULT_FALLBACK_TASK_TOP_K",
    "DirectEntityFallbackPredictionService",
)
