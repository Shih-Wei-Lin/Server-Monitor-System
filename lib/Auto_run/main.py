import io
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta

# Ensure stdout and stderr are redirected properly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Get the current script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)

# Add root directory to system path
sys.path.append(root_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from lib.Auto_run import util
from lib.db_config import DefaultConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("auto_run.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def daily_compress_and_update(compress_path, extract_path, hour, minute, second):
    """
    Perform compression every day at the specified time and immediately run data extraction.
    Args:
        compress_path (str): Path to the compression script.
        extract_path (str): Path to the data extraction script.
        hour (int): Execution time (hour).
        minute (int): Execution time (minute).
        second (int): Execution time (second).
    """
    try:
        command_compress = f"python {compress_path}"
        command_extract = f"python {extract_path}"
        logger.info(
            f"Daily compression and update task scheduled for {hour:02d}:{minute:02d}:{second:02d}"
        )
        logger.info(f"Compression command: {command_compress}")
        logger.info(f"Data extraction command: {command_extract}")

        while True:
            now = datetime.now()
            next_run = now.replace(
                hour=hour, minute=minute, second=second, microsecond=0
            )
            if now >= next_run:
                next_run += timedelta(days=1)

            sleep_duration = (next_run - now).total_seconds()
            logger.info(
                f"Next daily task will run in {(sleep_duration / 3600):.2f} hours (Time: {next_run})"
            )
            time.sleep(sleep_duration)

            logger.info("Starting daily task: Data compression...")
            util.executioner(command_compress, evaluate_time=False)
            logger.info(
                "After compression is complete, immediately run data extraction to fill the gap..."
            )
            util.executioner(command_extract, evaluate_time=False)
    except Exception as e:
        logger.exception(
            f"Error occurred during daily compression and update task: {e}"
        )


def main():
    """Main program entry point"""
    try:
        # Get file paths
        file_path = DefaultConfig.FILE_PATH
        file_check = DefaultConfig.FILE_CHECK_CONNECT
        file_extract = DefaultConfig.FILE_EXTRACT
        file_compress = DefaultConfig.FILE_COMPRESS

        # Create full paths
        check_file = os.path.join(file_path, file_check)
        extract_file = os.path.join(file_path, file_extract)
        compress_file = os.path.join(file_path, file_compress)

        # Verify files exist
        if not os.path.isfile(check_file):
            logger.error(f"Connection check file does not exist: {check_file}")
            return

        if not os.path.isfile(extract_file):
            logger.error(f"Data extraction file does not exist: {extract_file}")
            return

        if not os.path.isfile(compress_file):
            logger.error(f"Compression script does not exist: {compress_file}")
            return

        # --- Start tasks using multiple threads ---
        # Create a thread for continuous execution (data extraction every 10 seconds, connection check every 60 minutes)
        logger.info("Starting continuous execution program in an independent thread")
        continuous_thread = threading.Thread(
            target=util.continuous_execution,
            args=(check_file, extract_file),
            kwargs={
                "min_check": 60,
                "sec_check": 0,
                "min_extract": 0,
                "sec_extract": 10,
            },
            daemon=True,
        )

        # Create a thread for daily execution (compression and update every day at 00:00:00)
        logger.info(
            "Starting daily compression and update program in an independent thread"
        )
        daily_thread = threading.Thread(
            target=daily_compress_and_update,
            args=(compress_file, extract_file, 0, 0, 0),
            daemon=True,
        )

        # Start threads
        continuous_thread.start()
        daily_thread.start()

        # Keep main thread running to maintain activity of daemon threads
        while True:
            time.sleep(1)
    except Exception as e:
        logger.exception(f"Error occurred during program execution: {e}")
    except KeyboardInterrupt:
        logger.info("Program manually interrupted by user.")


if __name__ == "__main__":
    main()
