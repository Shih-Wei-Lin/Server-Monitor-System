"""
Execution helpers for scheduled scripts.
"""

from __future__ import annotations

import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_run.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def periodical_execution(file_path: str, minutes: int = 5, seconds: float = 0, count: int = 10) -> None:
    """
    Execute a Python file on a fixed interval.

    Parameters:
        file_path (str): Path to the Python file to execute.
        minutes (int): Minutes between executions.
        seconds (float): Seconds between executions.
        count (int): Executions per batch before prompt.
    Returns:
        None
    Raises:
        None
    """
    try:
        file_obj = Path(file_path)
        if not file_obj.is_file():
            logger.error("File not found: %s", file_path)
            return

        if not _validate_interval(minutes, "minutes"):
            return
        if not _validate_interval(seconds, "seconds"):
            return
        if not _validate_interval(count, "count"):
            return

        nap_time = minutes * 60 + seconds
        command = f"python {file_path}"

        status = True
        while status:
            logger.info(
                "Executing %s times every %s minutes and %s seconds",
                count,
                minutes,
                f"{seconds:.2f}",
            )
            for epoch in range(count):
                logger.info("Epoch: %s", epoch)
                execution_time = executioner(command)
                elapsed = execution_time or 0

                if epoch < count - 1:
                    sleep_time = max(0, nap_time - elapsed)
                    time.sleep(sleep_time)

            user_input = input("Run again? (Y/n): ") or "y"
            status = user_input.lower() not in ("n", "no")
    except Exception as exc:
        logger.exception("Unexpected error during execution: %s", exc)


def continuous_execution(
    check_file: str,
    extract_file: str,
    min_check: int = 60,
    sec_check: float = 0,
    min_extract: int = 5,
    sec_extract: float = 0,
) -> None:
    """
    Continuously run connection checks and data extraction.

    Parameters:
        check_file (str): Path to the connectivity check script.
        extract_file (str): Path to the data extraction script.
        min_check (int): Minutes between connection checks.
        sec_check (float): Seconds between connection checks.
        min_extract (int): Minutes between data extractions.
        sec_extract (float): Seconds between data extractions.
    Returns:
        None
    Raises:
        None
    """
    try:
        check_path = Path(check_file)
        extract_path = Path(extract_file)
        if not check_path.is_file():
            logger.error("Connection check file not found: %s", check_file)
            return
        if not extract_path.is_file():
            logger.error("Data extraction file not found: %s", extract_file)
            return

        for name, value in {
            "min_check": min_check,
            "sec_check": sec_check,
            "min_extract": min_extract,
            "sec_extract": sec_extract,
        }.items():
            if not _validate_interval(value, name):
                return

        if (min_check + sec_check == 0) and (min_extract + sec_extract == 0):
            logger.error("Execution time cannot be zero")
            return

        signal.signal(signal.SIGINT, terminate_execution)

        nap_check = min_check * 60 + sec_check
        nap_extract = min_extract * 60 + sec_extract
        logger.info("Checking connection every %s minutes and %s seconds", min_check, f"{sec_check:.2f}")
        logger.info("Extracting data every %s minutes and %s seconds", min_extract, f"{sec_extract:.2f}")

        check_command = f"python {check_file}"
        extract_command = f"python {extract_file}"

        time_until_next_check = 0.0

        while True:
            if time_until_next_check <= 0:
                logger.info("Executing connection check")
                executioner(check_command, evaluate_time=False)
                time_until_next_check = nap_check

            logger.info("Executing data extraction")
            extract_time = executioner(extract_command) or 0

            sleep_time = max(0, nap_extract - extract_time)
            time_until_next_check -= nap_extract

            mins = int(time_until_next_check // 60)
            secs = time_until_next_check % 60
            logger.info("Next connection check in %s minutes and %s seconds", mins, f"{secs:.2f}")

            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as exc:
        logger.exception("Unexpected error during continuous execution: %s", exc)


def executioner(command: str, evaluate_time: bool = True) -> Optional[float]:
    """
    Execute a shell command and optionally return the elapsed time.

    Parameters:
        command (str): Command to execute.
        evaluate_time (bool): Whether to return the execution time.
    Returns:
        Optional[float]: Execution time in seconds, or None.
    Raises:
        None
    """
    start = time.time()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    except Exception as exc:
        logger.exception("Command failed: %s", exc)
        return None

    execution_time = time.time() - start
    if result.returncode != 0:
        logger.warning("Command failed with exit code %s", result.returncode)
        logger.error("Standard error: %s", result.stderr)
    else:
        logger.info("Command succeeded")
        logger.info("Standard output: %s", result.stdout)
        logger.info("Execution time: %.2f seconds", execution_time)

    return execution_time if evaluate_time else None


def terminate_execution(sig_num, _frame) -> None:
    """
    Handle termination signals by exiting cleanly.

    Parameters:
        sig_num (int): Signal number.
        _frame: Current stack frame.
    Returns:
        None
    Raises:
        SystemExit: Always exits the process.
    """
    logger.info("Received signal %s, exiting", sig_num)
    sys.exit(0)


def _validate_interval(value, name: str) -> bool:
    """
    Validate that a timing value is a non-negative number.

    Parameters:
        value: Value to validate.
        name (str): Name used in error messages.
    Returns:
        bool: True if valid, False otherwise.
    Raises:
        None
    """
    if isinstance(value, (int, float)):
        if value < 0:
            logger.error("%s must be non-negative", name)
            return False
        return True

    logger.error("%s must be a number", name)
    return False
