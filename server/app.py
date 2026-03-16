"""Flask application factory for the Image Logger server."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from time import perf_counter

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .database import init_app as init_database
from .routes import bp


class JsonLogFormatter(logging.Formatter):
    """Serialize application log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        structured_data = getattr(record, "structured_data", None)
        if structured_data:
            payload.update(structured_data)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(app: Flask) -> None:
    """Apply JSON logging to the Flask application and the root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    app.logger.handlers.clear()
    app.logger.propagate = True


def configure_proxy_support(app: Flask) -> None:
    """Respect reverse-proxy forwarding headers when explicitly enabled."""
    if not app.config["ENABLE_PROXY_FIX"]:
        return

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=app.config["PROXY_FIX_X_FOR"],
        x_proto=app.config["PROXY_FIX_X_PROTO"],
        x_host=app.config["PROXY_FIX_X_HOST"],
        x_port=app.config["PROXY_FIX_X_PORT"],
        x_prefix=app.config["PROXY_FIX_X_PREFIX"],
    )


def wants_json_error() -> bool:
    """Decide whether the current request expects a JSON error response."""
    return request.path.startswith("/upload") or request.path.startswith("/health") or (
        request.accept_mimetypes.best == "application/json"
    )


def register_request_logging(app: Flask) -> None:
    """Log request start/end timing for observability."""

    @app.before_request
    def start_request_timer() -> None:
        g.request_started_at = perf_counter()

    @app.after_request
    def log_request(response):
        started_at = g.get("request_started_at", perf_counter())
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        app.logger.info(
            "request_completed",
            extra={
                "structured_data": {
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "remote_addr": request.remote_addr,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response


def register_error_handlers(app: Flask) -> None:
    """Register API and HTML error handlers."""

    def render_error(status_code: int, message: str):
        if wants_json_error():
            return jsonify({"status": "error", "message": message}), status_code
        return (
            render_template(
                "error.html",
                status_code=status_code,
                message=message,
            ),
            status_code,
        )

    @app.errorhandler(BadRequest)
    def handle_bad_request(error: BadRequest):
        return render_error(400, error.description or "Bad request.")

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(_: RequestEntityTooLarge):
        return render_error(413, "Uploaded file is too large.")

    @app.errorhandler(404)
    def handle_not_found(_: HTTPException):
        return render_error(404, "Requested resource was not found.")

    @app.errorhandler(Exception)
    def handle_internal_error(error: Exception):
        if isinstance(error, HTTPException):
            return render_error(error.code or 500, error.description)

        app.logger.exception("unhandled_exception")
        return render_error(500, "Internal server error.")


def create_app(config_object: type[Config] = Config) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(
        "image_logger_server",
        template_folder=str(config_object.PROJECT_ROOT / "templates"),
        static_folder=str(config_object.PROJECT_ROOT / "static"),
    )
    app.config.from_object(config_object)

    if app.config["AUTH_REQUIRED"] and not app.config["DEVICE_TOKENS"]:
        raise RuntimeError(
            "Device authentication is enabled, but no device tokens are configured."
        )

    config_object.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    configure_logging(app)
    configure_proxy_support(app)
    init_database(app)
    app.register_blueprint(bp)
    register_request_logging(app)
    register_error_handlers(app)

    return app


def main() -> None:
    """Run the Flask development server."""
    app = create_app()
    app.run(
        host=app.config["SERVER_HOST"],
        port=app.config["SERVER_PORT"],
        debug=False,
    )


if __name__ == "__main__":
    main()
