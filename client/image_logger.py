#!/usr/bin/env python3
"""Upload Raspberry Pi images and sensor readings to the Flask server."""

from __future__ import annotations

import argparse
import logging
import mimetypes
import os
from pathlib import Path

import requests

LOGGER = logging.getLogger("image_logger_client")


def configure_logging() -> None:
    """Configure readable console logging for the client script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the uploader."""
    parser = argparse.ArgumentParser(
        description=(
            "Upload an image and optional sensor data to an Image Logger server."
        )
    )
    parser.add_argument(
        "--server-url",
        default=os.getenv("IMAGE_LOGGER_SERVER_URL", "http://127.0.0.1:8080"),
        help="Base URL of the Flask server.",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the image file that should be uploaded.",
    )
    parser.add_argument(
        "--device-id",
        default=os.getenv("IMAGE_LOGGER_DEVICE_ID", "rpi01"),
        help="Identifier for the Raspberry Pi device.",
    )
    parser.add_argument(
        "--device-token",
        default=os.getenv("IMAGE_LOGGER_DEVICE_TOKEN", ""),
        help=(
            "Optional bearer token used when server-side device authentication "
            "is enabled."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Temperature in degrees Celsius.",
    )
    parser.add_argument("--humidity", type=float, help="Relative humidity percentage.")
    parser.add_argument("--pressure", type=float, help="Pressure in hPa.")
    parser.add_argument(
        "--sd-health",
        default=os.getenv("IMAGE_LOGGER_SD_HEALTH", "unknown"),
        help="Human-readable SD card health state.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("IMAGE_LOGGER_HTTP_TIMEOUT", "30")),
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def build_payload(arguments: argparse.Namespace) -> dict[str, str]:
    """Build the multipart form fields for the upload request."""
    payload = {
        "device_id": arguments.device_id,
        "sd_health": arguments.sd_health,
    }

    for field_name in ("temperature", "humidity", "pressure"):
        field_value = getattr(arguments, field_name)
        if field_value is not None:
            payload[field_name] = str(field_value)
    return payload


def build_headers(arguments: argparse.Namespace) -> dict[str, str]:
    """Build optional authentication headers for the upload request."""
    if not arguments.device_token:
        return {}
    return {"Authorization": f"Bearer {arguments.device_token}"}


def upload_measurement(arguments: argparse.Namespace) -> int:
    """Upload one image and return a process exit code."""
    image_path = Path(arguments.image).expanduser().resolve()
    if not image_path.is_file():
        LOGGER.error("Image file does not exist: %s", image_path)
        return 1

    server_url = arguments.server_url.rstrip("/")
    upload_url = f"{server_url}/upload"
    payload = build_payload(arguments)
    headers = build_headers(arguments)
    mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"

    try:
        with image_path.open("rb") as image_file:
            response = requests.post(
                upload_url,
                data=payload,
                headers=headers,
                files={"image": (image_path.name, image_file, mime_type)},
                timeout=arguments.timeout,
            )
        response.raise_for_status()
    except requests.RequestException as error:
        LOGGER.error("Upload failed: %s", error)
        return 1

    try:
        response_payload = response.json()
    except ValueError:
        LOGGER.error("Server returned a non-JSON response.")
        return 1

    LOGGER.info("Upload result: %s", response_payload)
    return 0


def main() -> int:
    """Run the uploader CLI."""
    configure_logging()
    arguments = parse_arguments()
    return upload_measurement(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
