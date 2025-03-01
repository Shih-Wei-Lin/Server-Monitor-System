import asyncio
import asyncssh
import aiomysql
from datetime import datetime
from db_config import DefaultConfig
import re
from contextlib import asynccontextmanager

# 配置信息
USERNAME = DefaultConfig.DEFAULT_USERNAME
PASSWORD = DefaultConfig.DEFAULT_PASSWORD
db_config = {
    'host': DefaultConfig.HOST,
    'port': DefaultConfig.PORT,
    'user': DefaultConfig.USER,
    'password': DefaultConfig.PASSWORD,
    'db': DefaultConfig.DB,
    'charset': DefaultConfig.CHARSET,
    'autocommit': DefaultConfig.AUTO_COMMIT
}

# 預編譯正則表達式
disk_info_pattern = re.compile(r'(\d+)\s+(\d+)')

@asynccontextmanager
async def get_db_pool():
    """建立和管理資料庫連接池的上下文管理器"""
    pool = await aiomysql.create_pool(**db_config)
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()

async def test_server_connectivity_and_disk(last_checked, server, db_pool):
    """測試服務器連接性和磁盤空間"""
    server_id = server['server_id']
    is_connectable = False
    total_capacity_gb, remaining_capacity_gb = None, None
    
    try:
        # 嘗試通過SSH連接服務器
        async with asyncssh.connect(
            server['host'],
            username=USERNAME,
            password=PASSWORD,
            known_hosts=None,
            connect_timeout=1.5
        ) as conn:
            is_connectable = True
            
            # 既然已經連接成功，檢查磁盤信息
            try:
                # 執行wmic命令來獲取C盤的磁盤空間信息
                result = await conn.run('wmic LogicalDisk where DeviceID="C:" get Size,FreeSpace', check=True)
                total_capacity_gb, remaining_capacity_gb = parse_disk_info(result.stdout)
            except Exception as e:
                print(f'Disk check failed for {server["host"]}: {str(e)}')
    except (OSError, asyncssh.Error) as e:
        print(f'Connection failed to {server["host"]}: {str(e)}')
        is_connectable = False
    
    # 批量更新資料庫 - 使用事務減少開銷
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 更新連接性信息
            await cursor.execute("""
                INSERT INTO server_connectivity (server_id, is_connectable, last_checked)
                VALUES (%s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                is_connectable = new.is_connectable,
                last_checked = new.last_checked
            """, (server_id, is_connectable, last_checked))
            
            # 如果有磁盤信息，更新磁盤信息
            if total_capacity_gb and remaining_capacity_gb:
                await cursor.execute("""
                    INSERT INTO server_disk_C_storage (server_id, total_capacity_gb, remaining_capacity_gb, last_checked)
                    VALUES (%s, %s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                    total_capacity_gb = new.total_capacity_gb,
                    remaining_capacity_gb = new.remaining_capacity_gb,
                    last_checked = new.last_checked
                """, (server_id, total_capacity_gb, remaining_capacity_gb, last_checked))
            
            # 只執行一次提交，減少資料庫交互
            await conn.commit()
            
def parse_disk_info(disk_output):
    """解析磁盤信息輸出"""
    match = disk_info_pattern.search(disk_output.strip())
    if match:
        # 提取剩余空間和總大小
        remaining_capacity_bytes = int(match.group(1))
        total_capacity_bytes = int(match.group(2))
        # 轉換為GB，保留兩位小數
        total_capacity_gb = round(total_capacity_bytes / (1024**3), 2)
        remaining_capacity_gb = round(remaining_capacity_bytes / (1024**3), 2)
        return total_capacity_gb, remaining_capacity_gb
    else:
        return None, None

async def main():
    """主程序入口"""
    last_checked = datetime.now()
    
    # 使用上下文管理器管理資料庫連接池
    async with get_db_pool() as db_pool:
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 獲取服務器列表
                await cursor.execute("SELECT server_id, host FROM servers")
                servers = await cursor.fetchall()
        
        # 測試所有服務器的連接性和磁盤
        tasks = [test_server_connectivity_and_disk(last_checked, server, db_pool) for server in servers]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")