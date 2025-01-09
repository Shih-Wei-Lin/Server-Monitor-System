import os
import time
import signal
# import re

from datetime import datetime
from db_config import DefaultConfig

def periodical_execution(object, min=5, sec=0, count=10):
    # The section will execute every 'min' minute 'sec' second
    # Input:
    #   object (str): A .py file (path\name) applied to execute periodically
    #   min (int): How many minutes per period
    #   sec (float): How many seconds per period, can be a float number
    # The whold period would be 60 * min + sec
    #   count (int): How many times before asking for next execution 
    
    # Check input format:
    compiler = 'python'
    if os.path.isfile(object):
        file = compiler + ' ' + object
    else:
        print('找不到檔案\n')
        return
    
    if isinstance(min, int):
        if min < 0:
            print('min should be a non-negative integer\n')
            return
    else:
        print('min should be an integer.\n')
        return

    if isinstance(sec, (float, int)):
        if sec < 0:
            print('sec should be non-negative\n')
            return
    else:
        print('sec should be an digital number.\n')
        return
        
    if isinstance(count, int):
        if count <= 0:
            print('count should be a positive integer\n')
            return
    else:
        print('count should be a positive integer.\n')
        return

    nap = min * 60 + sec
    
    status = True
    while status:
        print('Extract %d times every %d min %.2f sec per round.\n' % (count, min, sec))
        if  count > 1:
            for line in range(count-1):
                print('Epoch: ', line)
                t_ = executioner(file)
                time.sleep(nap-t_)
        print('Epoch: ', line+1)
        executioner(file)

        a = input('do you want to execute again?(Y/n)') or 'y'
        
        if a in 'Nn':
            status = False
    pass

def continuous_execution(object_check, object_extract, min_check=60, sec_check=0, min_extract=5, sec_extract=0):
    # The section will execute every 'min' minute 'sec' second
    # Input:
    #   object_* (str): .py files (path\name) of check connectivity and extract resources
    #   min_* (int): Minutes per period. Non-negative integer
    #   sec_* (float): Seconds per period. Non-negative float number
    #   The whole period of each function would be 60 * min_* + sec_*
    
    # Check input format:
    compiler = 'python'
    if os.path.isfile(object_check):
        file_check = compiler + ' ' + object_check
    else:
        print('找不到確認連結用的檔案\n')
        return
    
    if os.path.isfile(object_extract):
        file_extract = compiler + ' ' + object_extract
    else:
        print('找不到抓取數據用的檔案\n')
        return
    
    if isinstance(min_check, int):
        if min_check < 0:
            print('min須為非負整數\n')
            return
    else:
        print('min須為非負整數\n')
        return

    if isinstance(sec_check, (float, int)):
        if sec_check < 0:
            print('sec須為非負整數\n')
            return
    else:
        print('sec須為非負整數\n')
        return

    if isinstance(min_extract, int):
        if min_extract < 0:
            print('min須為非負整數\n')
            return
    else:
        print('min須為非負整數\n')
        return

    if isinstance(sec_extract, (float, int)):
        if sec_extract < 0:
            print('sec須為非負整數\n')
            return
    else:
        print('sec須為非負整數\n')
        return

    if (min_check + sec_check == 0) and (min_extract + sec_extract == 0):
        print('運行時間不可為0\n')
        return
    
    # Terminate the execution
    signal.signal(signal.SIGINT, terminate_execution)
    
    # Main function
    nap_check = min_check * 60 + sec_check
    nap_extract = min_extract * 60 + sec_extract
    print('每 %d min %.2f sec 確認連線\n' % (min_check, sec_check))
    print('每 %d min %.2f sec 抓取數據\n' % (min_extract, sec_extract))
    
    nap_check_ = nap_check
    executioner(file_check, evaluate_time=False)
    while True:
        if nap_check_ <= 0:
            executioner(file_check, evaluate_time=False)
            nap_check_ = nap_check
        
        t_extract = executioner(file_extract)
        t_sleep = nap_extract - t_extract
        if t_sleep >= 0:
            time.sleep(t_sleep)
        
        nap_check_ -= nap_extract
        min_c = nap_check_ // 60
        sec_c = nap_check_ % 60
        print('%d 分 %.2f 秒後再次確認連線' % (min_c, sec_c))
    
    pass


def executioner(object, evaluate_time=True):
    start = time.time()
    os.system(object)
    end = time.time()
    exection_time = end - start
    print('Execution time: %.2f sec\n' % exection_time)
    
    if evaluate_time:
        return exection_time 
    
    pass

def terminate_execution(signal):
    print('中斷結束運行')
    pass