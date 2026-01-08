"""
Aggregate high-frequency metrics into 10-minute averages.
"""

from __future__ import annotations

import pymysql

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
    Create a database connection.

    Parameters:
        None
    Returns:
        pymysql.connections.Connection: Open connection.
    Raises:
        Exception: If the connection fails.
    """
    try:
        return pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            db=DB_CONFIG["db"],
            charset=DB_CONFIG["charset"],
            autocommit=DB_CONFIG["autocommit"],
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.MySQLError as exc:
        raise Exception(f"Failed to connect to database: {exc}")


def execute_sql_commands() -> None:
    """
    Aggregate usage data and truncate raw tables.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        with connection.cursor() as cursor:
            insert_query = """
                INSERT INTO server_metrics_averages
                    (server_id, average_cpu_usage, average_memory_usage, average_active_users, average_timestamp)
                SELECT
                    cpu_data.server_id,
                    cpu_data.average_cpu_usage,
                    mem_data.average_memory_usage,
                    IFNULL(user_data.average_active_users, 0),
                    cpu_data.period_start
                FROM
                    (SELECT
                        server_id,
                        ROUND(AVG(cpu_usage), 2) AS average_cpu_usage,
                        FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(timestamp) / 600) * 600) AS period_start
                    FROM cpu_usages
                    GROUP BY server_id, period_start) AS cpu_data
                JOIN
                    (SELECT
                        server_id,
                        ROUND(AVG(memory_usage), 2) AS average_memory_usage,
                        FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(timestamp) / 600) * 600) AS period_start
                    FROM memory_usages
                    GROUP BY server_id, period_start) AS mem_data
                ON cpu_data.server_id = mem_data.server_id AND cpu_data.period_start = mem_data.period_start
                LEFT JOIN
                    (SELECT
                        server_id,
                        COUNT(DISTINCT username) AS average_active_users,
                        FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(timestamp) / 600) * 600) AS period_start
                    FROM active_users
                    GROUP BY server_id, period_start) AS user_data
                ON cpu_data.server_id = user_data.server_id AND cpu_data.period_start = user_data.period_start
                ON DUPLICATE KEY UPDATE
                    average_cpu_usage = VALUES(average_cpu_usage),
                    average_memory_usage = VALUES(average_memory_usage),
                    average_active_users = VALUES(average_active_users)
            """

            cursor.execute(insert_query)

            truncate_queries = [
                "TRUNCATE TABLE cpu_usages",
                "TRUNCATE TABLE memory_usages",
                "TRUNCATE TABLE active_users",
                "TRUNCATE TABLE active_ip",
                "OPTIMIZE TABLE cpu_usages, memory_usages, active_users, active_ip",
            ]
            for query in truncate_queries:
                cursor.execute(query)

        connection.commit()
    except pymysql.MySQLError as exc:
        print(f"SQL execution failed: {exc}")
    finally:
        connection.close()


def main() -> None:
    """
    Entry point for data compression.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    execute_sql_commands()


if __name__ == "__main__":
    main()
