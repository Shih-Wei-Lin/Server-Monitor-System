import pymysql
from db_config import DefaultConfig
import streamlit as st
# 添加第一组和第二组预设的用户凭证
DEFAULT_USERNAME = DefaultConfig.DEFAULT_USERNAME
DEFAULT_PASSWORD = DefaultConfig.DEFAULT_PASSWORD
SECONDARY_USERNAME = DefaultConfig.SECONDARY_USERNAME
SECONDARY_PASSWORD = DefaultConfig.SECONDARY_PASSWORD

db_config = {
    'host': DefaultConfig.HOST,
    'port': DefaultConfig.PORT,
    'user': DefaultConfig.USER,
    'password': DefaultConfig.PASSWORD,
    'db': DefaultConfig.DB,
    'charset': DefaultConfig.CHARSET,
    'autocommit': DefaultConfig.AUTO_COMMIT
}


# 建立數據庫連接
def get_database_connection():
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        raise Exception(f"無法連接到數據庫：{e}")

# 在需要数据库连接的函数中使用上下文管理器
def query_latest_check_time(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
            cursor.execute(query)
            result = cursor.fetchone()
            return result['last_checked'] if result and result['last_checked'] else None
    except Exception as e:
        print(f"Error fetching latest check time: {e}")
        return None

def get_latest_average_timestamp(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(average_timestamp) AS latest_timestamp FROM server_metrics_averages"
            cursor.execute(query)
            result = cursor.fetchone()
            return result['latest_timestamp'] if result and result['latest_timestamp'] else None
    except Exception as e:
        print(f"Error fetching latest average timestamp: {e}")
        return None


# 查詢每個伺服器最新的檢查時間記錄和伺服器資訊
def query_latest_server_connectivity(connection):
    
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



def query_recent_server_data(connection, server_id, num_records=15):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
        SELECT * FROM (
            SELECT
                c.timestamp,
                c.cpu_usage,
                m.memory_usage
            FROM cpu_usages AS c
            INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp
            WHERE c.server_id = %s
            ORDER BY c.timestamp DESC
            LIMIT %s
        ) AS subquery
        ORDER BY timestamp ASC
        """
        cursor.execute(query, (server_id, num_records))
        return cursor.fetchall()

# 获取最新的 timestamp 从 cpu_usages 表
def get_latest_timestamp(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(timestamp) AS latest_timestamp FROM cpu_usages")
        result = cursor.fetchone()
        return result['latest_timestamp'] if result['latest_timestamp'] else None
        


def query_server_usage(connection,latest_timestamp):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
        SELECT
            c.server_id,
            c.cpu_usage,
            m.memory_usage
        FROM cpu_usages AS c
        INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp 
        WHERE c.timestamp = %s
        """
        cursor.execute(query, (latest_timestamp,))
        return cursor.fetchall()

def get_disk_c_usage(connection,server_id):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT total_capacity_gb, remaining_capacity_gb
            FROM server_disk_C_storage
            WHERE server_id = %s
            ORDER BY last_checked DESC
            LIMIT 1;
            """
        cursor.execute(query, (server_id,))
        result = cursor.fetchone()
        return result



def get_active_users(connection,server_id, latest_timestamp):
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

def get_active_user_names(connection, server_id, latest_timestamp):
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

def get_active_users_and_names(connection, server_id, latest_timestamp):
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 查询 active_users 数据
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

            # 查询 active_user_names 数据
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
    except Exception as e:
        st.error(f"Error fetching active users and names: {e}")
        return [], []
    
# 查询数据库中的平均使用率数据
def get_server_metrics_averages(connection, server_id, start_date, end_date):
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT *
            FROM server_metrics_averages
            WHERE server_id = %s AND average_timestamp BETWEEN %s AND %s;
            """
            cursor.execute(query, (server_id, start_date, end_date))
            result = cursor.fetchall()
            return result
    except Exception as e:
        st.error(f"Error fetching server metrics averages: {e}")
        return []
    
def get_server_ids(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT server_id FROM servers;"
            cursor.execute(query)
            server_ids = cursor.fetchall()
            return [server['server_id'] for server in server_ids]
    except Exception as e:
        st.error(f"Error fetching server IDs: {e}")
        return []