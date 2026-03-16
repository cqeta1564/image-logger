"""Database-backed data models."""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Row


@dataclass(slots=True)
class Measurement:
    """A stored image upload and its environmental metadata."""

    id: int
    filename: str
    timestamp: str
    temperature: float | None
    humidity: float | None
    pressure: float | None
    sd_health: str
    device_id: str

    @classmethod
    def from_row(cls, row: Row) -> Measurement:
        """Build a measurement instance from a SQLite row."""
        return cls(
            id=row["id"],
            filename=row["filename"],
            timestamp=row["timestamp"],
            temperature=row["temperature"],
            humidity=row["humidity"],
            pressure=row["pressure"],
            sd_health=row["sd_health"] or "unknown",
            device_id=row["device_id"] or "unknown-device",
        )
