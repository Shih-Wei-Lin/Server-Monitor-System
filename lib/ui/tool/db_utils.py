"""
Database helpers for the Streamlit UI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pymysql
import streamlit as st

from lib.config import DefaultConfig

DB_CONFIG = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}


def get_database_connection() -> pymysql.connections.Connection:
    """
    Create a MySQL connection using the configured credentials.

    Parameters:
        None
    Returns:
        pymysql.connections.Connection: Open database connection.
    Raises:
        Exception: If the connection attempt fails.
    """
    try:
        return pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            db=DB_CONFIG["db"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.MySQLError as exc:
        raise Exception(f"Failed to connect to database: {exc}")


def query_latest_check_time(connection: pymysql.connections.Connection) -> Optional[str]:
    """
    Fetch the latest connectivity check timestamp.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
    Returns:
        Optional[str]: Latest check timestamp or None.
    Raises:
        None
    """
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
            cursor.execute(query)
            result = cursor.fetchone()
            return result["last_checked"] if result and result["last_checked"] else None
    except Exception as exc:
        print(f"Error fetching latest check time: {exc}")
        return None


def get_latest_average_timestamp(connection: pymysql.connections.Connection) -> Optional[str]:
    """
    Fetch the latest metrics average timestamp.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
    Returns:
        Optional[str]: Latest average timestamp or None.
    Raises:
        None
    """
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(average_timestamp) AS latest_timestamp FROM server_metrics_averages"
            cursor.execute(query)
            result = cursor.fetchone()
            return result["latest_timestamp"] if result and result["latest_timestamp"] else None
    except Exception as exc:
        print(f"Error fetching latest average timestamp: {exc}")
        return None


def query_latest_server_connectivity(
    connection: pymysql.connections.Connection,
) -> List[Dict[str, Any]]:
    """
    Fetch the latest connectivity status for all servers.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
    Returns:
        List[Dict[str, Any]]: List of server connectivity records.
    Raises:
        None
    """
    with connection.cursor() as cursor:
        query = """
            SELECT
                s.server_id,
                s.host,
                s.CPU_info,
                s.GPU_info,
                s.core_info,
                s.logical_process_info,
                s.Memory_size_info,
                s.System_OS_info,
                sc.is_connectable
            FROM servers s
            LEFT JOIN (
                SELECT
                    sc1.server_id,
                    sc1.is_connectable,
                    sc1.last_checked
                FROM server_connectivity sc1
                INNER JOIN (
                    SELECT server_id, MAX(last_checked) AS max_last_checked
                    FROM server_connectivity
                    GROUP BY server_id
                ) sc2
                ON sc1.server_id = sc2.server_id AND sc1.last_checked = sc2.max_last_checked
            ) sc ON s.server_id = sc.server_id
        """
        cursor.execute(query)
        return cursor.fetchall()


def query_recent_server_data(
    connection: pymysql.connections.Connection, server_id: int, num_records: int = 15
) -> List[Dict[str, Any]]:
    """
    Fetch recent CPU and memory usage for a server.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
        num_records (int): Number of records to return.
    Returns:
        List[Dict[str, Any]]: Ordered list of recent usage records.
    Raises:
        None
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT * FROM (
                SELECT
                    c.timestamp,
                    c.cpu_usage,
                    m.memory_usage
                FROM cpu_usages AS c
                INNER JOIN memory_usages AS m
                    ON c.server_id = m.server_id AND c.timestamp = m.timestamp
                WHERE c.server_id = %s
                ORDER BY c.timestamp DESC
                LIMIT %s
            ) AS subquery
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (server_id, num_records))
        return cursor.fetchall()


def get_latest_timestamp(connection: pymysql.connections.Connection) -> Optional[str]:
    """
    Fetch the latest CPU usage timestamp.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
    Returns:
        Optional[str]: Latest timestamp or None.
    Raises:
        None
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(timestamp) AS latest_timestamp FROM cpu_usages")
        result = cursor.fetchone()
        return result["latest_timestamp"] if result["latest_timestamp"] else None


def query_server_usage(
    connection: pymysql.connections.Connection, latest_timestamp: str
) -> List[Dict[str, Any]]:
    """
    Fetch CPU and memory usage for all servers at a timestamp.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        latest_timestamp (str): Timestamp to query.
    Returns:
        List[Dict[str, Any]]: List of server usage records.
    Raises:
        None
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT
                c.server_id,
                c.cpu_usage,
                m.memory_usage
            FROM cpu_usages AS c
            INNER JOIN memory_usages AS m
                ON c.server_id = m.server_id AND c.timestamp = m.timestamp
            WHERE c.timestamp = %s
        """
        cursor.execute(query, (latest_timestamp,))
        return cursor.fetchall()


def get_disk_c_usage(
    connection: pymysql.connections.Connection, server_id: int
) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest C drive usage for a server.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
    Returns:
        Optional[Dict[str, Any]]: Disk usage record or None.
    Raises:
        None
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT total_capacity_gb, remaining_capacity_gb
            FROM server_disk_C_storage
            WHERE server_id = %s
            ORDER BY last_checked DESC
            LIMIT 1
        """
        cursor.execute(query, (server_id,))
        return cursor.fetchone()


def get_active_users(
    connection: pymysql.connections.Connection, server_id: int, latest_timestamp: str
) -> List[Dict[str, Any]]:
    """
    Fetch active users for a server at or before the given timestamp.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
        latest_timestamp (str): Timestamp to query.
    Returns:
        List[Dict[str, Any]]: Active user records.
    Raises:
        None
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT username, timestamp
            FROM active_users
            WHERE server_id = %s AND timestamp = (
                SELECT MAX(timestamp)
                FROM active_users
                WHERE server_id = %s AND timestamp <= %s
            )
        """
        cursor.execute(query, (server_id, server_id, latest_timestamp))
        return cursor.fetchall()


def get_active_user_names(
    connection: pymysql.connections.Connection, server_id: int, latest_timestamp: str
) -> List[Dict[str, Any]]:
    """
    Fetch mapped user names from active IPs for a server.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
        latest_timestamp (str): Timestamp to query.
    Returns:
        List[Dict[str, Any]]: Active user name records.
    Raises:
        None
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT u.user_name, a.timestamp
            FROM active_ip AS a
            INNER JOIN user_ip_map AS u ON a.ip_address = u.ip_address
            WHERE a.server_id = %s AND a.timestamp = (
                SELECT MAX(timestamp)
                FROM active_ip
                WHERE server_id = %s AND timestamp <= %s
            )
        """
        cursor.execute(query, (server_id, server_id, latest_timestamp))
        return cursor.fetchall()


def get_active_users_and_names(
    connection: pymysql.connections.Connection, server_id: int, latest_timestamp: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch active users and mapped user names in one call.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
        latest_timestamp (str): Timestamp to query.
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Active users and mapped names.
    Raises:
        None
    """
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            query_active_users = """
                SELECT username, timestamp
                FROM active_users
                WHERE server_id = %s AND timestamp = (
                    SELECT MAX(timestamp)
                    FROM active_users
                    WHERE server_id = %s AND timestamp <= %s
                )
            """
            cursor.execute(query_active_users, (server_id, server_id, latest_timestamp))
            active_users = cursor.fetchall()

            query_active_user_names = """
                SELECT u.user_name, a.timestamp
                FROM active_ip AS a
                INNER JOIN user_ip_map AS u ON a.ip_address = u.ip_address
                WHERE a.server_id = %s AND a.timestamp = (
                    SELECT MAX(timestamp)
                    FROM active_ip
                    WHERE server_id = %s AND timestamp <= %s
                )
            """
            cursor.execute(query_active_user_names, (server_id, server_id, latest_timestamp))
            active_usernames = cursor.fetchall()

            return active_users, active_usernames
    except Exception as exc:
        st.error(f"Error fetching active users and names: {exc}")
        return [], []


def get_server_metrics_averages(
    connection: pymysql.connections.Connection, server_id: int, start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    """
    Fetch averaged metrics for a server and date range.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
        server_id (int): Server identifier.
        start_date (str): Start date time string.
        end_date (str): End date time string.
    Returns:
        List[Dict[str, Any]]: Metrics average records.
    Raises:
        None
    """
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT *
                FROM server_metrics_averages
                WHERE server_id = %s AND average_timestamp BETWEEN %s AND %s
            """
            cursor.execute(query, (server_id, start_date, end_date))
            return cursor.fetchall()
    except Exception as exc:
        st.error(f"Error fetching server metrics averages: {exc}")
        return []


def get_server_ids(connection: pymysql.connections.Connection) -> List[int]:
    """
    Fetch all server identifiers.

    Parameters:
        connection (pymysql.connections.Connection): Active database connection.
    Returns:
        List[int]: List of server IDs.
    Raises:
        None
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT server_id FROM servers")
            server_ids = cursor.fetchall()
            return [server["server_id"] for server in server_ids]
    except Exception as exc:
        st.error(f"Error fetching server IDs: {exc}")
        return []
