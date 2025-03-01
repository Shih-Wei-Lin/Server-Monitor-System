from db_config import DefaultConfig
import util
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

def main():
    """主程序入口點"""
    try:
        # 獲取檔案路徑
        file_path = DefaultConfig.FILE_PATH
        file_check = DefaultConfig.FILE_CHECK_CONNECT
        file_extract = DefaultConfig.FILE_EXTRACT
        
        # 構建完整路徑
        check_file = file_path + file_check
        extract_file = file_path + file_extract
        
        # 啟動連續執行
        logger.info(f"啟動連續執行程序")
        logger.info(f"檢查連線檔案: {check_file}")
        logger.info(f"提取資料檔案: {extract_file}")
        
        util.continuous_execution(
            check_file, 
            extract_file, 
            min_check=60, 
            sec_check=0, 
            min_extract=0, 
            sec_extract=5
        )
        
    except Exception as e:
        logger.exception(f"程序運行出錯: {e}")

if __name__ == "__main__":
    main()