"""Basic application tests for the Image Logger server."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from server.app import create_app
from server.config import Config

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


class AppTests(unittest.TestCase):
    """Verify the core server flows work with temporary storage."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp_dir.name)
        self.temp_root = temp_root

        self.app = self.create_test_app()
        self.client = self.app.test_client()
        self.upload_folder = Path(self.app.config["UPLOAD_FOLDER"])

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_test_app(self, **overrides):
        """Create an application instance with isolated temporary storage."""

        class TestConfig(Config):
            DATABASE_PATH = self.temp_root / "test.db"
            UPLOAD_FOLDER = self.temp_root / "images"
            MAX_CONTENT_LENGTH = 1024 * 1024
            AUTH_REQUIRED = False
            DEVICE_TOKENS = {}
            ENABLE_PROXY_FIX = False

        for setting_name, setting_value in overrides.items():
            setattr(TestConfig, setting_name, setting_value)
        return create_app(TestConfig)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["database"], "ok")

    def test_upload_and_dashboard_render(self) -> None:
        response = self.client.post(
            "/upload",
            data={
                "device_id": "rpi-main",
                "temperature": "21.5",
                "humidity": "48.2",
                "pressure": "1012.3",
                "sd_health": "healthy",
                "image": (io.BytesIO(PNG_BYTES), "capture.png"),
            },
            content_type="multipart/form-data",
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(list(self.upload_folder.iterdir())), 1)

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"rpi-main", dashboard.data)

    def test_upload_rejects_invalid_humidity(self) -> None:
        response = self.client.post(
            "/upload",
            data={
                "device_id": "rpi-main",
                "humidity": "120",
                "image": (io.BytesIO(PNG_BYTES), "capture.png"),
            },
            content_type="multipart/form-data",
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")

    def test_upload_requires_device_token_when_auth_enabled(self) -> None:
        secure_app = self.create_test_app(
            AUTH_REQUIRED=True,
            DEVICE_TOKENS={"rpi-main": "secret-token"},
        )
        secure_client = secure_app.test_client()

        response = secure_client.post(
            "/upload",
            data={
                "device_id": "rpi-main",
                "image": (io.BytesIO(PNG_BYTES), "capture.png"),
            },
            content_type="multipart/form-data",
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload["status"], "error")

    def test_upload_accepts_valid_device_token(self) -> None:
        secure_app = self.create_test_app(
            AUTH_REQUIRED=True,
            DEVICE_TOKENS={"rpi-main": "secret-token"},
        )
        secure_client = secure_app.test_client()

        response = secure_client.post(
            "/upload",
            data={
                "device_id": "rpi-main",
                "image": (io.BytesIO(PNG_BYTES), "capture.png"),
            },
            headers={"Authorization": "Bearer secret-token"},
            content_type="multipart/form-data",
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["status"], "success")


if __name__ == "__main__":
    unittest.main()
