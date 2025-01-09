# Config file for account info

class DefaultConfig(object):
    # 加入default 登入帳號及被用帳號
    DEFAULT_USERNAME = ""
    DEFAULT_PASSWORD = ""
    SECONDARY_USERNAME = ""
    SECONDARY_PASSWORD = ""

    #for check info
    HOST = 'localhost'
    PORT = 3306
    USER = 'root'
    PASSWORD = ''
    DB = 'server_resources'
    CHARSET = 'utf8mb4'
    AUTO_COMMIT = True
    
    #for website
    HOST_S = 'localhost'
    PORT_S = 3306
    USER_S = 'cilent'
    PASSWORD_S = ''
    DB_S = 'server_resources'
    CHARSET_S = 'utf8mb4'
    AUTO_COMMIT_S= True
    
    # 執行檔案路徑
    FILE_PATH = "c:/Users/monitor/Desktop/Monitor/Python/package/"
    FILE_EXTRACT = "Update_status_V0.2.py"
    FILE_CHECK_CONNECT = "Check_conective.py"
    
    LIBRARY_IP = "http://192.168.1.80"
    GIT_IP = ""#Can seeting your own website
    FILE_STATION_PAGE =""
    BULLETIN_BOARD=""
