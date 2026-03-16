# Image Logger

Image Logger is a lightweight distributed webcam monitoring project for Raspberry Pi devices. Each device uploads captured images and environmental measurements to a Flask server, which stores metadata in SQLite, saves images locally, and exposes a simple web dashboard.

## Features

- Secure multipart image uploads over HTTP
- SQLite-backed storage for image metadata and sensor readings
- Local image storage with safe generated filenames
- Web dashboard for recent uploads
- Health endpoint for probes and uptime checks
- Optional per-device bearer-token authentication
- Structured JSON logging for uploads and requests
- GitHub Actions CI for linting and tests
- Gunicorn and reverse-proxy deployment examples

## Project Structure

```text
image-logger/
├── client/
│   └── image_logger.py
├── images/
│   └── .gitkeep
├── server/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes.py
│   └── schema.sql
├── static/
│   └── style.css
├── templates/
│   ├── error.html
│   └── index.html
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── deploy/
│   ├── gunicorn.conf.py
│   ├── image-logger.service
│   └── nginx-image-logger.conf
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── tests/
│   └── test_app.py
└── wsgi.py
```

## Requirements

- Python 3.11+
- A writable local filesystem for `images/` and `database.db`

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install development tooling:

```bash
pip install -r requirements-dev.txt
```

## Running the Server

Start the Flask server from the project root:

```bash
python -m server.app
```

Configuration is controlled through environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `IMAGE_LOGGER_DATABASE_PATH` | `./database.db` | SQLite database location |
| `IMAGE_LOGGER_UPLOAD_FOLDER` | `./images` | Directory for uploaded images |
| `IMAGE_LOGGER_MAX_UPLOAD_SIZE` | `10485760` | Maximum upload size in bytes |
| `IMAGE_LOGGER_HOST` | `0.0.0.0` | Server bind host |
| `IMAGE_LOGGER_PORT` | `8080` | Server port |
| `IMAGE_LOGGER_IMAGE_LIST_LIMIT` | `100` | Number of records shown on the dashboard |
| `IMAGE_LOGGER_AUTH_REQUIRED` | `false` | Require a valid device token for uploads |
| `IMAGE_LOGGER_DEVICE_TOKENS_JSON` | unset | JSON mapping of device IDs to tokens |
| `IMAGE_LOGGER_DEVICE_TOKENS_FILE` | unset | Path to a JSON file containing device tokens |
| `IMAGE_LOGGER_ENABLE_PROXY_FIX` | `false` | Trust reverse-proxy forwarding headers |

## Upload API

`POST /upload`

Multipart form fields:

- `image` (required): JPEG or PNG image file
- `device_id` (optional): Raspberry Pi identifier
- `temperature` (optional): floating-point value
- `humidity` (optional): floating-point value from 0 to 100
- `pressure` (optional): floating-point value
- `sd_health` (optional): short free-form health description

Headers:

- `Authorization: Bearer <token>` or `X-Device-Token: <token>` when authentication is enabled

Example response:

```json
{
  "status": "success",
  "message": "Image uploaded",
  "data": {
    "filename": "rpi01_20260316T120000Z_abcd1234.jpg",
    "device_id": "rpi01",
    "timestamp": "2026-03-16T12:00:00+00:00"
  }
}
```

Example upload with `curl`:

```bash
curl -X POST http://127.0.0.1:8080/upload \
  -H "Authorization: Bearer your-device-token" \
  -F "image=@/path/to/image.jpg" \
  -F "device_id=rpi01" \
  -F "temperature=21.5" \
  -F "humidity=48.2" \
  -F "pressure=1012.3" \
  -F "sd_health=healthy"
```

## Health Endpoint

`GET /health`

Returns a simple JSON payload confirming that the application and database are reachable.

## Raspberry Pi Client

The client uploader sends an existing image file and optional sensor metadata:

```bash
python client/image_logger.py \
  --server-url http://127.0.0.1:8080 \
  --image ./capture.jpg \
  --device-id rpi01 \
  --device-token your-device-token \
  --temperature 21.5 \
  --humidity 48.2 \
  --pressure 1012.3 \
  --sd-health healthy
```

## Device Authentication

Enable per-device authentication by setting `IMAGE_LOGGER_AUTH_REQUIRED=true` and supplying a token map:

```bash
export IMAGE_LOGGER_AUTH_REQUIRED=true
export IMAGE_LOGGER_DEVICE_TOKENS_JSON='{"rpi01":"replace-this-token","rpi02":"replace-this-token-too"}'
python -m server.app
```

For production, prefer `IMAGE_LOGGER_DEVICE_TOKENS_FILE` pointing to a root-readable JSON file outside the repository.

## Security Notes

- Uploads are capped using Flask's `MAX_CONTENT_LENGTH`
- Filenames are generated server-side to avoid path traversal
- Uploaded files are verified with Pillow before saving
- All SQLite writes use parameterized queries
- Device tokens are compared with constant-time checks when authentication is enabled

## Running Tests

Run the basic regression suite from the project root:

```bash
python -m unittest discover -s tests
```

Run lint checks:

```bash
ruff check .
```

GitHub Actions runs both checks with the workflow at `.github/workflows/ci.yml`.

## Production Deployment

Use Gunicorn as the WSGI server and place Nginx in front of it:

```bash
export IMAGE_LOGGER_AUTH_REQUIRED=true
export IMAGE_LOGGER_DEVICE_TOKENS_FILE=/etc/image-logger/device-tokens.json
export IMAGE_LOGGER_ENABLE_PROXY_FIX=true
gunicorn --config deploy/gunicorn.conf.py wsgi:app
```

Deployment examples are included in:

- `deploy/gunicorn.conf.py`
- `deploy/image-logger.service`
- `deploy/nginx-image-logger.conf`

## Recommended Next Steps

- Add TLS termination and certificate renewal for the reverse proxy
- Replace static device tokens with short-lived signed credentials if the network model becomes more hostile
- Add coverage reporting and release automation once the public repository is live
