import pymysql

from lib.db_config import DefaultConfig

db_config = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}


# 建立数据库连接
def get_database_connection():
    try:
        connection = pymysql.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            db=db_config["db"],
            charset=db_config["charset"],
            autocommit=db_config["autocommit"],
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"无法连接到数据库：{e}")
        exit()


# 执行SQL命令
def execute_sql_commands():
    connection = get_database_connection()
    try:
        with connection.cursor() as cursor:
            # 插入数据到 server_metrics_averages
            insert_query = (
                insert_query
            ) = """
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
                            average_active_users = VALUES(average_active_users);
                    """

            cursor.execute(insert_query)

            # 清空表
            truncate_queries = [
                "TRUNCATE TABLE cpu_usages;",
                "TRUNCATE TABLE memory_usages;",
                "TRUNCATE TABLE active_users;",
                "TRUNCATE TABLE active_ip;",
                "optimize table cpu_usages,memory_usages,active_users,active_ip ;",
            ]
            for query in truncate_queries:
                cursor.execute(query)

        connection.commit()
    except pymysql.MySQLError as e:
        print(f"执行SQL命令时出错：{e}")
    finally:
        connection.close()


def main():
    execute_sql_commands()


if __name__ == "__main__":
    main()
