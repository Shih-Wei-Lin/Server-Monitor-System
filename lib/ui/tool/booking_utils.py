"""
File-based booking state helpers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from lib.config import DefaultConfig

ROOT_DIR = Path(__file__).resolve().parents[3]
BOOKING_STATE_FILE = ROOT_DIR / "booking_state.json"
LOCK_FILE = ROOT_DIR / "booking_state.lock"

BookingState = Dict[str, Dict[str, Any]]


def get_booking_state() -> BookingState:
    """
    Load the booking state from disk.

    Parameters:
        None
    Returns:
        BookingState: The current booking state, or an empty dict if missing or invalid.
    Raises:
        None
    """
    try:
        content = BOOKING_STATE_FILE.read_text(encoding="utf-8")
        if not content:
            return {}
        return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_booking_state(data: BookingState) -> None:
    """
    Persist the booking state to disk.

    Parameters:
        data (BookingState): The booking state dictionary to write.
    Returns:
        None
    Raises:
        OSError: If the file cannot be written.
    """
    BOOKING_STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def acquire_lock(timeout: int = DefaultConfig.LOCK_TIMEOUT_S) -> bool:
    """
    Acquire a file lock by creating a lock file.

    Parameters:
        timeout (int): Maximum wait time in seconds.
    Returns:
        bool: True if the lock is acquired, False if it times out.
    Raises:
        None
    """
    start_time = time.time()
    while LOCK_FILE.exists():
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.1)

    try:
        LOCK_FILE.write_text(str(int(time.time())), encoding="utf-8")
        return True
    except OSError:
        return False


def release_lock() -> None:
    """
    Release the file lock.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass
