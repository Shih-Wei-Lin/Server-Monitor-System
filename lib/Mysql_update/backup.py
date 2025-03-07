import subprocess
from datetime import datetime

from lib.db_config import DefaultConfig

# 数据库配置


db_config = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}

db_user = user = db_config["user"]
db_password = password = db_config["password"]
db_name = db_config["db"]

backup_path = r"C:\Users\monitor\Desktop\Backup"

# 创建备份文件名，包含时间戳，用下划线分隔年月日时分秒
timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
backup_filename = f"{db_name}_{timestamp}.sql"
backup_fullpath = rf"{backup_path}\{backup_filename}"

# 构建带有完整路径的 mysqldump 命令
mysqldump_path = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
dumpcmd = (
    f'"{mysqldump_path}" -u {db_user} -p"{db_password}" {db_name} > "{backup_fullpath}"'
)

# 执行命令
try:
    print("备份数据库开始...")
    subprocess.run(dumpcmd, shell=True, check=True)
    print(f"备份数据库成功，备份文件保存在：{backup_fullpath}")
except subprocess.CalledProcessError as e:
    print("备份数据库失败：", e)
