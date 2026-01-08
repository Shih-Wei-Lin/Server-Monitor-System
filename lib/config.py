class DefaultConfig:
    """
    Central configuration values for the project.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """

    DEFAULT_USERNAME = ""
    DEFAULT_PASSWORD = ""
    SECONDARY_USERNAME = ""
    SECONDARY_PASSWORD = ""

    HOST = "localhost"
    PORT = 3306
    USER = "root"
    PASSWORD = ""
    DB = "server_resources"
    CHARSET = "utf8mb4"
    AUTO_COMMIT = True

    HOST_S = "localhost"
    PORT_S = 3306
    USER_S = "root"
    PASSWORD_S = ""
    DB_S = "server_resources"
    CHARSET_S = "utf8mb4"
    AUTO_COMMIT_S = True

    FILE_PATH = ""
    FILE_EXTRACT = "update_status.py"
    FILE_CHECK_CONNECT = "check_connect.py"
    FILE_COMPRESS = "compress_data.py"

    LIBRARY_IP = ""
    GIT_IP = ""
    FILE_STATION_PAGE = ""
    BULLETIN_BOARD = ""
    ASUS_AUTOMATION = ""
    PI_AUTOMATION = ""
    OPEN_WEBUI = ""

    PAGE_TITLE = "Monitor"
    PAGE_ICON = ":desktop_computer:"
    REFRESH_INTERVAL_MS = 20000
    USER_OFFLINE_THRESHOLD_S = 10

    BOOKING_DURATION_SECONDS = 8 * 60 * 60
    LOCK_TIMEOUT_S = 5

    HELP_URL = ""
    BUG_REPORT_URL = ""
