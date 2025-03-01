import os
import time
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_run")

def periodical_execution(file_path: str, min: int = 5, sec: float = 0, count: int = 10) -> None:
    """
    定期執行指定的 Python 檔案。
    
    Args:
        file_path: 要執行的 Python 檔案路徑
        min: 每次執行間隔的分鐘數 (預設: 5)
        sec: 每次執行間隔的秒數 (預設: 0)
        count: 詢問是否繼續前執行的次數 (預設: 10)
    """
    try:
        # 檢查檔案是否存在
        file_obj = Path(file_path)
        if not file_obj.is_file():
            logger.error(f"找不到檔案: {file_path}")
            return

        # 檢查參數有效性
        if not isinstance(min, int) or min < 0:
            logger.error("min 必須是非負整數")
            return
            
        if not isinstance(sec, (int, float)) or sec < 0:
            logger.error("sec 必須是非負數")
            return
            
        if not isinstance(count, int) or count <= 0:
            logger.error("count 必須是正整數")
            return

        # 計算休眠時間
        nap_time = min * 60 + sec
        command = f"python {file_path}"
        
        # 主執行迴圈
        status = True
        while status:
            logger.info(f"將執行 {count} 次，每次間隔 {min} 分 {sec:.2f} 秒")
            
            for epoch in range(count):
                logger.info(f"Epoch: {epoch}")
                execution_time = executioner(command)
                
                # 最後一次執行後不需要休眠
                if epoch < count - 1:
                    sleep_time = max(0, nap_time - execution_time)
                    time.sleep(sleep_time)
            
            # 詢問是否繼續
            user_input = input("是否要再次執行? (Y/n): ") or "y"
            status = user_input.lower() not in ("n", "no")
    
    except Exception as e:
        logger.exception(f"執行過程中發生錯誤: {e}")

def continuous_execution(
    check_file: str, 
    extract_file: str, 
    min_check: int = 60, 
    sec_check: float = 0, 
    min_extract: int = 5, 
    sec_extract: float = 0
) -> None:
    """
    持續執行連線檢查和資料提取檔案。
    
    Args:
        check_file: 連線檢查的 Python 檔案路徑
        extract_file: 資料提取的 Python 檔案路徑
        min_check: 檢查連線的間隔分鐘數 (預設: 60)
        sec_check: 檢查連線的間隔秒數 (預設: 0)
        min_extract: 提取資料的間隔分鐘數 (預設: 5)
        sec_extract: 提取資料的間隔秒數 (預設: 0)
    """
    try:
        # 檢查檔案是否存在
        check_path = Path(check_file)
        extract_path = Path(extract_file)
        
        if not check_path.is_file():
            logger.error(f"找不到確認連結用的檔案: {check_file}")
            return
            
        if not extract_path.is_file():
            logger.error(f"找不到抓取數據用的檔案: {extract_file}")
            return
        
        # 檢查參數有效性
        for param_name, param_value in {
            "min_check": min_check, 
            "min_extract": min_extract
        }.items():
            if not isinstance(param_value, int) or param_value < 0:
                logger.error(f"{param_name} 須為非負整數")
                return
                
        for param_name, param_value in {
            "sec_check": sec_check, 
            "sec_extract": sec_extract
        }.items():
            if not isinstance(param_value, (int, float)) or param_value < 0:
                logger.error(f"{param_name} 須為非負數")
                return
        
        # 檢查至少一個執行時間不為零
        if (min_check + sec_check == 0) and (min_extract + sec_extract == 0):
            logger.error("運行時間不可為0")
            return
        
        # 設置中斷處理
        signal.signal(signal.SIGINT, terminate_execution)
        
        # 計算執行間隔
        nap_check = min_check * 60 + sec_check
        nap_extract = min_extract * 60 + sec_extract
        
        logger.info(f"每 {min_check} 分 {sec_check:.2f} 秒確認連線")
        logger.info(f"每 {min_extract} 分 {sec_extract:.2f} 秒抓取數據")
        
        check_command = f"python {check_file}"
        extract_command = f"python {extract_file}"
        
        # 初始化倒數計時器
        time_until_next_check = 0
        
        # 主迴圈
        while True:
            # 檢查是否需要執行連線檢查
            if time_until_next_check <= 0:
                logger.info("執行連線檢查")
                executioner(check_command, evaluate_time=False)
                time_until_next_check = nap_check
            
            # 執行資料提取
            logger.info("執行資料提取")
            extract_time = executioner(extract_command)
            
            # 計算下次資料提取前的等待時間
            sleep_time = max(0, nap_extract - extract_time)
            
            # 更新倒數計時器
            time_until_next_check -= nap_extract
            
            # 顯示下次連線檢查的時間
            mins = int(time_until_next_check // 60)
            secs = time_until_next_check % 60
            logger.info(f"{mins} 分 {secs:.2f} 秒後再次確認連線")
            
            # 休眠到下次資料提取
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except Exception as e:
        logger.exception(f"執行過程中發生錯誤: {e}")

def executioner(command: str, evaluate_time: bool = True) -> Optional[float]:
    """
    執行指定的命令並計算執行時間。
    
    Args:
        command: 要執行的命令
        evaluate_time: 是否計算並返回執行時間
        
    Returns:
        如果 evaluate_time 為 True，返回執行時間（秒），否則返回 None
    """
    start = time.time()
    exit_code = os.system(command)
    end = time.time()
    
    execution_time = end - start
    
    if exit_code != 0:
        logger.warning(f"命令執行失敗，退出碼: {exit_code}")
    
    logger.info(f"執行時間: {execution_time:.2f} 秒")
    
    if evaluate_time:
        return execution_time
    return None

def terminate_execution(sig_num, frame):
    """
    處理中斷信號。
    
    Args:
        sig_num: 信號號碼
        frame: 當前堆疊幀
    """
    logger.info(f"收到信號 {sig_num}，中斷結束運行")
    exit(0)