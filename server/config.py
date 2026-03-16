"""Application configuration values."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

DEVICE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def _read_bool(value: str | None, *, default: bool = False) -> bool:
    """Convert a string environment value into a boolean."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_device_id(raw_value: str) -> str:
    """Normalize device IDs used in configuration maps."""
    cleaned_value = DEVICE_ID_PATTERN.sub("-", raw_value.strip())
    return cleaned_value.strip("-_")[:64]


def _load_device_tokens() -> dict[str, str]:
    """Load optional device tokens from an environment variable or JSON file."""
    tokens_file = os.getenv("IMAGE_LOGGER_DEVICE_TOKENS_FILE", "").strip()
    tokens_json = os.getenv("IMAGE_LOGGER_DEVICE_TOKENS_JSON", "").strip()

    if tokens_file:
        raw_tokens = json.loads(
            Path(tokens_file).expanduser().read_text(encoding="utf-8")
        )
    elif tokens_json:
        raw_tokens = json.loads(tokens_json)
    else:
        return {}

    if not isinstance(raw_tokens, dict):
        raise ValueError("Device tokens must be defined as a JSON object.")

    normalized_tokens: dict[str, str] = {}
    for raw_device_id, raw_token in raw_tokens.items():
        device_id = _sanitize_device_id(str(raw_device_id))
        token = raw_token.strip() if isinstance(raw_token, str) else ""
        if not device_id or not token:
            raise ValueError(
                "Each configured device token must contain a valid device ID "
                "and token."
            )
        normalized_tokens[device_id] = token
    return normalized_tokens


class Config:
    """Default Flask configuration for the Image Logger service."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATABASE_PATH = Path(
        os.getenv("IMAGE_LOGGER_DATABASE_PATH", PROJECT_ROOT / "database.db")
    ).resolve()
    UPLOAD_FOLDER = Path(
        os.getenv("IMAGE_LOGGER_UPLOAD_FOLDER", PROJECT_ROOT / "images")
    ).resolve()
    MAX_CONTENT_LENGTH = int(
        os.getenv("IMAGE_LOGGER_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    )
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    ALLOWED_IMAGE_FORMATS = {"jpeg", "png"}
    IMAGE_LIST_LIMIT = int(os.getenv("IMAGE_LOGGER_IMAGE_LIST_LIMIT", "100"))
    SERVER_HOST = os.getenv("IMAGE_LOGGER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("IMAGE_LOGGER_PORT", "8080"))
    AUTH_REQUIRED = _read_bool(os.getenv("IMAGE_LOGGER_AUTH_REQUIRED"), default=False)
    DEVICE_TOKENS = _load_device_tokens()
    ENABLE_PROXY_FIX = _read_bool(
        os.getenv("IMAGE_LOGGER_ENABLE_PROXY_FIX"),
        default=False,
    )
    PROXY_FIX_X_FOR = int(os.getenv("IMAGE_LOGGER_PROXY_FIX_X_FOR", "1"))
    PROXY_FIX_X_PROTO = int(os.getenv("IMAGE_LOGGER_PROXY_FIX_X_PROTO", "1"))
    PROXY_FIX_X_HOST = int(os.getenv("IMAGE_LOGGER_PROXY_FIX_X_HOST", "1"))
    PROXY_FIX_X_PORT = int(os.getenv("IMAGE_LOGGER_PROXY_FIX_X_PORT", "1"))
    PROXY_FIX_X_PREFIX = int(os.getenv("IMAGE_LOGGER_PROXY_FIX_X_PREFIX", "1"))
