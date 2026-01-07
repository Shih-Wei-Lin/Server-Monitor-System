# lib/UI/tool/booking_utils.py

"""
Utility functions for handling the server booking state.

This module provides a thread-safe way to read and write the server booking status
to a JSON file by using a file-based locking mechanism.
"""

import json
import os
import time
from typing import Any, Dict

from lib.db_config import DefaultConfig

# Define the path to the booking state file and the lock file
# Assumes the project root is three levels up from the 'tool' directory
# lib/UI/tool -> lib/UI -> lib -> root
_tool_dir: str = os.path.dirname(__file__)
_root_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(_tool_dir)))
BOOKING_STATE_FILE: str = os.path.join(_root_dir, "booking_state.json")
LOCK_FILE: str = os.path.join(_root_dir, "booking_state.lock")

BookingState = Dict[str, Dict[str, Any]]


def get_booking_state() -> BookingState:
    """
    Reads the booking state from the JSON file.

    If the file does not exist or is empty or contains invalid JSON,
    it safely returns an empty dictionary.

    Returns:
        BookingState: A dictionary representing the current booking state.
                      Example: {"server_id": {"user": "name", "purpose": "testing", ...}}
    """
    try:
        with open(BOOKING_STATE_FILE, "r", encoding="utf-8") as f:
            content: str = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_booking_state(data: BookingState) -> None:
    """
    Saves the given data to the booking state JSON file.

    Args:
        data (BookingState): The booking state dictionary to save.

    Raises:
        IOError: If the file cannot be written to.
    """
    with open(BOOKING_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def acquire_lock(timeout: int = DefaultConfig.LOCK_TIMEOUT_S) -> bool:
    """
    Acquires a file lock by creating a .lock file.

    This function will wait for a lock to be released for a specified
    duration. If it cannot acquire the lock within the timeout, it will fail.
    This prevents indefinite waits.

    Args:
        timeout (int): Maximum time in seconds to wait for the lock. Defaults to 5.

    Returns:
        bool: True if the lock was acquired successfully, False otherwise.
    """
    start_time: float = time.time()
    while os.path.exists(LOCK_FILE):
        if time.time() - start_time > timeout:
            return False  # Timeout
        time.sleep(0.1)

    try:
        # Create the lock file
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except IOError:
        return False


def release_lock() -> None:
    """
    Releases the file lock by deleting the .lock file.

    This function will silently ignore errors, for instance, if the
    lock file was already removed by another process.
    """
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except IOError:
        # Handle cases where the file might be locked or already removed
        pass
