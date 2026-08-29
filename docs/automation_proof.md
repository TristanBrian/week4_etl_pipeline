# Proof of Automation

The daily operations report should be ready by 6:00 AM, so schedule the pipeline to run every day at 6:00 AM.

## Linux or Mac Cron

Open cron:

```bash
crontab -e
```

Add this entry:

```cron
0 6 * * * cd "/path/to/IDOP" && /usr/bin/python3 run_pipeline.py
```

Take a screenshot of the saved cron entry and store it in this folder as `cron_screenshot.png`.

## Windows Task Scheduler

1. Open **Task Scheduler**.
2. Choose **Create Basic Task**.
3. Name it `Daily Operations Pipeline`.
4. Set the trigger to **Daily** at **6:00:00 AM**.
5. Choose **Start a Program**.
6. Program/script: the full path to `python.exe`.
7. Add arguments: `run_pipeline.py`.
8. Start in: the full path to the `IDOP` folder.
9. Save the task.

Take a screenshot of the final task screen and store it in this folder as `task_scheduler_screenshot.png`.
