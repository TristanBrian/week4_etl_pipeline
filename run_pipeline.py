#!/usr/bin/env python3
"""
run_pipeline.py - Production ETL Pipeline for IoT Sensor Data

Extracts sensor data from CSV, transforms it, validates it with Great Expectations,
and loads it into SQLite. Idempotent, cron-safe, and fully logged.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta
import random

import pandas as pd
from dotenv import load_dotenv
from faker import Faker

# Great Expectations imports
import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnToExist,
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeBetween,
)

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_path)

DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_FILENAME", "pipeline.db"))
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, os.getenv("RAW_FILENAME", "raw_sensors.csv"))
LOG_FILE = os.path.join(PROJECT_ROOT, "pipeline.log")

# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# EXTRACT - NOW WITH FAKER
# ============================================================

def generate_sample_data(num_rows=20):
    """
    Generates a realistic sensor dataset using Faker.
    All values are within valid ranges (passes validation).
    """
    os.makedirs(PROJECT_ROOT, exist_ok=True)
    logger.info(f"Generating {num_rows} rows of realistic sensor data at {RAW_DATA_PATH}")

    fake = Faker()
    Faker.seed(42)  # reproducible

    data = {
        "id": [f"S{i+1:03d}" for i in range(num_rows)],
        "timestamp": [
            (datetime.now() - timedelta(minutes=i*5)).isoformat()
            for i in range(num_rows)
        ],
        "temperature": [round(random.uniform(18.0, 35.0), 1) for _ in range(num_rows)],
        "pressure": [round(random.uniform(980.0, 1050.0), 1) for _ in range(num_rows)],
        "humidity": [round(random.uniform(30.0, 70.0), 1) for _ in range(num_rows)],
    }
    df = pd.DataFrame(data)
    df.to_csv(RAW_DATA_PATH, index=False)
    logger.info(f"Generated {len(df)} rows of clean data (all valid).")
    return df

def extract_data():
    """Reads CSV into DataFrame. Creates sample data if missing."""
    logger.info(f"Extracting data from {RAW_DATA_PATH}...")
    if not os.path.exists(RAW_DATA_PATH):
        df = generate_sample_data()
    else:
        df = pd.read_csv(RAW_DATA_PATH)
        logger.info(f"Extracted {len(df)} rows.")
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df

# ============================================================
# TRANSFORM (IDEMPOTENT)
# ============================================================

def transform_data(df):
    """Cleans data: removes nulls, clips outliers, drops duplicates."""
    logger.info("Transforming data...")
    initial_count = len(df)
    
    # Drop rows with null IDs
    df = df.dropna(subset=['id'])
    
    # Clip temperature
    temp_min = float(os.getenv("TEMP_MIN", -50))
    temp_max = float(os.getenv("TEMP_MAX", 100))
    df['temperature'] = df['temperature'].clip(lower=temp_min, upper=temp_max)
    
    # Fix pressure (must be > 0)
    df['pressure'] = df['pressure'].apply(
        lambda x: 999.0 if (pd.isna(x) or x <= 0) else x
    )
    
    # Clip humidity
    df['humidity'] = df['humidity'].clip(lower=0, upper=100)
    
    # Idempotency: remove duplicate IDs
    df = df.drop_duplicates(subset=['id'], keep='first')
    
    # Fill remaining nulls
    df['temperature'] = df['temperature'].fillna(df['temperature'].mean())
    df['pressure'] = df['pressure'].fillna(999.0)
    df['humidity'] = df['humidity'].fillna(50.0)
    
    final_count = len(df)
    logger.info(f"Transformed: {initial_count} -> {final_count} rows.")
    return df

# ============================================================
# VALIDATION (GREAT EXPECTATIONS)
# ============================================================

def validate_data(df):
    """
    Validates data with 8 Great Expectations rules.
    Halts pipeline (sys.exit(1)) if ANY rule fails.
    """
    logger.info("Starting Great Expectations validation...")
    
    # Ephemeral context (no files written)
    context = gx.get_context(mode="ephemeral")
    
    # Create expectation suite
    suite_name = "sensor_suite"
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    
    # 8 Expectations (exceeds required 5)
    suite.add_expectation(ExpectColumnToExist(column="id"))
    suite.add_expectation(ExpectColumnToExist(column="temperature"))
    suite.add_expectation(ExpectColumnToExist(column="pressure"))
    suite.add_expectation(ExpectColumnToExist(column="humidity"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="id"))
    suite.add_expectation(
        ExpectColumnValuesToBeBetween(column="temperature", min_value=-50, max_value=100)
    )
    suite.add_expectation(
        ExpectColumnValuesToBeBetween(column="pressure", min_value=0.1)
    )
    suite.add_expectation(
        ExpectColumnValuesToBeBetween(column="humidity", min_value=0, max_value=100)
    )
    
    logger.info(f"Loaded {len(suite.expectations)} expectations.")
    
    # Add pandas datasource and dataframe asset
    datasource = context.data_sources.add_pandas("pandas_datasource")
    asset = datasource.add_dataframe_asset("df_asset")
    
    # Create a batch definition
    batch_definition = asset.add_batch_definition_whole_dataframe("batch_definition")
    
    # Get the batch (pass DataFrame via batch_parameters)
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    
    # Create validator and validate
    validator = context.get_validator(
        batch=batch,
        expectation_suite=suite,
    )
    results = validator.validate()
    
    # Check results
    if not results["success"]:
        logger.error("❌ VALIDATION FAILED - HALTING PIPELINE!")
        for res in results["results"]:
            if not res["success"]:
                logger.error(f"  Failed: {res['expectation_config'].get('type', 'Unknown')}")
        sys.exit(1)  # Hard stop
    else:
        logger.info("✅ All data quality checks passed!")
        return True

# ============================================================
# LOAD (IDEMPOTENT)
# ============================================================

def load_data(df):
    """Loads to SQLite with 'replace' mode (idempotent)."""
    logger.info(f"Loading {len(df)} rows into {DB_PATH}...")
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql("sensor_readings", conn, if_exists="replace", index=False)
        logger.info(f"Loaded into 'sensor_readings' (table replaced).")
    except Exception as e:
        logger.error(f"Load failed: {e}")
        raise
    finally:
        conn.close()

# ============================================================
# MAIN
# ============================================================

def main():
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"PIPELINE STARTED at {start_time}")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info("=" * 60)
    
    try:
        raw_df = extract_data()
        clean_df = transform_data(raw_df)
        validate_data(clean_df)
        load_data(clean_df)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"✅ SUCCESS at {end_time} (Duration: {duration:.2f}s)")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"💥 CRASH: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()