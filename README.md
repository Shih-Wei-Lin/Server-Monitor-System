# Server Monitor System

Collects server resource usage over SSH, stores metrics in MySQL, and presents dashboards in Streamlit.

## Requirements

- Python 3.10+
- MySQL
- OpenSSH access to target servers

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure `lib/config.py` with database credentials, SSH accounts, and URLs.

3. Ensure your MySQL schema matches the expected tables used by the scripts.

## Run

### Streamlit UI

```bash
streamlit run lib/ui/app.py
```

### Booking UI

The booking interface is part of the Streamlit app.
Booking state is stored in `booking_state.json` at the repo root.

### Data Collection Scripts

```bash
python -m lib.mysql_update.check_connect
python -m lib.mysql_update.update_status
python -m lib.mysql_update.compress_data
```

### Scheduler

```bash
python -m lib.auto_run.runner
```

### Backup (optional)

```bash
python -m lib.mysql_update.backup
```

## Notes

- `lib/auto_run/runner.py` uses `DefaultConfig.FILE_PATH` to locate scripts.
  If it is empty, it defaults to `lib/mysql_update` under the repo root.
- For version display, the UI reads `git describe` when available.
