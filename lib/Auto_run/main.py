import io
import logging
import os
import sys

# Ensure redirection of sys.stdout and sys.stderr in all possible places
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
# Get the directory where the current script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# print(f"Current Directory: {current_dir}")
# Get the parent directory, which should be "ServerMonitor"
parent_dir = os.path.dirname(current_dir)
# print(f"Parent Directory: {parent_dir}")
# Get the root directory
root_dir = os.path.dirname(parent_dir)
# print(f"Root Directory: {root_dir}")
# Add the root directory to the system path
sys.path.append(root_dir)
# If "ServerMonitor" directory is not in the system path, add it
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
from lib.Auto_run import util
from lib.db_config import DefaultConfig

# Set logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_run.log"), logging.StreamHandler()],
)
logger = logging.getLogger("main")


def main():
    """Main program entry point"""
    try:
        # Get file paths
        file_path = DefaultConfig.FILE_PATH
        file_check = DefaultConfig.FILE_CHECK_CONNECT
        file_extract = DefaultConfig.FILE_EXTRACT
        # Build full paths
        check_file = os.path.join(file_path, file_check)
        extract_file = os.path.join(file_path, file_extract)
        # Verify files exist
        if not os.path.isfile(check_file):
            logger.error(f"Connection check file not found: {check_file}")
            return
        if not os.path.isfile(extract_file):
            logger.error(f"Data extraction file not found: {extract_file}")
            return
        # Start continuous execution
        logger.info("Starting continuous execution program")
        logger.info(f"Connection check file: {check_file}")
        logger.info(f"Data extraction file: {extract_file}")
        util.continuous_execution(
            check_file,
            extract_file,
            min_check=60,
            sec_check=0,
            min_extract=0,
            sec_extract=5,
        )
    except Exception as e:
        logger.exception(f"An error occurred while running the program: {e}")


if __name__ == "__main__":
    main()
