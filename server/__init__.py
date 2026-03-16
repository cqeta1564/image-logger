"""Server package for the Image Logger application."""


def create_app(*args, **kwargs):
    """Import the Flask application factory lazily."""
    from .app import create_app as application_factory

    return application_factory(*args, **kwargs)

__all__ = ["create_app"]
