import pymysql
from db_config import DefaultConfig
import streamlit as st
from contextlib import contextmanager

# 添加第一组和第二组预设的用户凭证
DEFAULT_USERNAME = DefaultConfig.DEFAULT_USERNAME
DEFAULT_PASSWORD = DefaultConfig.DEFAULT_PASSWORD
SECONDARY_USERNAME = DefaultConfig.SECONDARY_USERNAME
SECONDARY_PASSWORD = DefaultConfig.SECONDARY_PASSWORD

# 數據庫配置
db_config = {
    'host': DefaultConfig.HOST,
    'port': DefaultConfig.PORT,
    'user': DefaultConfig.USER,
    'password': DefaultConfig.PASSWORD,
    'db': DefaultConfig.DB,
    'charset': DefaultConfig.CHARSET,
    'autocommit': DefaultConfig.AUTO_COMMIT
}

# 使用上下文管理器來確保資料庫連接的安全關閉
@contextmanager
def get_database_connection():
    connection = None
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        yield connection
    except pymysql.MySQLError as e:
        raise Exception(f"無法連接到數據庫：{e}")
    finally:
        if connection:
            connection.close()

# 通用的查詢執行函數，用於減少重複代碼
def execute_query(connection, query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

# 查詢最新的檢查時間
def query_latest_check_time(connection):
    query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
    result = execute_query(connection, query)
    return result[0]['last_checked'] if result and result[0]['last_checked'] else None

# 獲取最新的平均時間戳
def get_latest_average_timestamp(connection):
    query = "SELECT MAX(average_timestamp) AS latest_timestamp FROM server_metrics_averages"
    result = execute_query(connection, query)
    return result[0]['latest_timestamp'] if result and result[0]['latest_timestamp'] else None

# 查詢每個伺服器最新的檢查時間記錄和伺服器資訊
def query_latest_server_connectivity(connection):
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
    return execute_query(connection, query)

# 查詢伺服器最近的資料
def query_recent_server_data(connection, server_id, num_records=15):
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
    return execute_query(connection, query, (server_id, num_records))

# 獲取最新的時間戳
def get_latest_timestamp(connection):
    query = "SELECT MAX(timestamp) AS latest_timestamp FROM cpu_usages"
    result = execute_query(connection, query)
    return result[0]['latest_timestamp'] if result and result[0]['latest_timestamp'] else None

# 查詢伺服器使用情況
def query_server_usage(connection, latest_timestamp):
    query = """
    SELECT
        c.server_id,
        c.cpu_usage,
        m.memory_usage
    FROM cpu_usages AS c
    INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp 
    WHERE c.timestamp = %s
    """
    return execute_query(connection, query, (latest_timestamp,))

# 獲取伺服器磁盤C的使用情況
def get_disk_c_usage(connection, server_id):
    query = """
        SELECT total_capacity_gb, remaining_capacity_gb
        FROM server_disk_C_storage
        WHERE server_id = %s
        ORDER BY last_checked DESC
        LIMIT 1;
        """
    result = execute_query(connection, query, (server_id,))
    return result[0] if result else None

# 獲取活躍用戶
def get_active_users(connection, server_id, latest_timestamp):
    query = """
        SELECT username, timestamp
        FROM active_users
        WHERE server_id = %s AND timestamp = (
            SELECT MAX(timestamp)
            FROM active_users
            WHERE server_id = %s AND timestamp <= %s
        )
        """
    return execute_query(connection, query, (server_id, server_id, latest_timestamp))

# 獲取活躍用戶名稱
def get_active_user_names(connection, server_id, latest_timestamp):
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
    return execute_query(connection, query, (server_id, server_id, latest_timestamp))

# 同時獲取活躍用戶和用戶名稱
def get_active_users_and_names(connection, server_id, latest_timestamp):
    try:
        active_users = get_active_users(connection, server_id, latest_timestamp)
        active_usernames = get_active_user_names(connection, server_id, latest_timestamp)
        return active_users, active_usernames
    except Exception as e:
        st.error(f"Error fetching active users and names: {e}")
        return [], []

# 查詢伺服器的平均使用率數據
def get_server_metrics_averages(connection, server_id, start_date, end_date):
    query = """
    SELECT *
    FROM server_metrics_averages
    WHERE server_id = %s AND average_timestamp BETWEEN %s AND %s;
    """
    return execute_query(connection, query, (server_id, start_date, end_date))

# 獲取所有伺服器的ID
def get_server_ids(connection):
    try:
        query = "SELECT server_id FROM servers;"
        server_ids = execute_query(connection, query)
        return [server['server_id'] for server in server_ids]
    except Exception as e:
        st.error(f"Error fetching server IDs: {e}")
        return []