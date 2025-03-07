from datetime import timedelta

import pandas as pd
import pymysql
import streamlit as st
from plotly import graph_objs as go
from streamlit_autorefresh import st_autorefresh
from version_updates import display_version_updates

from lib.db_config import DefaultConfig

# 设置页面居中
st.set_page_config(
    page_title="ASUS SI/PI",
    page_icon=":desktop_computer:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_custom_css():
    custom_css = """
        <style>
            .stButton>button {
                width: 100%;
                border: none;
                border-radius: 0;
                margin: 0;
                padding: 10px 0; /* 添加内边距 */
                text-align: left; /* 文字靠左 */
                background-color: transparent; /* 移除背景色 */
                box-shadow: none; /* 移除阴影 */
            }
            .stButton>button:hover {
                background-color: rgba(0, 0, 0, 0.1); /* 鼠标悬停时的背景色，可根据需要调整 */
            }
            /* 添加创建者信息的样式 */
            .credit {
                position: fixed;
                bottom: 10px;
                right: 10px;
                color: grey;
                font-size: 0.8em;
                z-index:9999;
            }
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


# 添加第一组和第二组预设的用户凭证
DEFAULT_USERNAME = DefaultConfig.DEFAULT_USERNAME
DEFAULT_PASSWORD = DefaultConfig.DEFAULT_PASSWORD
SECONDARY_USERNAME = DefaultConfig.SECONDARY_USERNAME
SECONDARY_PASSWORD = DefaultConfig.SECONDARY_PASSWORD

db_config = {
    "host": DefaultConfig.HOST,
    "port": DefaultConfig.PORT,
    "user": DefaultConfig.USER,
    "password": DefaultConfig.PASSWORD,
    "db": DefaultConfig.DB,
    "charset": DefaultConfig.CHARSET,
    "autocommit": DefaultConfig.AUTO_COMMIT,
}


# 建立數據庫連接
def get_database_connection():
    try:
        connection = pymysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            db=db_config["db"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except pymysql.MySQLError as e:
        st.error(f"无法连接到数据库：{e}")
        st.stop()


# 在需要数据库连接的函数中使用上下文管理器
def query_latest_check_time(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
            cursor.execute(query)
            result = cursor.fetchone()
            return result["last_checked"] if result and result["last_checked"] else None
    except Exception as e:
        print(f"Error fetching latest check time: {e}")
        return None


def get_latest_average_timestamp(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT MAX(average_timestamp) AS latest_timestamp FROM server_metrics_averages"
            cursor.execute(query)
            result = cursor.fetchone()
            return (
                result["latest_timestamp"]
                if result and result["latest_timestamp"]
                else None
            )
    except Exception as e:
        print(f"Error fetching latest average timestamp: {e}")
        return None


# 查詢每個伺服器最新的檢查時間記錄和伺服器資訊
def query_latest_server_connectivity(connection):

    with connection.cursor() as cursor:
        query = """
        SELECT
            s.server_id,
            s.host,
            s.CPU_info,
            s.GPU_info,
            s.core_info,
            s.logical_process_info,
            s.Memory_size_info,
            s.System_OS_info,
            sc.is_connectable
        FROM servers s
        LEFT JOIN (
            SELECT
                sc1.server_id,
                sc1.is_connectable,
                sc1.last_checked
            FROM server_connectivity sc1
            INNER JOIN (
                SELECT server_id, MAX(last_checked) AS max_last_checked
                FROM server_connectivity
                GROUP BY server_id
            ) sc2
            ON sc1.server_id = sc2.server_id AND sc1.last_checked = sc2.max_last_checked
        ) sc ON s.server_id = sc.server_id
        """
        cursor.execute(query)
        return cursor.fetchall()


# 給定連接狀態，返回對應的顏色標記
def get_status_color(is_connectable):
    return "🟢" if is_connectable else "🔴"


def query_recent_server_data(connection, server_id, num_records=15):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
        SELECT * FROM (
            SELECT
                c.timestamp,
                c.cpu_usage,
                m.memory_usage
            FROM cpu_usages AS c
            INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp
            WHERE c.server_id = %s
            ORDER BY c.timestamp DESC
            LIMIT %s
        ) AS subquery
        ORDER BY timestamp ASC
        """
        cursor.execute(query, (server_id, num_records))
        return cursor.fetchall()


# 获取最新的 timestamp 从 cpu_usages 表
def get_latest_timestamp(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(timestamp) AS latest_timestamp FROM cpu_usages")
        result = cursor.fetchone()
        return result["latest_timestamp"] if result["latest_timestamp"] else None


def query_server_usage(connection, latest_timestamp):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
        SELECT
            c.server_id,
            c.cpu_usage,
            m.memory_usage
        FROM cpu_usages AS c
        INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp 
        WHERE c.timestamp = %s
        """
        cursor.execute(query, (latest_timestamp,))
        return cursor.fetchall()


def get_disk_c_usage(connection, server_id):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT total_capacity_gb, remaining_capacity_gb
            FROM server_disk_C_storage
            WHERE server_id = %s
            ORDER BY last_checked DESC
            LIMIT 1;
            """
        cursor.execute(query, (server_id,))
        result = cursor.fetchone()
        return result


def get_active_users(connection, server_id, latest_timestamp):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
                    SELECT username, timestamp
                    FROM active_users
                    WHERE server_id = %s AND timestamp = (
                        SELECT MAX(timestamp)
                        FROM active_users
                        WHERE server_id = %s AND timestamp <= %s
                    )
                    """
        cursor.execute(query, (server_id, server_id, latest_timestamp))
        return cursor.fetchall()


def get_active_user_names(connection, server_id, latest_timestamp):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
                SELECT u.user_name, a.timestamp
                FROM active_ip AS a
                INNER JOIN user_ip_map AS u ON a.ip_address = u.ip_address
                WHERE a.server_id = %s AND a.timestamp = (
                    SELECT MAX(timestamp)
                    FROM active_ip
                    WHERE server_id = %s AND timestamp <= %s
                )
                """
        cursor.execute(query, (server_id, server_id, latest_timestamp))
        return cursor.fetchall()


def get_server_ids(connection):
    try:
        with connection.cursor() as cursor:
            query = "SELECT server_id FROM servers;"
            cursor.execute(query)
            server_ids = cursor.fetchall()
            return [server["server_id"] for server in server_ids]
    except Exception as e:
        st.error(f"Error fetching server IDs: {e}")
        return []


# 查询数据库中的平均使用率数据
def get_server_metrics_averages(connection, server_id, start_date, end_date):
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT *
            FROM server_metrics_averages
            WHERE server_id = %s AND average_timestamp BETWEEN %s AND %s;
            """
            cursor.execute(query, (server_id, start_date, end_date))
            result = cursor.fetchall()
            return result
    except Exception as e:
        st.error(f"Error fetching server metrics averages: {e}")
        return []


# 顯示伺服器最新的連接狀態
def display_latest_server_connectivity(connection, latest_check_time):

    formatted_time = (
        latest_check_time.strftime("%Y-%m-%d %H:%M:%S") if latest_check_time else "未知"
    )
    st.markdown(f"###### Last connect checked: {formatted_time}")
    try:
        connectivity_data = query_latest_server_connectivity(connection)
        if connectivity_data:
            df = pd.DataFrame(connectivity_data)
            df["status"] = df["is_connectable"].apply(get_status_color)
            df.rename(columns=lambda x: x.replace("_info", ""), inplace=True)
            df = df[
                [
                    "status",
                    "server_id",
                    "host",
                    "CPU",
                    "GPU",
                    "core",
                    "logical_process",
                    "Memory_size",
                    "System_OS",
                ]
            ]
            df.rename(
                columns={
                    "server_id": "Server ID",
                    "host": "IP",
                    "core": "#Core",
                    "logical_process": "#Logical Process",
                    "Memory_size": "Memory Size",
                    "OS": "OS",
                },
                inplace=True,
            )

            st.dataframe(
                df.style.map(
                    lambda v: "color: green;" if v == "🟢" else "color: red;",
                    subset=["status"],
                )
            )
            # 使用 Streamlit 的 dataframe 函数显示表格，并设置高度

        else:
            st.write("沒有可用的伺服器連接數據。")
    except pymysql.MySQLError as e:
        st.error(f"查詢數據庫時出錯：{e}")


def create_progress_bar_disk(usage_percentage, label, used_gb, total_gb):
    # 根据百分比选择颜色
    if usage_percentage < 21:
        color = "#4caf50"  # 绿色
    elif usage_percentage < 41:
        color = "#2196f3"  # 蓝色
    elif usage_percentage < 61:
        color = "#ffeb3b"  # 黄色
    elif usage_percentage < 81:
        color = "#ff9800"  # 橘色
    else:
        color = "#f44336"  # 红色

    # 使用自定义样式的HTML来创建长方形进度条，文字加粗，并显示已用容量和总容量
    progress_bar_html = f"""
    <div style='display: flex; align-items: center; margin-top: 5px;'>
        <span style='margin-right: 11px;white-space: nowrap;'>{label}</span>
        <div style="background-color: #d0d3d8; border-radius: 0; position: relative; height: 20px; width: 100%;">
            <div style="background-color: {color}; width: {usage_percentage}%; height: 100%; border-radius: 0;"></div>
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold;">
                 {used_gb:.2f} / {total_gb:.2f}GB
            </div>
        </div>
    </div>
    """
    return progress_bar_html


def create_progress_bar(percentage):
    # 根据百分比选择颜色
    if percentage < 21:
        color = "#4caf50"  # 绿色
    elif percentage < 41:
        color = "#2196f3"  # 蓝色
    elif percentage < 61:
        color = "#ffeb3b"  # 黄色
    elif percentage < 81:
        color = "#ff9800"  # 橘色
    else:
        color = "#f44336"  # 红色

    # 使用自定义样式的HTML来创建长方形进度条，文字加粗
    progress_bar_style = f"""
    <div style="background-color: #d0d3d8; border-radius: 0; position: relative; height: 20px; width: 100%;">
        <div style="background-color: {color}; width: {percentage}%; height: 100%; border-radius: 0;"></div>
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold;">{percentage}%</div>
    </div>
    """
    return progress_bar_style


def create_chart(df_recent):
    cpu_trace = go.Scatter(
        x=df_recent["timestamp"],
        y=df_recent["cpu_usage"],
        name="CPU Usage",
        mode="lines",
        line=dict(color="blue"),
        hoverinfo="text+y",  # 显示自定义文本和y值
        hovertemplate="CPU: %{y:.2f}%<extra></extra>",  # 定义悬停文本格式，不显示额外的悬停信息
    )
    mem_trace = go.Scatter(
        x=df_recent["timestamp"],
        y=df_recent["memory_usage"],
        name="Memory Usage",
        mode="lines",
        line=dict(color="green"),
        hoverinfo="text+y",  # 显示自定义文本和y值
        hovertemplate="MEM: %{y:.2f}%<extra></extra>",  # 定义悬停文本格式，不显示额外的悬停信息
    )
    layout = go.Layout(
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=True, range=[0, 100]),
        height=200,
        # width=300,
        hovermode="x unified",  # 同一x位置的点共享悬停框，并显示在图表的上方
        showlegend=False,
        margin=dict(
            t=10, b=10, l=10, r=10
        ),  # 设置图表的上下左右边距，t为上边距，b为下边距，l为左边距，r为右边距
    )
    fig = go.Figure(data=[cpu_trace, mem_trace], layout=layout)
    st.plotly_chart(fig, use_container_width=False)


# 展示伺服器使用情况
def display_server_usage_data(usage_data, latest_timestamp):
    try:

        if latest_timestamp:
            # 格式化时间戳以便于阅读
            formatted_timestamp = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            # 在页面上显示时间戳
            st.markdown(f"###### Last usage checked: {formatted_timestamp}")
            # 使用最新的时间戳查询数据
            # 转换为 DataFrame
            df_usage = pd.DataFrame(usage_data)
            df_usage.rename(
                columns={
                    "server_id": "Server ID",
                    "cpu_usage": "CPU Usage (%)",
                    "memory_usage": "Memory Usage (%)",
                },
                inplace=True,
            )
            with st.expander("Server Usage Data", expanded=False):
                st.dataframe(df_usage)

        else:
            st.error("No data available.")
    except pymysql.MySQLError as e:
        st.error(f"Error querying the database: {e}")


def display_server_usage(connection, usage_data, latest_timestamp):
    try:
        df_usage = pd.DataFrame(usage_data)
        df_usage["server_id"] = df_usage["server_id"].astype(int)  # 确保 ID 是整数
        df_usage.rename(
            columns={
                "server_id": "Server ID",
                "cpu_usage": "CPU Usage (%)",
                "memory_usage": "Memory Usage (%)",
            },
            inplace=True,
        )
        cols_per_row = 5
        rows = (len(df_usage) + cols_per_row - 1) // cols_per_row
        for i in range(rows):
            cols = st.columns(cols_per_row)
            for j, index in enumerate(range(i * cols_per_row, (i + 1) * cols_per_row)):
                if index < len(df_usage):
                    with cols[j]:
                        show_server_data(
                            connection, df_usage.iloc[index], latest_timestamp
                        )
                else:
                    with cols[j]:
                        st.empty()
            # 在每行结束后添加一条细线
            if i < rows - 1:  # 避免在最后一行后添加线条
                st.markdown(
                    "<hr style='margin-top: 1rem; margin-bottom: 1rem; border-top: 1px solid #ccc;'/>",
                    unsafe_allow_html=True,
                )
    except pymysql.MySQLError as e:
        st.error(f"Error querying the database: {e}")


def show_server_data(connection, row, latest_timestamp):
    server_id = int(row["Server ID"])
    active_users = get_active_users(connection, server_id, latest_timestamp)
    active_usernames = get_active_user_names(connection, server_id, latest_timestamp)
    num_active_users = len(active_users) if active_users else 0
    # 获取磁盘 C 的使用率
    disk_c_data = get_disk_c_usage(connection, server_id)
    if disk_c_data:
        total_capacity_gb = disk_c_data["total_capacity_gb"]
        remaining_capacity_gb = disk_c_data["remaining_capacity_gb"]
        used_capacity_gb = total_capacity_gb - remaining_capacity_gb
        disk_c_usage_percentage = round((used_capacity_gb / total_capacity_gb) * 100, 2)
    else:
        disk_c_usage_percentage = 0
    # 生成灯号的HTML
    lights = []
    for i in range(4):
        if i < num_active_users:
            if num_active_users == 1:
                light_color = "#28a745"  # 一个用户，灯变为绿色
            elif num_active_users == 2:
                light_color = "#ffc107"  # 两个用户，灯变为黄色
            elif num_active_users == 3:
                light_color = "#fd7e14"  # 三个用户，灯变为橘色
            else:
                light_color = "#dc3545"  # 四个或更多用户，灯变为红色
        else:
            light_color = "#6c757d"  # 没有用户对应的灯保持灰色

        lights.append(
            f"<div style='width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; background-color: {light_color};'></div>"
        )

    st.markdown(
        # 创建一个容器，其中包含指示灯和服务器 ID，确保它们垂直居中对齐
        f"<div style='display: flex; justify-content: flex-start; align-items: center;'>"
        # 指示灯部分
        f"<div style='display: flex; flex-direction: row; min-height: 22px; margin-right: 10px;'>"
        + "".join(lights)
        + f"</div>"
        # 服务器 ID 部分
        f"<div style='display: flex; align-items: center;'>"
        f"<h5 style='font-weight: bold; margin: 0; padding-left: 10px;'>{server_id}</h5>"
        f"</div>"
        f"</div>"
        # 显示 CPU 使用率进度条
        f"<div style='display: flex; align-items: center; margin-top: 5px;'>"
        "<span style='margin-right: 24px;'>CPU</span>"
        f"{create_progress_bar(row['CPU Usage (%)'])}</div>"
        # 显示内存使用率进度条
        f"<div style='display: flex; align-items: center; margin-top: 5px;'>"
        "<span style='margin-right: 20px;'>MEM</span>"
        f"{create_progress_bar(row['Memory Usage (%)'])}</div>",
        unsafe_allow_html=True,
    )
    disk_progress = create_progress_bar_disk(
        disk_c_usage_percentage, "Disk C", used_capacity_gb, total_capacity_gb
    )
    st.markdown(f"{disk_progress}", unsafe_allow_html=True)
    st.markdown(
        "<div style='margin-top: 10px;'></div>", unsafe_allow_html=True
    )  # 添加10像素的上边距
    st.markdown(
        """
        <style>
        div.row-widget.stRadio > div{flex-direction:row;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f" {server_id} more info", expanded=False):
        try:
            recent_data = query_recent_server_data(connection, server_id)

            # 将active_users和active_usernames的数据转换为DataFrame
            if active_users:
                df_active_users = pd.DataFrame(active_users)
            else:
                df_active_users = pd.DataFrame(columns=["username", "timestamp"])

            if active_usernames:
                df_active_usernames = pd.DataFrame(active_usernames)
            else:
                df_active_usernames = pd.DataFrame(columns=["user_name", "timestamp"])

            # 合并DataFrame，这里我们使用timestamp来对齐数据
            df_merged = pd.concat([df_active_users, df_active_usernames], axis=1)

            # 重命名列，使其更明确
            df_merged = df_merged.rename(
                columns={"username": "Account", "user_name": "User"}
            )

            # 删除timestamp列，因为我们不想在表格中展示它
            df_merged = df_merged.drop(columns=["timestamp"])

            # 展示合并后的表格
            if not df_merged.empty:
                st.table(df_merged)
            else:
                st.info(f"No active accounts or users at server {server_id}")

            # 展示时间图表
            if recent_data:
                df_recent = pd.DataFrame(recent_data)
                df_recent["timestamp"] = pd.to_datetime(df_recent["timestamp"])
                create_chart(df_recent)  # 使用辅助函数创建图表
                # 结束包含服务器信息的div

            else:
                st.error(f"No usage data available for server ID {server_id}")

        except pymysql.MySQLError as e:
            st.error(f"Error querying the database: {e}")


def show_statistics(connection, server_ids, latest_average_time):
    default_end_date = latest_average_time
    default_start_date = latest_average_time - timedelta(days=7)  # 往前推7天

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("Start", default_start_date)
    with col_date2:
        end_date = st.date_input("End(latest statistical time)", default_end_date)

    if start_date and end_date is not None:
        cpu_traces = []  # 存儲所有伺服器的 CPU traces
        mem_traces = []  # 存儲所有伺服器的 CPU traces
        for server_id in server_ids:
            data = get_server_metrics_averages(
                connection, server_id, start_date, end_date
            )
            if data:
                df = pd.DataFrame(data)
                df.rename(columns={"average_timestamp": "Time"}, inplace=True)
                cpu_trace = go.Scatter(
                    x=df["Time"],
                    y=df["average_cpu_usage"],
                    mode="lines",
                    name=f"{server_id}",
                    hoverinfo="text+y",
                    hovertemplate=f"{server_id} : %{{y:.2f}}%<extra></extra>",
                    visible="legendonly",  # 設置為只在圖例中顯示
                )
                cpu_traces.append(cpu_trace)
                mem_trace = go.Scatter(
                    x=df["Time"],
                    y=df["average_memory_usage"],
                    mode="lines",
                    name=f"{server_id}",
                    hoverinfo="text+y",
                    hovertemplate=f"{server_id} : %{{y:.2f}}%<extra></extra>",
                    visible="legendonly",  # 設置為只在圖例中顯示
                )
                mem_traces.append(mem_trace)
            # 設置圖表的佈局
        layout_CPU = go.Layout(
            title="Servers Average CPU Usage",
            xaxis=dict(title="Time", range=[start_date, end_date]),
            yaxis=dict(title="CPU(%)", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", x=0, y=1.1),
        )
        layout_MEM = go.Layout(
            title="Servers Average Memory Usage",
            xaxis=dict(title="Time", range=[start_date, end_date]),
            yaxis=dict(title="Memory (%)", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", x=0, y=1.1),
        )

        # 創建 Figure 並添加所有 CPU traces
        fig_CPU = go.Figure(data=cpu_traces, layout=layout_CPU)

        fig_MEM = go.Figure(data=mem_traces, layout=layout_MEM)
        # 在 Streamlit 中顯示圖表
        col_plot1, col_plot2 = st.columns(2)
        with col_plot1:

            st.plotly_chart(fig_CPU, use_container_width=True)
        with col_plot2:

            st.plotly_chart(fig_MEM, use_container_width=True)
    else:
        st.write("Please select a date range and at least one metric to display.")


def navigate_to(page_name):
    st.session_state.current_page = page_name


# 页面显示函数
def show_home():
    st.sidebar.write("Welcome to ASUS SIPI Home Page!")  # 在侧边栏显示欢迎信息


def show_server_monitor_system():
    st.title("Server Monitor System")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Server Usage", "Server Status", "Statistics", "Version Updates"]
    )
    connection = get_database_connection()
    with tab1:
        latest_timestamp = get_latest_timestamp(connection)
        usage_data = query_server_usage(connection, latest_timestamp)
        display_server_usage_data(usage_data, latest_timestamp)
        display_server_usage(connection, usage_data, latest_timestamp)
    with tab2:
        latest_check_time = query_latest_check_time(connection)
        display_latest_server_connectivity(connection, latest_check_time)
    with tab3:
        latest_average_time = get_latest_average_timestamp(connection)
        server_ids = get_server_ids(connection)
        show_statistics(connection, server_ids, latest_average_time)

    with tab4:
        display_version_updates(st)
    connection.close()  # 假设的关闭数据库连接


# 主函数
def main():
    # 注入自定义CSS
    inject_custom_css()
    st.markdown('<div class="credit">Created by Sean Lin</div>', unsafe_allow_html=True)

    # 初始化session_state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Server Monitor System"

    # 侧边栏
    st.sidebar.title("ASUS SIPI")

    # 侧边栏全宽度无外框按钮用来导航
    if st.sidebar.button("Server Monitor System", key="server_monitor_button"):
        navigate_to("Server Monitor System")
    if st.sidebar.button("Home", key="home_button"):
        navigate_to("Home")

    # 根据session_state中的current_page展示不同的页面
    if st.session_state.current_page == "Home":
        show_home()
    elif st.session_state.current_page == "Server Monitor System":
        st_autorefresh(interval=20000, key="server_monitor_autorefresh")
        show_server_monitor_system()


if __name__ == "__main__":
    main()
