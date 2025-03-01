import asyncio
import asyncssh
import aiomysql
import re
from datetime import datetime
from contextlib import asynccontextmanager
from db_config import DefaultConfig

# 預編譯正則表達式
memory_pattern = re.compile(r"FreePhysicalMemory=(\d+)\s+TotalVisibleMemorySize=(\d+)", re.IGNORECASE)
cpu_pattern = re.compile(r'"(\d+.\d+)"')
user_pattern = re.compile(r"(\w+)\s+\S+\s+\d+\s+Active", re.MULTILINE)
disk_pattern = re.compile(r"FreeSpace=(\d+)", re.IGNORECASE)
ip_pattern = re.compile(r'\s192\.168\.1\.\d+:3389\s+(192\.168\.1\.\d+)', re.MULTILINE)

# 添加第一組和第二組預設的用戶憑證
CREDENTIALS = [
    (DefaultConfig.DEFAULT_USERNAME, DefaultConfig.DEFAULT_PASSWORD),
    (DefaultConfig.SECONDARY_USERNAME, DefaultConfig.SECONDARY_PASSWORD)
]

db_config = {
    'host': DefaultConfig.HOST,
    'port': DefaultConfig.PORT,
    'user': DefaultConfig.USER,
    'password': DefaultConfig.PASSWORD,
    'db': DefaultConfig.DB,
    'charset': DefaultConfig.CHARSET,
    'autocommit': DefaultConfig.AUTO_COMMIT
}

def bytes_to_gb(bytes_value):
    """將字節轉換為 GB 並保留兩位小數"""
    return round(bytes_value / (1024 ** 3), 2)

@asynccontextmanager
async def get_db_pool():
    """數據庫連接池上下文管理器"""
    pool = await aiomysql.create_pool(**db_config)
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()

async def get_server_usage(host, connect_timeout=10):
    """獲取服務器使用情況，使用憑證列表嘗試連接"""
    command = (
        "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value & "
        "typeperf \"\\Processor Information(_Total)\\% Processor Time\" -sc 1 & "
        "query user & "
        "wmic LOGICALDISK WHERE Name='C:' get FreeSpace /Value &"
        "netstat -an | findstr \"192.168.1.*:3389\""
    )
    
    # 嘗試每組憑證
    for username, password in CREDENTIALS:
        try:
            async with asyncssh.connect(
                host, 
                username=username, 
                password=password,
                connect_timeout=connect_timeout
            ) as conn:
                result = await conn.run(command)
                output = result.stdout
                
                # 內存使用率
                memory_match = memory_pattern.search(output)
                memory_usage = "Unknown"
                if memory_match is not None:
                    free_memory = int(memory_match.group(1))
                    total_memory = int(memory_match.group(2))
                    memory_usage = (total_memory - free_memory) / total_memory * 100
                
                # CPU 使用率
                cpu_usage = "Unknown"
                cpu_usage_match = cpu_pattern.search(output)
                if cpu_usage_match is not None:
                    cpu_usage = float(cpu_usage_match.group(1))
                
                # 活躍用戶和IP
                active_users = user_pattern.findall(output)
                active_ip = ip_pattern.findall(output)
                
                return (host, cpu_usage, memory_usage, active_users, active_ip)
        except (asyncssh.Error, asyncio.TimeoutError) as e:
            print(f"Failed to connect to {host} using {username}: {e}")
            continue
    
    # 所有憑證都失敗
    print(f"Error connecting to {host}: All credential sets failed.")
    return (host, "Error", "Error", [], [])

async def update_database(host, cpu_usage, memory_usage, active_users, active_ip, current_time, db_pool):
    """更新數據庫中的服務器信息"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 獲取服務器ID（如果不存在，則創建）
            await cur.execute("SELECT server_id FROM servers WHERE host = %s", (host,))
            server_id_result = await cur.fetchone()
            
            if server_id_result is None:
                await cur.execute("INSERT INTO servers (host) VALUES (%s)", (host,))
                await cur.execute("SELECT LAST_INSERT_ID()")
                server_id_result = await cur.fetchone()
            
            server_id = server_id_result[0]
            
            # 準備數據進行批量插入
            if cpu_usage != "Error" and memory_usage != "Error":
                # 轉換和四捨五入數值
                cpu_value = round(float(cpu_usage), 2) if cpu_usage != "Unknown" else None
                memory_value = round(float(memory_usage), 2) if memory_usage != "Unknown" else None
                
                # 批量插入性能數據
                await cur.execute(
                    "INSERT INTO cpu_usages (server_id, cpu_usage, timestamp) VALUES (%s, %s, %s)",
                    (server_id, cpu_value, current_time)
                )
                
                await cur.execute(
                    "INSERT INTO memory_usages (server_id, memory_usage, timestamp) VALUES (%s, %s, %s)",
                    (server_id, memory_value, current_time)
                )
            
            # 批量插入活躍用戶數據（如果有）
            if active_users:
                user_values = [(server_id, user, current_time) for user in active_users]
                await cur.executemany(
                    "INSERT INTO active_users (server_id, username, timestamp) VALUES (%s, %s, %s)",
                    user_values
                )
            
            # 更新活躍IP地址（如果有）
            if active_ip:
                ip_values = [(server_id, ip, current_time) for ip in active_ip]
                await cur.executemany(
                    """INSERT INTO active_ip (server_id, ip_address, timestamp) 
                    VALUES (%s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                    ip_address = new.ip_address,
                    timestamp = new.timestamp""",
                    ip_values
                )
            
            # 最後一次性提交所有事務
            await conn.commit()

async def get_connectable_servers(db_pool):
    """獲取可連接的服務器列表，使用索引優化查詢"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 獲取最新檢查時間並使用索引優化查詢
                query = """
                    SELECT s.host 
                    FROM servers s
                    JOIN (
                        SELECT server_id, MAX(last_checked) as latest_time
                        FROM server_connectivity
                        WHERE is_connectable = TRUE
                        GROUP BY server_id
                    ) sc ON s.server_id = sc.server_id
                    WHERE sc.latest_time = (
                        SELECT MAX(last_checked) 
                        FROM server_connectivity
                    )
                """
                await cursor.execute(query)
                results = await cursor.fetchall()
                return [result[0] for result in results]
    except Exception as e:
        print(f"Error fetching connectable servers: {e}")
        return []

async def main():
    """主程序入口"""
    try:
        async with get_db_pool() as db_pool:
            # 獲取可連接的服務器
            server_ips = await get_connectable_servers(db_pool)
            
            if not server_ips:
                print("No connectable servers found in the database.")
                return
            
            # 並發獲取所有服務器的使用情況
            tasks = [get_server_usage(ip) for ip in server_ips]
            results = await asyncio.gather(*tasks)
            
            # 更新數據庫
            current_time = datetime.now()
            update_tasks = []
            
            for result in results:
                if isinstance(result, tuple):
                    host, cpu_usage, memory_usage, active_users, active_ip = result
                    update_tasks.append(
                        update_database(host, cpu_usage, memory_usage, active_users, active_ip, current_time, db_pool)
                    )
            
            await asyncio.gather(*update_tasks)
            print(f"Update completed successfully at {current_time}")
    except Exception as e:
        print(f"An error occurred in main: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")