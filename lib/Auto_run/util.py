import io
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_run.log"), logging.StreamHandler()],
)
logger = logging.getLogger()


def periodical_execution(
    file_path: str, min: int = 5, sec: float = 0, count: int = 10
) -> None:
    """
    Periodically execute the specified Python file.
    Args:
        file_path: Path to the Python file to be executed
        min: Minutes between each execution (default: 5)
        sec: Seconds between each execution (default: 0)
        count: Number of executions before asking if to continue (default: 10)
    """
    try:
        # Check if the file exists
        file_obj = Path(file_path)
        if not file_obj.is_file():
            logger.error(f"File not found: {file_path}")
            return

        # Validate parameters
        for param_name, param_value in {"min": min, "sec": sec, "count": count}.items():
            if isinstance(param_value, int):
                if param_value < 0:
                    logger.error(f"{param_name} must be a non-negative integer")
                    return
            elif isinstance(param_value, float):
                if param_value < 0:
                    logger.error(f"{param_name} must be a non-negative number")
                    return
            else:
                logger.error(f"{param_name} must be an integer or float")
                return

        # Calculate nap time
        nap_time = min * 60 + sec
        command = f"python {file_path}"

        # Main execution loop
        status = True
        while status:
            logger.info(
                f"To be executed {count} times, with an interval of {min} minutes and {sec:.2f} seconds"
            )
            for epoch in range(count):
                logger.info(f"Epoch: {epoch}")
                execution_time = executioner(command)
                # No need to sleep after the last execution
                if epoch < count - 1:
                    sleep_time = max(0, nap_time - execution_time)
                    time.sleep(sleep_time)

            # Ask whether to continue
            user_input = input("Do you want to run again? (Y/n): ") or "y"
            status = user_input.lower() not in ("n", "no")
    except Exception as e:
        logger.exception(f"An error occurred during execution: {e}")


def continuous_execution(
    check_file: str,
    extract_file: str,
    min_check: int = 60,
    sec_check: float = 0,
    min_extract: int = 5,
    sec_extract: float = 0,
) -> None:
    """
    Continuously execute the connection check and data extraction files.
    Args:
        check_file: Path to the Python file for checking the connection
        extract_file: Path to the Python file for extracting data
        min_check: Interval in minutes between connection checks (default: 60)
        sec_check: Interval in seconds between connection checks (default: 0)
        min_extract: Interval in minutes between data extractions (default: 5)
        sec_extract: Interval in seconds between data extractions (default: 0)
    """
    try:
        # Check if the files exist
        check_path = Path(check_file)
        extract_path = Path(extract_file)
        if not check_path.is_file():
            logger.error(f"Connection check file not found: {check_file}")
            return
        if not extract_path.is_file():
            logger.error(f"Data extraction file not found: {extract_file}")
            return

        # Validate parameters
        for param_name, param_value in {
            "min_check": min_check,
            "sec_check": sec_check,
            "min_extract": min_extract,
            "sec_extract": sec_extract,
        }.items():
            if isinstance(param_value, int):
                if param_value < 0:
                    logger.error(f"{param_name} must be a non-negative integer")
                    return
            elif isinstance(param_value, float):
                if param_value < 0:
                    logger.error(f"{param_name} must be a non-negative number")
                    return
            else:
                logger.error(f"{param_name} must be an integer or float")
                return

        # Check that at least one execution time is not zero
        if (min_check + sec_check == 0) and (min_extract + sec_extract == 0):
            logger.error("Execution time cannot be zero")
            return

        # Calculate execution intervals
        nap_check = min_check * 60 + sec_check
        nap_extract = min_extract * 60 + sec_extract
        logger.info(
            f"Checking connection every {min_check} minutes and {sec_check:.2f} seconds"
        )
        logger.info(
            f"Extracting data every {min_extract} minutes and {sec_extract:.2f} seconds"
        )

        check_command = f"python {check_file}"
        extract_command = f"python {extract_file}"

        # Initialize countdown timer
        time_until_next_check = 0

        # Main loop
        while True:
            # Check if connection check is needed
            if time_until_next_check <= 0:
                logger.info("Executing connection check")
                executioner(check_command, evaluate_time=False)
                time_until_next_check = nap_check

            # Execute data extraction
            logger.info("Executing data extraction")
            extract_time = executioner(extract_command)

            # Calculate the wait time before next data extraction
            sleep_time = max(0, nap_extract - extract_time)

            # Update countdown timer
            time_until_next_check -= nap_extract

            # Display time until next connection check
            mins = int(time_until_next_check // 60)
            secs = time_until_next_check % 60
            logger.info(
                f"Checking connection again in {mins} minutes and {secs:.2f} seconds"
            )

            # Sleep until the next data extraction
            if sleep_time > 0:
                time.sleep(sleep_time)
    except Exception as e:
        logger.exception(f"An error occurred during execution: {e}")


def daily_execution(
    file_path: str, hour: int = 24, minute: int = 0, second: int = 0
) -> None:
    """
    Execute the specified Python file once every day at a given time.
    Args:
        file_path: Path to the Python file to be executed
        hour: Hour of the day for execution (default: 24)
        minute: Minute of the hour for execution (default: 0)
        second: Second of the minute for execution (default: 0)
    """
    try:
        # Check if the file exists
        file_obj = Path(file_path)
        if not file_obj.is_file():
            logger.error(f"File not found: {file_path}")
            return

        # Validate parameters
        for param_name, param_value in {
            "hour": hour,
            "minute": minute,
            "second": second,
        }.items():
            if isinstance(param_value, int):
                if param_value < 0:
                    logger.error(f"{param_name} must be a non-negative integer")
                    return
            else:
                logger.error(f"{param_name} must be an integer")
                return

        # Calculate the next execution time
        now = datetime.now()
        next_execution_time = datetime(
            now.year, now.month, now.day, hour, minute, second
        )

        if next_execution_time < now:
            next_execution_time += timedelta(days=1)

        logger.info(f"Next daily execution scheduled for: {next_execution_time}")

        # Main loop
        while True:
            # Calculate time until the next execution
            sleep_until_next = (next_execution_time - datetime.now()).total_seconds()
            if sleep_until_next > 0:
                logger.info(
                    f"Sleeping until next daily execution in {sleep_until_next / 3600:.2f} hours"
                )
                time.sleep(sleep_until_next)

            # Execute the file
            command = f"python {file_path}"
            executioner(command, evaluate_time=False)

            # Calculate the next execution time for the following day
            next_execution_time += timedelta(days=1)
    except Exception as e:
        logger.exception(f"An error occurred during daily execution: {e}")


def executioner(command: str, evaluate_time: bool = True) -> Optional[float]:
    """
    Execute the specified command and calculate the execution time.
    Args:
        command: Command to be executed
        evaluate_time: Whether to calculate and return the execution time
    Returns:
        Execution time in seconds if evaluate_time is True, otherwise None
    """
    start = time.time()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    except Exception as e:
        logger.exception(f"An exception occurred while executing the command: {e}")
        return None

    end = time.time()
    execution_time = end - start

    if result.returncode != 0:
        logger.warning(f"Command execution failed with exit code: {result.returncode}")
        logger.error(f"Standard error output: {result.stderr}")
    else:
        logger.info("Command executed successfully")
        logger.info(f"Standard output: {result.stdout}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")

    if evaluate_time:
        return execution_time

    return None
