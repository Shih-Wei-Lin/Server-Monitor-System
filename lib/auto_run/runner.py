"""
Runner for continuous checks, extraction, and daily compression.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from lib.auto_run import util
from lib.config import DefaultConfig

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPT_DIR = ROOT_DIR / "lib" / "mysql_update"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_run.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def resolve_script_path(filename: str) -> Path:
    """
    Resolve a script path from config or default script directory.

    Parameters:
        filename (str): Script filename to resolve.
    Returns:
        Path: Resolved script path.
    Raises:
        None
    """
    base_path = Path(DefaultConfig.FILE_PATH) if DefaultConfig.FILE_PATH else DEFAULT_SCRIPT_DIR
    if not base_path.is_absolute():
        base_path = ROOT_DIR / base_path
    return base_path / filename


def daily_compress_and_update(compress_path: Path, extract_path: Path, hour: int, minute: int, second: int) -> None:
    """
    Run daily compression and then data extraction.

    Parameters:
        compress_path (Path): Path to the compression script.
        extract_path (Path): Path to the data extraction script.
        hour (int): Hour to run the daily job.
        minute (int): Minute to run the daily job.
        second (int): Second to run the daily job.
    Returns:
        None
    Raises:
        None
    """
    try:
        command_compress = f"python {compress_path}"
        command_extract = f"python {extract_path}"
        logger.info("Daily job scheduled for %02d:%02d:%02d", hour, minute, second)
        logger.info("Compression command: %s", command_compress)
        logger.info("Extraction command: %s", command_extract)

        while True:
            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)

            sleep_duration = (next_run - now).total_seconds()
            logger.info("Next daily run in %.2f hours", sleep_duration / 3600)
            time.sleep(sleep_duration)

            logger.info("Starting daily compression")
            util.executioner(command_compress, evaluate_time=False)
            logger.info("Running extraction after compression")
            util.executioner(command_extract, evaluate_time=False)
    except Exception as exc:
        logger.exception("Daily job failed: %s", exc)


def main() -> None:
    """
    Start the continuous and daily execution threads.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    try:
        check_file = resolve_script_path(DefaultConfig.FILE_CHECK_CONNECT)
        extract_file = resolve_script_path(DefaultConfig.FILE_EXTRACT)
        compress_file = resolve_script_path(DefaultConfig.FILE_COMPRESS)

        if not check_file.is_file():
            logger.error("Connection check file does not exist: %s", check_file)
            return
        if not extract_file.is_file():
            logger.error("Data extraction file does not exist: %s", extract_file)
            return
        if not compress_file.is_file():
            logger.error("Compression script does not exist: %s", compress_file)
            return

        logger.info("Starting continuous execution thread")
        continuous_thread = threading.Thread(
            target=util.continuous_execution,
            args=(str(check_file), str(extract_file)),
            kwargs={"min_check": 60, "sec_check": 0, "min_extract": 0, "sec_extract": 10},
            daemon=True,
        )

        logger.info("Starting daily compression thread")
        daily_thread = threading.Thread(
            target=daily_compress_and_update,
            args=(compress_file, extract_file, 0, 0, 0),
            daemon=True,
        )

        continuous_thread.start()
        daily_thread.start()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.exception("Runner failed: %s", exc)


if __name__ == "__main__":
    main()
