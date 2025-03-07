import asyncio
import os
import sys
from datetime import datetime

import aiomysql
import asyncssh

# Get the directory where the current script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# print(f"Current Directory: {current_dir}")

# Get the path of the parent directory, which should be the "ServerMonitor" directory
parent_dir = os.path.dirname(current_dir)
# print(f"Parent Directory: {parent_dir}")
root_dir = os.path.dirname(parent_dir)
# print(f"Root Directory: {root_dir}")
sys.path.append(root_dir)
import re

from lib.db_config import DefaultConfig

# 配置信息
USERNAME = DefaultConfig.DEFAULT_USERNAME
PASSWORD = DefaultConfig.DEFAULT_PASSWORD
db_config = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}

disk_info_pattern = re.compile(r"(\d+)\s+(\d+)")


async def test_server_disk_c_storage(last_checked, server, db_pool):
    try:
        # SSH连接到Windows服务器
        async with asyncssh.connect(
            server["host"],
            username=USERNAME,
            password=PASSWORD,
            known_hosts=None,
            connect_timeout=1.5,
        ) as conn:
            # 执行wmic命令来获取C盘的磁盘空间信息
            result = await conn.run(
                'wmic LogicalDisk where DeviceID="C:" get Size,FreeSpace', check=True
            )
            total_capacity, remaining_capacity = parse_disk_info(result.stdout)
    except (OSError, asyncssh.Error) as e:
        print(f'Disk check failed for {server["host"]}: {str(e)}')
        total_capacity, remaining_capacity = None, None
    if total_capacity and remaining_capacity:
        server_id = server["server_id"]
        # 更新数据库中的磁盘信息
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO server_disk_C_storage (server_id, total_capacity_gb, remaining_capacity_gb, last_checked)
                    VALUES (%s, %s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                    total_capacity_gb = new.total_capacity_gb,
                    remaining_capacity_gb = new.remaining_capacity_gb,
                    last_checked = new.last_checked
                """,
                    (server_id, total_capacity, remaining_capacity, last_checked),
                )
                await conn.commit()


async def test_server_connectivity_and_disk(last_checked, server, db_pool):
    is_connectable = False
    try:
        # 尝试通过SSH连接服务器
        async with asyncssh.connect(
            server["host"],
            username=USERNAME,
            password=PASSWORD,
            known_hosts=None,
            connect_timeout=1.5,
        ) as conn:
            is_connectable = True
            # 既然已经连接成功，我们现在可以检查磁盘信息
            await test_server_disk_c_storage(last_checked, server, db_pool)
    except (OSError, asyncssh.Error) as e:
        print(f'Connection failed to {server["host"]}: {str(e)}')
        is_connectable = False

    server_id = server["server_id"]

    # 更新数据库中的连接性信息
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


def parse_disk_info(disk_output):
    # 使用预编译的正则表达式匹配数字
    match = disk_info_pattern.search(disk_output.strip())
    if match:
        # 提取剩余空间和总大小
        remaining_capacity_bytes = int(match.group(1))
        total_capacity_bytes = int(match.group(2))
        # 转换为GB
        total_capacity_gb = round(total_capacity_bytes / (1024**3), 2)
        remaining_capacity_gb = round(remaining_capacity_bytes / (1024**3), 2)
        return total_capacity_gb, remaining_capacity_gb
    else:
        return None, None


async def main():
    # 数据库连接池
    db_pool = await aiomysql.create_pool(**db_config)

    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 获取服务器列表
            await cursor.execute("SELECT server_id, host FROM servers")
            servers = await cursor.fetchall()

    last_checked = datetime.now()
    # 测试所有服务器的连接性并检查磁盘
    tasks = [
        test_server_connectivity_and_disk(last_checked, server, db_pool)
        for server in servers
    ]
    await asyncio.gather(*tasks)

    db_pool.close()
    await db_pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
