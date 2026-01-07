# Config file for account info


class DefaultConfig(object):
    # 添加第一组和第二组预设的用户凭证
    DEFAULT_USERNAME = ""
    DEFAULT_PASSWORD = ""
    SECONDARY_USERNAME = ""
    SECONDARY_PASSWORD = ""

    # for check info
    HOST = "localhost"
    PORT = 3306
    USER = "root"
    PASSWORD = ""
    DB = "server_resources"
    CHARSET = "utf8mb4"
    AUTO_COMMIT = True

    # for website
    HOST_S = "localhost"
    PORT_S = 3306
    USER_S = "root"
    PASSWORD_S = ""
    DB_S = "server_resources"
    CHARSET_S = "utf8mb4"
    AUTO_COMMIT_S = True

    # 執行檔案路徑
    FILE_PATH = ""
    FILE_EXTRACT = "Update_status_V0.2.py"
    FILE_CHECK_CONNECT = "Check_connect_V0.1.py"
    FILE_COMPRESS = "Compress_data_10min.py"

    LIBRARY_IP = ""
    GIT_IP = ""
    FILE_STATION_PAGE = ""
    BULLETIN_BOARD = ""
    ASUS_AUTOMATION = ""
    PI_AUTOMATION = ""
    OPEN_WEBUI = ""

    # UI and App Behavior Settings
    PAGE_TITLE = "Monitor"
    PAGE_ICON = ":desktop_computer:"
    REFRESH_INTERVAL_MS = 20000  # In milliseconds
    USER_OFFLINE_THRESHOLD_S = 10  # In seconds

    # Booking System Settings
    BOOKING_DURATION_SECONDS = 8 * 60 * 60  # 8 hours
    LOCK_TIMEOUT_S = 5  # In seconds for booking state file

    # External Links
    HELP_URL = ""
    BUG_REPORT_URL =""

# Config file for account info
