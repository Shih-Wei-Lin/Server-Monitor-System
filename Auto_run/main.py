from db_config import DefaultConfig
import util

file_path = DefaultConfig.FILE_PATH
file_check = DefaultConfig.FILE_CHECK_CONNECT
file_extract = DefaultConfig.FILE_EXTRACT

f_check = file_path + file_check
f_extract = file_path + file_extract
# util.periodical_execution(file, min=0, sec=5, count=2)
util.continuous_execution(f_check, f_extract, min_check=60, sec_check=0, min_extract=0, sec_extract=5)
