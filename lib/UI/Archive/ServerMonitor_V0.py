from datetime import datetime

import pandas as pd
import pymysql
import streamlit as st
from plotly import graph_objs as go
from streamlit_autorefresh import st_autorefresh

from lib.db_config import DefaultConfig

# 设置页面居中
st.set_page_config(layout="wide")


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
    with connection.cursor() as cursor:
        query = "SELECT MAX(last_checked) AS last_checked FROM server_connectivity"
        cursor.execute(query)
        result = cursor.fetchone()
    # 关闭连接
    return result["last_checked"] if result["last_checked"] else None


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


# def query_server_usage(connection, latest_timestamp):
#     with connection.cursor(pymysql.cursors.DictCursor) as cursor:
#         query = """
#         SELECT
#             c.server_id,
#             c.cpu_usage,
#             m.memory_usage,
#             d.total_capacity_gb,
#             d.remaining_capacity_gb
#         FROM cpu_usages AS c
#         INNER JOIN memory_usages AS m ON c.server_id = m.server_id AND c.timestamp = m.timestamp
#         INNER JOIN (
#             SELECT server_id, total_capacity_gb, remaining_capacity_gb
#             FROM server_disk_C_storage
#             WHERE last_checked = (
#                 SELECT MAX(last_checked)
#                 FROM server_disk_C_storage AS sdcs
#                 WHERE sdcs.server_id = server_disk_C_storage.server_id
#             )
#         ) AS d ON c.server_id = d.server_id
#         WHERE c.timestamp = %s
#         """
#         cursor.execute(query, (latest_timestamp,))
#         return cursor.fetchall()


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

            # 使用 Streamlit 的 dataframe 函数显示表格，并设置高度
            with st.expander("Server Connectivity Data", expanded=True):
                st.dataframe(
                    df.style.map(
                        lambda v: "color: green;" if v == "🟢" else "color: red;",
                        subset=["status"],
                    )
                )
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
        width=300,
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
        # df_usage['server_id'] = df_usage['server_id'].astype(int)  # 确保 ID 是整数
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

    # 生成服务器ID和灯号的HTML
    # 生成服务器ID和灯号的HTML，并添加灰色圆角边框以及加粗服务器名
    # 使用边框和圆角包含服务器信息的HTML
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
    with st.expander(f" {server_id} more info", expanded=False):

        try:
            recent_data = query_recent_server_data(connection, server_id)

            # 展示活跃用户列表
            if active_users:
                df_active_users = pd.DataFrame(active_users)
                df_active_users = df_active_users.drop(columns=["timestamp"])
                st.table(df_active_users)
            else:
                st.info(f"No active users at server  {server_id}")

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


# 主函數
def main():
    # 设置自动刷新，每隔10000毫秒（即10秒）刷新一次页面
    st_autorefresh(interval=20000, key="data_refresh")
    # 側邊欄導航
    st.title("Server Monitor System")
    # 使用标签页进行导航
    tab1, tab2 = st.tabs(["Server Usage", "Server Status"])
    # 获取最新的时间戳
    connection = get_database_connection()
    with tab1:
        latest_timestamp = get_latest_timestamp(connection)
        usage_data = query_server_usage(connection, latest_timestamp)
        display_server_usage_data(usage_data, latest_timestamp)
        display_server_usage(connection, usage_data, latest_timestamp)

    with tab2:
        latest_check_time = query_latest_check_time(connection)
        display_latest_server_connectivity(connection, latest_check_time)

    connection.close()


if __name__ == "__main__":
    main()
