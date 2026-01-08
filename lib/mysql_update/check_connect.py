"""
Connectivity checks and disk usage updates for servers.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

import aiomysql
import asyncssh

from lib.config import DefaultConfig

USERNAME = DefaultConfig.DEFAULT_USERNAME
PASSWORD = DefaultConfig.DEFAULT_PASSWORD

DB_CONFIG = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}

DISK_INFO_PATTERN = re.compile(r"(\d+)\s+(\d+)")


def parse_disk_info(disk_output: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse WMIC disk output and convert to GB.

    Parameters:
        disk_output (str): Raw command output.
    Returns:
        Tuple[Optional[float], Optional[float]]: Remaining and total GB values.
    Raises:
        None
    """
    match = DISK_INFO_PATTERN.search(disk_output.strip())
    if not match:
        return None, None

    remaining_capacity_bytes = int(match.group(1))
    total_capacity_bytes = int(match.group(2))
    total_capacity_gb = round(total_capacity_bytes / (1024**3), 2)
    remaining_capacity_gb = round(remaining_capacity_bytes / (1024**3), 2)
    return total_capacity_gb, remaining_capacity_gb


async def test_server_disk_c_storage(
    last_checked: datetime, server: Dict[str, str], db_pool
) -> None:
    """
    Update C drive storage data for a server.

    Parameters:
        last_checked (datetime): Timestamp for this check.
        server (Dict[str, str]): Server record with host and server_id.
        db_pool: Aiomysql connection pool.
    Returns:
        None
    Raises:
        None
    """
    try:
        async with asyncssh.connect(
            server["host"],
            username=USERNAME,
            password=PASSWORD,
            known_hosts=None,
            connect_timeout=2,
        ) as conn:
            result = await conn.run(
                'wmic LogicalDisk where DeviceID="C:" get Size,FreeSpace', check=True
            )
            total_capacity, remaining_capacity = parse_disk_info(result.stdout)
    except (OSError, asyncssh.Error) as exc:
        print(f"Disk check failed for {server['host']}: {exc}")
        total_capacity, remaining_capacity = None, None

    if total_capacity and remaining_capacity:
        server_id = server["server_id"]
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO server_disk_C_storage
                        (server_id, total_capacity_gb, remaining_capacity_gb, last_checked)
                    VALUES (%s, %s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                        total_capacity_gb = new.total_capacity_gb,
                        remaining_capacity_gb = new.remaining_capacity_gb,
                        last_checked = new.last_checked
                    """,
                    (server_id, total_capacity, remaining_capacity, last_checked),
                )
                await conn.commit()


async def test_server_connectivity_and_disk(
    last_checked: datetime, server: Dict[str, str], db_pool
) -> None:
    """
    Check connectivity for a server and update disk usage.

    Parameters:
        last_checked (datetime): Timestamp for this check.
        server (Dict[str, str]): Server record with host and server_id.
        db_pool: Aiomysql connection pool.
    Returns:
        None
    Raises:
        None
    """
    is_connectable = False
    try:
        async with asyncssh.connect(
            server["host"],
            username=USERNAME,
            password=PASSWORD,
            known_hosts=None,
            connect_timeout=1.5,
        ) as _conn:
            is_connectable = True
            await test_server_disk_c_storage(last_checked, server, db_pool)
    except (OSError, asyncssh.Error) as exc:
        print(f"Connection failed to {server['host']}: {exc}")
        is_connectable = False

    server_id = server["server_id"]
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO server_connectivity (server_id, is_connectable, last_checked)
                VALUES (%s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                    is_connectable = new.is_connectable,
                    last_checked = new.last_checked
                """,
                (server_id, is_connectable, last_checked),
            )
            await conn.commit()


async def main() -> None:
    """
    Run connectivity checks for all servers.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    db_pool = await aiomysql.create_pool(**DB_CONFIG)
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT server_id, host FROM servers")
            servers = await cursor.fetchall()

    last_checked = datetime.now()
    tasks = [
        test_server_connectivity_and_disk(last_checked, server, db_pool) for server in servers
    ]
    await asyncio.gather(*tasks)

    db_pool.close()
    await db_pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
