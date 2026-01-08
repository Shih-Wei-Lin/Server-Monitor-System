"""
Collect server resource usage over SSH and persist it to MySQL.
"""

from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Tuple

import aiomysql
import asyncssh

from lib.config import DefaultConfig

MEMORY_PATTERN = re.compile(r"FreePhysicalMemory=(\d+)\s+TotalVisibleMemorySize=(\d+)", re.IGNORECASE)
CPU_PATTERN = re.compile(r'"(\d+\.\d+)"')
USER_PATTERN = re.compile(r"(\w+)\s+\S+\s+\d+\s+Active", re.MULTILINE)
IP_PATTERN = re.compile(r"\s192\.168\.1\.\d+:3389\s+(192\.168\.1\.\d+)", re.MULTILINE)

DEFAULT_USERNAME = DefaultConfig.DEFAULT_USERNAME
DEFAULT_PASSWORD = DefaultConfig.DEFAULT_PASSWORD
SECONDARY_USERNAME = DefaultConfig.SECONDARY_USERNAME
SECONDARY_PASSWORD = DefaultConfig.SECONDARY_PASSWORD

DB_CONFIG = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}


@asynccontextmanager
async def get_db_pool():
    """
    Create and yield an aiomysql connection pool.

    Parameters:
        None
    Returns:
        aiomysql.Pool: Connection pool context.
    Raises:
        Exception: Propagates pool creation errors.
    """
    pool = await aiomysql.create_pool(**DB_CONFIG)
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()


async def get_server_usage(host: str, connect_timeout: int = 10):
    """
    Collect CPU, memory, active users, and active IPs for a server.

    Parameters:
        host (str): Server hostname or IP.
        connect_timeout (int): SSH connection timeout in seconds.
    Returns:
        Tuple[str, object, object, List[str], List[str]]: Host, CPU, memory, users, IPs.
    Raises:
        None
    """

    async def try_connect(username: str, password: str) -> Optional[Tuple[str, object, object, List[str], List[str]]]:
        try:
            async with asyncssh.connect(
                host,
                username=username,
                password=password,
                connect_timeout=connect_timeout,
                known_hosts=None,
            ) as conn:
                command = (
                    "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value & "
                    'typeperf "\\Processor Information(_Total)\\% Processor Time" -sc 1 & '
                    "query user & "
                    "wmic LOGICALDISK WHERE Name='C:' get FreeSpace /Value &"
                    'netstat -an | findstr "192.168.1.*:3389"'
                )
                result = await conn.run(command)
                output = result.stdout

                memory_match = MEMORY_PATTERN.search(output)
                if memory_match is not None:
                    free_memory = int(memory_match.group(1))
                    total_memory = int(memory_match.group(2))
                    memory_usage = (total_memory - free_memory) / total_memory * 100
                else:
                    memory_usage = "Unknown"

                cpu_usage_match = CPU_PATTERN.search(output)
                if cpu_usage_match is not None:
                    cpu_usage = float(cpu_usage_match.group(1))
                else:
                    cpu_usage = "Unknown"

                active_users = USER_PATTERN.findall(output)
                active_ip = IP_PATTERN.findall(output)

                return host, cpu_usage, memory_usage, active_users, active_ip
        except (asyncssh.Error, asyncio.TimeoutError) as exc:
            print(f"Connect to {host} failed or timed out: {exc}")
            return None

    result = await try_connect(DEFAULT_USERNAME, DEFAULT_PASSWORD)
    if result is None:
        result = await try_connect(SECONDARY_USERNAME, SECONDARY_PASSWORD)
    if result is None:
        print(f"Error connecting to {host}: both credential sets failed.")
        return host, "Error", "Error", [], "Error"
    return result


async def update_database(
    host: str,
    cpu_usage,
    memory_usage,
    active_users: List[str],
    active_ip: List[str],
    current_time: str,
    db_pool,
) -> None:
    """
    Persist server metrics to the database.

    Parameters:
        host (str): Server host.
        cpu_usage: CPU usage percentage or "Unknown".
        memory_usage: Memory usage percentage or "Unknown".
        active_users (List[str]): Active user list.
        active_ip (List[str]): Active IP list.
        current_time (str): Timestamp string.
        db_pool: Aiomysql connection pool.
    Returns:
        None
    Raises:
        None
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT server_id FROM servers WHERE host = %s", (host,))
            server_id = await cur.fetchone()
            if server_id is None:
                await cur.execute("INSERT INTO servers (host) VALUES (%s)", (host,))
                await conn.commit()
                await cur.execute("SELECT LAST_INSERT_ID()")
                server_id = await cur.fetchone()
            server_id = server_id[0]

            cpu_value = round(float(cpu_usage), 2) if cpu_usage != "Unknown" else "Unknown"
            mem_value = round(memory_usage, 2) if memory_usage != "Unknown" else "Unknown"

            await cur.execute(
                "INSERT INTO cpu_usages (server_id, cpu_usage, timestamp) VALUES (%s, %s, %s)",
                (server_id, cpu_value, current_time),
            )
            await cur.execute(
                "INSERT INTO memory_usages (server_id, memory_usage, timestamp) VALUES (%s, %s, %s)",
                (server_id, mem_value, current_time),
            )

            for user in active_users:
                await cur.execute(
                    "INSERT INTO active_users (server_id, username, timestamp) VALUES (%s, %s, %s)",
                    (server_id, user, current_time),
                )

            for ip in active_ip:
                await cur.execute(
                    """
                    INSERT INTO active_ip (server_id, ip_address, timestamp) VALUES (%s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                        ip_address = new.ip_address,
                        timestamp = new.timestamp
                    """,
                    (server_id, ip, current_time),
                )


async def query_latest_check_time(db_pool) -> Optional[str]:
    """
    Fetch the latest connectivity check timestamp.

    Parameters:
        db_pool: Aiomysql connection pool.
    Returns:
        Optional[str]: Latest check time or None.
    Raises:
        None
    """
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
                await cursor.execute(query)
                result = await cursor.fetchone()
                return result[0] if result else None
    except Exception as exc:
        print(f"Error fetching latest check time: {exc}")
        return None


async def get_servers_from_db(latest_check_time: Optional[str], db_pool) -> List[str]:
    """
    Fetch connectable servers based on the latest connectivity check.

    Parameters:
        latest_check_time (Optional[str]): Latest check timestamp.
        db_pool: Aiomysql connection pool.
    Returns:
        List[str]: List of server hosts.
    Raises:
        None
    """
    servers: List[str] = []
    if latest_check_time:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT s.host
                    FROM servers s
                    JOIN server_connectivity sc ON s.server_id = sc.server_id
                    WHERE sc.last_checked = %s AND sc.is_connectable = TRUE
                    """,
                    (latest_check_time,),
                )
                server_records = await cur.fetchall()
                for record in server_records:
                    servers.append(record[0])
    return servers


async def main() -> None:
    """
    Orchestrate usage collection and database updates.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    async with get_db_pool() as db_pool:
        latest_check_time = await query_latest_check_time(db_pool)
        server_ips = await get_servers_from_db(latest_check_time, db_pool)
        if not server_ips:
            print("No connectable servers found in the database.")
            return

        tasks = [get_server_usage(ip) for ip in server_ips]
        results = await asyncio.gather(*tasks)

        update_tasks = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for result in results:
            if isinstance(result, tuple):
                host, cpu_usage, memory_usage, active_users, active_ip = result
                update_tasks.append(
                    update_database(
                        host,
                        cpu_usage,
                        memory_usage,
                        active_users,
                        active_ip,
                        current_time,
                        db_pool,
                    )
                )

        await asyncio.gather(*update_tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"An error occurred: {exc}")
