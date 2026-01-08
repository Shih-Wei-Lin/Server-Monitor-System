"""
Create a MySQL dump backup for the configured database.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from lib.config import DefaultConfig

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT_DIR / "backups"

DB_CONFIG = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
}


def build_dump_command(output_path: Path) -> str:
    """
    Build the mysqldump command string.

    Parameters:
        output_path (Path): Output file path for the dump.
    Returns:
        str: Shell command string.
    Raises:
        None
    """
    mysqldump_path = shutil.which("mysqldump")
    if not mysqldump_path:
        return ""

    user = DB_CONFIG["user"]
    password = DB_CONFIG["password"]
    db_name = DB_CONFIG["db"]
    return f'"{mysqldump_path}" -u {user} -p"{password}" {db_name} > "{output_path}"'


def create_backup() -> None:
    """
    Create a timestamped database backup.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    db_name = DB_CONFIG["db"]
    backup_filename = f"{db_name}_{timestamp}.sql"
    backup_fullpath = BACKUP_DIR / backup_filename

    dumpcmd = build_dump_command(backup_fullpath)
    if not dumpcmd:
        print("mysqldump not found on PATH.")
        return

    try:
        print("Starting database backup...")
        subprocess.run(dumpcmd, shell=True, check=True)
        print(f"Backup complete: {backup_fullpath}")
    except subprocess.CalledProcessError as exc:
        print(f"Backup failed: {exc}")


def main() -> None:
    """
    Entry point for backup script.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    create_backup()


if __name__ == "__main__":
    main()
