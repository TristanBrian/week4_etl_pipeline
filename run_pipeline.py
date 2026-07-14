from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "pipeline.log"


def configure_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def env_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def load_config() -> dict[str, Any]:
    load_dotenv(BASE_DIR / ".env")
    config = {
        "source_type": os.getenv("SOURCE_TYPE", "csv").lower(),
        "source_csv": env_path(os.getenv("SOURCE_CSV", "data/sensor_data.csv")),
        "database_path": env_path(os.getenv("DATABASE_PATH", "output/operations_daily_snapshots.sqlite")),
        "target_table": os.getenv("TARGET_TABLE", "daily_sensor_snapshots"),
        "snapshot_date": os.getenv("SNAPSHOT_DATE", datetime.now(timezone.utc).date().isoformat()),
        "api_url": os.getenv("API_URL", ""),
        "api_key": os.getenv("API_KEY", ""),
    }
    return config


def extract_sensor_data(config: dict[str, Any]) -> pd.DataFrame:
    """Extract raw sensor data from a CSV file or an API endpoint."""
    if config["source_type"] == "csv":
        logging.info("Extracting CSV source: %s", config["source_csv"])
        return pd.read_csv(config["source_csv"])

    if config["source_type"] == "api":
        if not config["api_url"]:
            raise ValueError("SOURCE_TYPE is api, but API_URL is empty.")
        headers = {}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        logging.info("Extracting API source: %s", config["api_url"])
        response = requests.get(config["api_url"], headers=headers, timeout=30)
        response.raise_for_status()
        return pd.DataFrame(response.json())

    raise ValueError(f"Unsupported SOURCE_TYPE: {config['source_type']}")


def transform_sensor_data(raw_df: pd.DataFrame, snapshot_date: str) -> pd.DataFrame:
    """Clean duplicate rows and remove obviously invalid pressure readings."""
    df = raw_df.copy()
    df.columns = [column.strip().lower() for column in df.columns]

    required_columns = ["timestamp", "sensor_id", "pressure_psi", "temperature_c", "status"]
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Input data is missing required columns: {missing_columns}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["pressure_psi"] = pd.to_numeric(df["pressure_psi"], errors="coerce")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["sensor_id"] = df["sensor_id"].astype("string").str.strip()
    df["status"] = df["status"].astype("string").str.strip().str.upper()

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["timestamp", "sensor_id"], keep="last")
    logging.info("Removed %s duplicate rows", before_dedup - len(df))

    before_filter = len(df)
    df = df[df["pressure_psi"].isna() | (df["pressure_psi"] >= 0)].copy()
    logging.info("Filtered %s negative pressure rows", before_filter - len(df))

    df["snapshot_date"] = snapshot_date
    df["loaded_at_utc"] = datetime.now(timezone.utc).isoformat()
    return df.sort_values(["timestamp", "sensor_id"]).reset_index(drop=True)


def validate_with_great_expectations(df: pd.DataFrame) -> bool:
    """
    Run the quality gate.

    The preferred path uses Great Expectations. If Great Expectations is unavailable
    in a classroom environment, the same five rules are checked directly so students
    can still observe the halt behavior.
    """
    try:
        import great_expectations as gx  # type: ignore
        from great_expectations.dataset import PandasDataset  # type: ignore

        class SensorDataset(PandasDataset):
            pass

        ge_df = SensorDataset(df)
        results = [
            ge_df.expect_column_values_to_not_be_null("timestamp"),
            ge_df.expect_column_values_to_not_be_null("sensor_id"),
            ge_df.expect_column_values_to_be_unique("timestamp"),
            ge_df.expect_column_values_to_be_between("pressure_psi", min_value=0, max_value=200),
            ge_df.expect_column_values_to_be_between("temperature_c", min_value=-20, max_value=120),
            ge_df.expect_column_values_to_be_in_set("status", ["OK", "WARN", "FAIL"]),
        ]
        success = all(result["success"] for result in results)
        docs_dir = BASE_DIR / "gx" / "uncommitted" / "data_docs" / "local_site"
        docs_dir.mkdir(parents=True, exist_ok=True)
        report_file = docs_dir / "index.html"
        report_rows = "".join(
            f"<tr><td>{result['expectation_config']['expectation_type']}</td><td>{result['success']}</td></tr>"
            for result in results
        )
        report_file.write_text(
            f"<html><body><h1>Sensor Quality Gate</h1><table>{report_rows}</table></body></html>",
            encoding="utf-8",
        )
        logging.info("Great Expectations version loaded: %s", getattr(gx, "__version__", "unknown"))
        logging.info("Data Docs report: %s", report_file)
        return success
    except ModuleNotFoundError:
        logging.warning("Great Expectations is not installed. Running equivalent local checks.")

    checks = {
        "timestamp has no nulls": df["timestamp"].notna().all(),
        "sensor_id has no nulls": df["sensor_id"].notna().all(),
        "timestamps are unique": df["timestamp"].is_unique,
        "pressure is between 0 and 200 psi": df["pressure_psi"].between(0, 200).all(),
        "temperature is between -20 and 120 C": df["temperature_c"].between(-20, 120).all(),
        "status is recognized": df["status"].isin(["OK", "WARN", "FAIL"]).all(),
    }
    report_file = BASE_DIR / "docs" / "quality_gate_report.txt"
    report_file.write_text("\n".join(f"{name}: {passed}" for name, passed in checks.items()), encoding="utf-8")
    logging.info("Fallback quality report: %s", report_file)
    return all(checks.values())


def load_daily_snapshot(df: pd.DataFrame, config: dict[str, Any]) -> None:
    """Load data safely by replacing only the configured daily snapshot."""
    db_path = config["database_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {config["target_table"]} (
                timestamp TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                pressure_psi REAL NOT NULL,
                temperature_c REAL NOT NULL,
                status TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                loaded_at_utc TEXT NOT NULL,
                PRIMARY KEY (snapshot_date, timestamp, sensor_id)
            )
            """
        )
        conn.execute(f"DELETE FROM {config['target_table']} WHERE snapshot_date = ?", (config["snapshot_date"],))
        df.to_sql(config["target_table"], conn, if_exists="append", index=False)


def run_pipeline() -> None:
    configure_logging()
    logging.info("Pipeline started")
    config = load_config()

    try:
        raw_df = extract_sensor_data(config)
        logging.info("Rows extracted: %s", len(raw_df))

        clean_df = transform_sensor_data(raw_df, config["snapshot_date"])
        logging.info("Rows after transform: %s", len(clean_df))

        if not validate_with_great_expectations(clean_df):
            raise ValueError("Quality gate failed. Load step halted.")
        logging.info("Quality gate passed")

        load_daily_snapshot(clean_df, config)
        logging.info("Rows loaded: %s", len(clean_df))
        logging.info("Pipeline finished successfully")
    except Exception:
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    run_pipeline()
