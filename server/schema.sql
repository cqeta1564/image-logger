CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    sd_health TEXT NOT NULL DEFAULT 'unknown',
    device_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
    ON measurements (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_measurements_device_id
    ON measurements (device_id);
