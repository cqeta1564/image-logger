"""SQLite helpers for the Image Logger server."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

from .models import Measurement

MEASUREMENT_COLUMNS = """
    id,
    filename,
    timestamp,
    temperature,
    humidity,
    pressure,
    sd_health,
    device_id
"""


def get_db() -> sqlite3.Connection:
    """Return a request-scoped SQLite connection."""
    connection = g.get("db_connection")
    if connection is None:
        connection = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db_connection = connection
    return connection


def close_db(_: BaseException | None = None) -> None:
    """Close the request-scoped database connection."""
    connection = g.pop("db_connection", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create the SQLite database schema if it does not already exist."""
    database_path = Path(current_app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.commit()

    current_app.logger.info(
        "database_initialized",
        extra={"structured_data": {"database_path": str(database_path)}},
    )


def init_app(app) -> None:
    """Register database lifecycle hooks with Flask."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()


def insert_measurement(
    *,
    filename: str,
    timestamp: str,
    temperature: float | None,
    humidity: float | None,
    pressure: float | None,
    sd_health: str,
    device_id: str,
) -> Measurement:
    """Insert a new measurement row and return the stored record."""
    connection = get_db()
    cursor = connection.execute(
        """
        INSERT INTO measurements (
            filename,
            timestamp,
            temperature,
            humidity,
            pressure,
            sd_health,
            device_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (filename, timestamp, temperature, humidity, pressure, sd_health, device_id),
    )
    connection.commit()

    measurement = get_measurement(cursor.lastrowid)
    if measurement is None:
        raise sqlite3.DatabaseError("Failed to fetch the inserted measurement.")
    return measurement


def get_measurement(record_id: int) -> Measurement | None:
    """Fetch a single measurement by primary key."""
    row = get_db().execute(
        f"SELECT {MEASUREMENT_COLUMNS} FROM measurements WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        return None
    return Measurement.from_row(row)


def list_measurements(limit: int) -> list[Measurement]:
    """Return the newest measurements first."""
    rows = get_db().execute(
        f"""
        SELECT {MEASUREMENT_COLUMNS}
        FROM measurements
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [Measurement.from_row(row) for row in rows]


def delete_measurement(record_id: int) -> Measurement | None:
    """Delete a measurement row and return the removed record."""
    measurement = get_measurement(record_id)
    if measurement is None:
        return None

    connection = get_db()
    connection.execute("DELETE FROM measurements WHERE id = ?", (record_id,))
    connection.commit()
    return measurement


def ping_database() -> None:
    """Run a lightweight query to confirm the database is reachable."""
    get_db().execute("SELECT 1").fetchone()
