"""WSGI entry point for Gunicorn and other production servers."""

from server import create_app

app = create_app()
