"""Filesystem layout helpers for source-centered user cache payloads."""

from __future__ import annotations

from pathlib import Path


def files_root_from_sqlite_path(sqlite_path: str | Path) -> Path:
    """Return the payload root next to the SQLite cache index."""
    return Path(sqlite_path).expanduser().parent / "files"


def patient_cache_root(files_root: str | Path, patient_id: object) -> Path:
    """Return the bucketed patient cache root."""
    normalized_patient_id = _normalize_required_text(patient_id, "patient_id")
    return Path(files_root) / "patient" / _bucket(normalized_patient_id) / normalized_patient_id


def raw_source_cache_root(
    files_root: str | Path,
    *,
    source_type: object,
    source_id: object,
    pattern: object,
) -> Path:
    """Return the raw-path root for a patient or direct-entity source."""
    normalized_source_type = _normalize_required_text(source_type, "source_type")
    normalized_source_id = _normalize_required_text(source_id, "source_id")
    if normalized_source_type == "patient":
        return patient_cache_root(files_root, normalized_source_id)
    normalized_pattern = _normalize_required_text(pattern, "pattern")
    source_key = f"{_slug_part(normalized_pattern)}__{_slug_part(normalized_source_id)}"
    return Path(files_root) / "direct_entity_profile" / source_key


def cache_leaf_dir(
    root: str | Path,
    *,
    cache_type: object,
    query_family: object,
    window_days: object,
    config_hash: object,
    cached_base_date: object,
) -> Path:
    """Return the common cache payload leaf directory."""
    normalized_cache_type = _normalize_required_text(cache_type, "cache_type")
    normalized_query_family = _normalize_required_text(query_family, "query_family")
    normalized_config_hash = _normalize_required_text(config_hash, "config_hash")
    normalized_base_date = _normalize_required_text(cached_base_date, "cached_base_date")
    normalized_window_days = _normalize_positive_int(window_days, "window_days")
    return (
        Path(root)
        / normalized_cache_type
        / _slug_part(normalized_query_family)
        / f"window_{normalized_window_days}"
        / f"config_{_slug_part(normalized_config_hash)}"
        / f"base_{_slug_part(normalized_base_date)}"
    )


def source_cache_leaf_dir(
    files_root: str | Path,
    *,
    source_type: object,
    source_id: object,
    pattern: object,
    cache_type: object,
    query_family: object,
    window_days: object,
    config_hash: object,
    cached_base_date: object,
) -> Path:
    """Return a cache leaf rooted by the raw path's source."""
    return cache_leaf_dir(
        raw_source_cache_root(
            files_root,
            source_type=source_type,
            source_id=source_id,
            pattern=pattern,
        ),
        cache_type=cache_type,
        query_family=query_family,
        window_days=window_days,
        config_hash=config_hash,
        cached_base_date=cached_base_date,
    )


def patient_cache_leaf_dir(
    files_root: str | Path,
    *,
    patient_id: object,
    cache_type: object,
    query_family: object,
    window_days: object,
    config_hash: object,
    cached_base_date: object,
) -> Path:
    """Return a cache leaf rooted by the consuming patient/profile ID."""
    return cache_leaf_dir(
        patient_cache_root(files_root, patient_id),
        cache_type=cache_type,
        query_family=query_family,
        window_days=window_days,
        config_hash=config_hash,
        cached_base_date=cached_base_date,
    )


def _bucket(value: str) -> str:
    return _slug_part(value[:2] or "unknown")


def _normalize_required_text(value: object, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _normalize_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _slug_part(value: object) -> str:
    text = str(value).strip().lower()
    slug: list[str] = []
    for char in text:
        if char.isalnum():
            slug.append(char)
        elif char in ("-", "_"):
            slug.append(char)
        else:
            slug.append("-")
    return "".join(slug).strip("-") or "none"
