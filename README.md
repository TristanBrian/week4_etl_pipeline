# Industrializing the Daily Operations Pipeline

This lab turns a manual daily sensor update into a modular, repeatable Python pipeline.

## Files

- `run_pipeline.py` - modular extract, transform, quality gate, and load script.
- `data/sensor_data.csv` - clean sample input.
- `data/sensor_data_bad_example.csv` - intentionally bad input for testing the quality gate.
- `.env` - local configuration for this lab.
- `.env.example` - safe template for GitHub.
- `docs/automation_proof.md` - cron and Windows Task Scheduler proof instructions.
- `docs/technical_brief.md` - plain-English manager memo.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_pipeline.py
```

## Quality Gate Test

To prove the pipeline halts on bad data, temporarily set this in `.env`:

```text
SOURCE_CSV=data/sensor_data_bad_example.csv
```

Then rerun:

```powershell
python run_pipeline.py
```

The run should stop before loading to the database.

## Idempotency Test

Run the pipeline twice with the clean file:

```powershell
python run_pipeline.py
python run_pipeline.py
```

The script deletes the existing rows for the configured `SNAPSHOT_DATE` and reloads that day. Re-running does not create duplicate daily records.
