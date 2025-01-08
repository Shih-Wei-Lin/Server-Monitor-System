import asyncio
import asyncssh
import aiomysql
import re
from datetime import datetime
from contextlib import asynccontextmanager
from db_config import DefaultConfig

# 预编译正则表达式
memory_pattern = re.compile(r"FreePhysicalMemory=(\d+)\s+TotalVisibleMemorySize=(\d+)", re.IGNORECASE)
cpu_pattern = re.compile(r'"(\d+.\d+)"')
user_pattern = re.compile(r"(\w+)\s+\S+\s+\d+\s+Active", re.MULTILINE)
disk_pattern = re.compile(r"FreeSpace=(\d+)", re.IGNORECASE)
ip_pattern = re.compile(r'\s192\.168\.1\.\d+:3389\s+(192\.168\.1\.\d+)', re.MULTILINE)

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

def bytes_to_gb(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)  # 将字节转换为 GB 并保留两位小数

@asynccontextmanager
async def get_db_pool():
    pool = await aiomysql.create_pool(**db_config)
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()


async def get_server_usage(host,connect_timeout=10):
    # 尝试连接的内部函数
    async def try_connect(username, password):
        try:
            async with asyncssh.connect(host, username=username, password=password,connect_timeout=connect_timeout) as conn:
                command = ("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value & "
                           "typeperf \"\\Processor Information(_Total)\\% Processor Time\" -sc 1 & "
                           "query user & "
                           "wmic LOGICALDISK WHERE Name='C:' get FreeSpace /Value &"
                           "netstat -an | findstr \"192.168.1.*:3389\""
                           )
                result = await conn.run(command)
                output = result.stdout
                # 内存使用率
                memory_match = memory_pattern.search(output)
                if memory_match is not None:
                    free_memory = int(memory_match.group(1))
                    total_memory = int(memory_match.group(2))
                    memory_usage = (total_memory - free_memory) / total_memory * 100
                else:
                    memory_usage = "Unknown"
                    
                # CPU 使用率
                cpu_usage_match = cpu_pattern.search(output)
                if cpu_usage_match is not None:
                    cpu_usage = float(cpu_usage_match.group(1)) 
                else: 
                    cpu_usage ="Unknown"

                # 活跃用户
                active_users = user_pattern.findall(output)
                # 活躍ip 
                active_ip = ip_pattern.findall(output)
                    
                    
                return (host, cpu_usage, memory_usage, active_users,active_ip)
        except (asyncssh.Error, asyncio.TimeoutError) as e:
            print(f"Connect to {host} failed or time out:{e}")
            return None

    result = await try_connect(DEFAULT_USERNAME, DEFAULT_PASSWORD)
    if result is None:
        result = await try_connect(SECONDARY_USERNAME, SECONDARY_PASSWORD)
    if result is None:
        print(f"Error connecting to {host}: Both credential sets failed.")
        return (host, "Error", "Error", [], "Error")
    return result

async def update_database(host, cpu_usage, memory_usage, active_users,active_ip, current_time, db_pool):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 获取或创建 server_id
            await cur.execute("SELECT server_id FROM servers WHERE host = %s", (host,))
            server_id = await cur.fetchone()
            if server_id is None:
                await cur.execute("INSERT INTO servers (host) VALUES (%s)", (host,))
                await conn.commit()
                await cur.execute("SELECT LAST_INSERT_ID()")
                server_id = await cur.fetchone()
            server_id = server_id[0]
            cpu_usage = round(float(cpu_usage), 2) if cpu_usage != "Unknown" else "Unknown"
            memory_usage = round(memory_usage, 2) if memory_usage != "Unknown" else "Unknown"
            # 将磁盘空间从字节转换为 GB


            # 插入 CPU 使用率
            await cur.execute("INSERT INTO cpu_usages (server_id, cpu_usage, timestamp) VALUES (%s, %s, %s)",
                              (server_id, cpu_usage, current_time))
            # 插入内存使用率
            await cur.execute("INSERT INTO memory_usages (server_id, memory_usage, timestamp) VALUES (%s, %s, %s)",
                              (server_id, memory_usage, current_time))
            # 插入活跃用户
            for user in active_users:
                await cur.execute("INSERT INTO active_users (server_id, username, timestamp) VALUES (%s, %s, %s)",
                                  (server_id, user, current_time))
            # 插入活跃ip
            for ip in active_ip:
                await cur.execute("""INSERT INTO active_ip (server_id, ip_address, timestamp) VALUES (%s, %s, %s) AS new
                                  ON Duplicate Key update
                                  ip_address = new.ip_address,
                                  timestamp = new.timestamp
                                  """,
                                  (server_id, ip, current_time))
            #await conn.commit()

async def query_latest_check_time(db_pool):
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
                await cursor.execute(query)
                result = await cursor.fetchone()
                # print(f"fetchall:{result}")
                return result[0] if result else None
    except Exception as e:
        print(f"Error fetching latest check time: {e}")
        return None
    
async def get_servers_from_db(latest_check_time, db_pool):
    servers = []
    if latest_check_time:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 使用最新的检查时间来过滤服务器
                await cur.execute("""
                    SELECT s.host
                    FROM servers s
                    JOIN server_connectivity sc ON s.server_id = sc.server_id
                    WHERE sc.last_checked = %s AND sc.is_connectable = TRUE
                """, (latest_check_time,))
                server_records = await cur.fetchall()
                for record in server_records:
                    host = record[0]
                    servers.append(host)
    return servers

async def main():
    async with get_db_pool() as db_pool:
        # 先获取最新的检查时间
        latest_check_time = await query_latest_check_time(db_pool)
        # print(latest_check_time)
        # 然后使用这个时间戳来获取服务器列表
        server_ips= await get_servers_from_db(latest_check_time, db_pool)
        # for ip in server_ips:
        #      print(ip)
        if not server_ips:
            print("No connectable servers found in the database.")
            return
        # 获取服务器资源使用情况并更新数据库
        tasks = [get_server_usage(ip) for ip in server_ips]
        results = await asyncio.gather(*tasks)
        update_tasks = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for result in results:
            if isinstance(result, tuple):
                host, cpu_usage, memory_usage, active_users,active_ip = result
                update_tasks.append(update_database(host, cpu_usage, memory_usage, active_users,active_ip, current_time, db_pool))
        await asyncio.gather(*update_tasks)

# 程序入口
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")
