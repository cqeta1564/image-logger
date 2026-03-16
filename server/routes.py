"""HTTP routes for the Image Logger server."""

from __future__ import annotations

import hmac
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, InternalServerError, Unauthorized
from werkzeug.utils import secure_filename

from .database import (
    delete_measurement,
    insert_measurement,
    list_measurements,
    ping_database,
)

bp = Blueprint("main", __name__)

DEVICE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def sanitize_device_id(raw_value: str | None) -> str:
    """Normalize a device identifier into a safe filesystem-friendly value."""
    cleaned_value = DEVICE_ID_PATTERN.sub("-", (raw_value or "").strip())
    cleaned_value = cleaned_value.strip("-_")
    return cleaned_value[:64] or "unknown-device"


def sanitize_text(raw_value: str | None, *, default: str, max_length: int) -> str:
    """Strip control characters and collapse extra whitespace."""
    cleaned_value = " ".join((raw_value or "").split())
    cleaned_value = "".join(
        character for character in cleaned_value if character.isprintable()
    )
    cleaned_value = cleaned_value[:max_length].strip()
    return cleaned_value or default


def parse_optional_float(field_name: str) -> float | None:
    """Parse an optional float from a multipart form field."""
    raw_value = (request.form.get(field_name) or "").strip()
    if not raw_value:
        return None

    try:
        parsed_value = float(raw_value)
    except ValueError as error:
        raise BadRequest(f"Field '{field_name}' must be a valid number.") from error

    if not math.isfinite(parsed_value):
        raise BadRequest(f"Field '{field_name}' must be a finite number.")

    if field_name == "humidity" and not 0 <= parsed_value <= 100:
        raise BadRequest("Field 'humidity' must be between 0 and 100.")
    return parsed_value


def validate_uploaded_image(uploaded_file: FileStorage) -> str:
    """Validate the uploaded image content and return the normalized extension."""
    original_name = secure_filename(uploaded_file.filename or "")
    if not original_name:
        raise BadRequest("The uploaded file must include a filename.")

    original_extension = Path(original_name).suffix.lower().lstrip(".")
    if original_extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        allowed_extensions = ", ".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        raise BadRequest(f"Unsupported file type. Allowed types: {allowed_extensions}.")

    try:
        uploaded_file.stream.seek(0)
        with Image.open(uploaded_file.stream) as image:
            image.verify()
            detected_format = (image.format or "").lower()
    except (UnidentifiedImageError, OSError) as error:
        raise BadRequest("Uploaded file is not a valid image.") from error
    finally:
        uploaded_file.stream.seek(0)

    if detected_format not in current_app.config["ALLOWED_IMAGE_FORMATS"]:
        raise BadRequest("Uploaded image format is not supported.")

    return "jpg" if detected_format == "jpeg" else detected_format


def extract_device_token() -> str:
    """Read a device token from either the Authorization header or a custom header."""
    authorization_header = request.headers.get("Authorization", "").strip()
    if authorization_header.lower().startswith("bearer "):
        return authorization_header.split(None, 1)[1].strip()
    return request.headers.get("X-Device-Token", "").strip()


def authenticate_device_request(device_id: str) -> None:
    """Require a valid per-device token when authentication is enabled."""
    if not current_app.config["AUTH_REQUIRED"]:
        return

    expected_token = current_app.config["DEVICE_TOKENS"].get(device_id)
    provided_token = extract_device_token()
    if expected_token and provided_token and hmac.compare_digest(
        provided_token,
        expected_token,
    ):
        return

    current_app.logger.warning(
        "device_authentication_failed",
        extra={
            "structured_data": {
                "device_id": device_id,
                "remote_addr": request.remote_addr,
            }
        },
    )
    raise Unauthorized("Valid device credentials are required for uploads.")


def build_storage_path(device_id: str, file_extension: str) -> tuple[str, Path]:
    """Create a unique, safe destination path inside the configured upload folder."""
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)

    timestamp_label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = secure_filename(
        f"{device_id}_{timestamp_label}_{uuid4().hex[:8]}.{file_extension}"
    )
    destination = (upload_folder / filename).resolve()

    if upload_folder not in destination.parents:
        raise BadRequest("Resolved upload path is invalid.")
    return filename, destination


def json_response(
    *,
    status: str,
    message: str,
    http_status: int,
    data: dict | None = None,
):
    """Return a consistent JSON response payload."""
    payload = {"status": status, "message": message}
    if data:
        payload["data"] = data
    return jsonify(payload), http_status


@bp.get("/")
def index():
    """Render the latest measurements in a simple HTML dashboard."""
    measurements = list_measurements(current_app.config["IMAGE_LIST_LIMIT"])
    return render_template("index.html", measurements=measurements)


@bp.get("/health")
def health():
    """Return a basic health response for probes and monitoring."""
    ping_database()
    return json_response(
        status="success",
        message="Service is healthy",
        http_status=200,
        data={"database": "ok", "timestamp": datetime.now(UTC).isoformat()},
    )


@bp.post("/upload")
def upload():
    """Accept an image upload and store its related sensor metadata."""
    uploaded_file = request.files.get("image")
    if uploaded_file is None:
        raise BadRequest("The request must include an 'image' file.")

    device_id = sanitize_device_id(request.form.get("device_id"))
    authenticate_device_request(device_id)
    sd_health = sanitize_text(
        request.form.get("sd_health"),
        default="unknown",
        max_length=64,
    )
    temperature = parse_optional_float("temperature")
    humidity = parse_optional_float("humidity")
    pressure = parse_optional_float("pressure")

    file_extension = validate_uploaded_image(uploaded_file)
    stored_filename, destination = build_storage_path(device_id, file_extension)
    measurement_timestamp = datetime.now(UTC).isoformat(timespec="seconds")

    try:
        uploaded_file.save(destination)
        measurement = insert_measurement(
            filename=stored_filename,
            timestamp=measurement_timestamp,
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            sd_health=sd_health,
            device_id=device_id,
        )
    except Exception as error:
        if destination.exists():
            destination.unlink()
        raise InternalServerError("Image upload could not be stored.") from error

    current_app.logger.info(
        "upload_completed",
        extra={
            "structured_data": {
                "device_id": measurement.device_id,
                "filename": measurement.filename,
                "timestamp": measurement.timestamp,
                "content_length": request.content_length or 0,
                "remote_addr": request.remote_addr,
            }
        },
    )

    return json_response(
        status="success",
        message="Image uploaded",
        http_status=201,
        data={
            "filename": measurement.filename,
            "device_id": measurement.device_id,
            "timestamp": measurement.timestamp,
        },
    )


@bp.post("/delete/<int:record_id>")
def remove_measurement(record_id: int):
    """Delete a measurement record and its corresponding image file."""
    measurement = delete_measurement(record_id)
    if measurement is None:
        abort(404)

    image_path = Path(current_app.config["UPLOAD_FOLDER"]) / measurement.filename
    if image_path.exists():
        image_path.unlink()

    current_app.logger.info(
        "measurement_deleted",
        extra={
            "structured_data": {
                "record_id": record_id,
                "filename": measurement.filename,
                "device_id": measurement.device_id,
            }
        },
    )
    return redirect(url_for("main.index"))


@bp.get("/images/<path:filename>")
def serve_image(filename: str):
    """Serve a previously uploaded image by its stored filename."""
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        abort(404)

    image_path = Path(current_app.config["UPLOAD_FOLDER"]) / safe_filename
    if not image_path.is_file():
        abort(404)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        safe_filename,
        max_age=60,
    )
