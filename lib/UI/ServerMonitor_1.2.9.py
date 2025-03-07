import os
import sys
from datetime import timedelta

import pandas as pd
import pymysql
import streamlit as st
from plotly import graph_objs as go
from streamlit_autorefresh import st_autorefresh

# Get the directory where the current script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# print(f"Current Directory: {current_dir}")

# Get the path of the parent directory, which should be the "ServerMonitor" directory
parent_dir = os.path.dirname(current_dir)
# print(f"Parent Directory: {parent_dir}")
root_dir = os.path.dirname(parent_dir)
# print(f"Root Directory: {root_dir}")
sys.path.append(root_dir)
from lib.db_config import DefaultConfig
from lib.UI.tool.db_utils import (get_active_users_and_names,
                                  get_database_connection, get_disk_c_usage,
                                  get_latest_average_timestamp,
                                  get_latest_timestamp, get_server_ids,
                                  get_server_metrics_averages,
                                  query_latest_check_time,
                                  query_latest_server_connectivity,
                                  query_recent_server_data, query_server_usage)
from lib.UI.tool.utils import (create_chart, create_open_new_page_button,
                               create_progress_bar, create_progress_bar_disk,
                               get_status_color, inject_custom_css)
from lib.UI.tool.version_updates import display_version_updates, updates_data

library_ip = DefaultConfig.LIBRARY_IP
git_ip = DefaultConfig.GIT_IP
filestation_ip = DefaultConfig.FILE_STATION_PAGE
bulletin_ip = DefaultConfig.BULLETIN_BOARD
via_wizard_ip = DefaultConfig.VIA_WIZARD
# need version_updates.py utils.py db_utils.py

# 设置页面居中
st.set_page_config(
    page_title="ASUS SI/PI",
    page_icon=":desktop_computer:",
    layout="wide",
    initial_sidebar_state="expanded",
)


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

        else:
            st.write("沒有可用的伺服器連接數據。")
    except pymysql.MySQLError as e:
        st.error(f"查詢數據庫時出錯：{e}")


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


def get_disk_c_usage_percentage(connection, server_id):
    disk_c_data = get_disk_c_usage(connection, server_id)
    if disk_c_data:
        total_capacity_gb = disk_c_data["total_capacity_gb"]
        remaining_capacity_gb = disk_c_data["remaining_capacity_gb"]
        used_capacity_gb = total_capacity_gb - remaining_capacity_gb
        return (
            round((used_capacity_gb / total_capacity_gb) * 100, 2),
            total_capacity_gb,
            used_capacity_gb,
        )
    return 0, 0, 0


def merge_user_data(active_users, active_usernames):
    df_active_users = (
        pd.DataFrame(active_users)
        if active_users
        else pd.DataFrame(columns=["username", "timestamp"])
    )
    df_active_usernames = (
        pd.DataFrame(active_usernames)
        if active_usernames
        else pd.DataFrame(columns=["user_name", "timestamp"])
    )
    df_merged = pd.concat([df_active_users, df_active_usernames], axis=1)
    df_merged = df_merged.rename(columns={"username": "Account", "user_name": "User"})
    df_merged = df_merged.drop(columns=["timestamp"])
    df_merged["User"] = df_merged["User"].fillna("Duplicate users")
    return df_merged


def show_expanded_info(connection, server_id, active_users, active_usernames):
    try:
        recent_data = query_recent_server_data(connection, server_id)
        if recent_data:
            df_recent = pd.DataFrame(recent_data)
            df_recent["timestamp"] = pd.to_datetime(df_recent["timestamp"])
            create_chart(df_recent)
        else:
            st.error(f"No usage data available for server ID {server_id}")

        df_merged = merge_user_data(active_users, active_usernames)
        if not df_merged.empty:
            st.table(df_merged)
        else:
            st.info(f"No active accounts or users at server {server_id}")
    except pymysql.MySQLError as e:
        st.error(f"Error querying the database: {e}")


def generate_lights_html(num_active_users, max_lights=4):
    light_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
    lights = []
    for i in range(max_lights):
        light_color = (
            light_colors[min(num_active_users, max_lights) - 1]
            if i < num_active_users
            else "#6c757d"
        )
        lights.append(
            f"<div style='width: 0.6em; height: 0.6em; border-radius: 50%; margin-right: 0.3em; background-color: {light_color}; transform: translateY(-0.5em);'></div>"
        )
    return "".join(lights)


def show_server_data(connection, row, latest_timestamp):
    server_id = int(row["Server ID"])
    active_users, active_usernames = get_active_users_and_names(
        connection, server_id, latest_timestamp
    )
    num_active_users = len(active_users) if active_users else 0

    # 获取磁盘 C 的使用率
    disk_c_usage_percentage, total_capacity_gb, used_capacity_gb = (
        get_disk_c_usage_percentage(connection, server_id)
    )

    # 生成指示灯的HTML
    lights_html = generate_lights_html(num_active_users)

    st.markdown(
        f"<div style='display: flex; justify-content: flex-start; align-items: center;'>"
        f"<div style='display: flex; align-items: center; margin-right: 0.6em;'>"
        f"{lights_html}"
        f"</div>"
        f"<div style='display: flex; align-items: center;'>"
        f"<h5 style='font-weight: bold; margin: 0;'>{server_id}</h5>"
        f"</div>"
        f"</div>"
        f"<div style='display: flex; align-items: center; margin-top: 0.3em;'>"
        "<span style='margin-right: 1.5em;'>CPU</span>"
        f"{create_progress_bar(row['CPU Usage (%)'])}</div>"
        f"<div style='display: flex; align-items: center; margin-top: 0.3em;'>"
        "<span style='margin-right: 1.25em;'>MEM</span>"
        f"{create_progress_bar(row['Memory Usage (%)'])}</div>",
        unsafe_allow_html=True,
    )

    disk_progress = create_progress_bar_disk(
        disk_c_usage_percentage, "Disk C", used_capacity_gb, total_capacity_gb
    )
    st.markdown(f"{disk_progress}", unsafe_allow_html=True)
    st.markdown(
        "<div style='margin-top: 0.6em;'></div>", unsafe_allow_html=True
    )  # 添加0.6em的上边距
    st.markdown(
        """
        <style>
        div.row-widget.stRadio > div{flex-direction:row;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f" {server_id} more info", expanded=False):
        show_expanded_info(connection, server_id, active_users, active_usernames)


def show_statistics(connection, server_ids, latest_average_time):
    default_end_date = latest_average_time
    default_start_date = latest_average_time - timedelta(days=7)  # 往前推7天

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("Start", default_start_date)
    with col_date2:
        end_date = st.date_input("End(latest statistical time)", default_end_date)

    if start_date and end_date:
        all_times = pd.date_range(start=start_date, end=end_date, freq="10min")
        df_all_times = pd.DataFrame(all_times, columns=["Time"])

        cpu_traces, mem_traces = [], []

        # 遍歷所有 server_ids 並生成 traces
        for server_id in server_ids:
            data = get_server_metrics_averages(
                connection, server_id, start_date, end_date
            )
            if data:
                df = pd.DataFrame(data)
                df.rename(columns={"average_timestamp": "Time"}, inplace=True)
                df_merged = pd.merge(df_all_times, df, on="Time", how="outer")

                cpu_trace = go.Scatter(
                    x=df_merged["Time"],
                    y=df_merged["average_cpu_usage"],
                    mode="lines",
                    name=f"{server_id}",
                    connectgaps=False,
                    visible="legendonly",
                )
                mem_trace = go.Scatter(
                    x=df_merged["Time"],
                    y=df_merged["average_memory_usage"],
                    mode="lines",
                    name=f"{server_id}",
                    connectgaps=False,
                    visible="legendonly",
                )

                cpu_traces.append(cpu_trace)
                mem_traces.append(mem_trace)

        # 設置圖表的佈局
        layout = lambda title, yaxis_title: go.Layout(
            title=dict(
                text=title,
                y=1,
                x=0.5,
                xanchor="center",
                yanchor="top",
                font=dict(size=20),
            ),
            xaxis=dict(title="Time", range=[start_date, end_date]),
            yaxis=dict(title=yaxis_title, range=[0, 100]),
            height=600,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                x=0,
                y=1.18,
                bgcolor="rgba(200,200,200,0.5)",
                font=dict(size=15, family="Arial, sans-serif"),
            ),
        )

        # 創建和顯示圖表
        fig_CPU = go.Figure(
            data=cpu_traces, layout=layout("Servers CPU Usage", "CPU(%)")
        )
        fig_MEM = go.Figure(
            data=mem_traces, layout=layout("Servers Memory Usage", "Memory (%)")
        )

        col_plot1, col_plot2 = st.columns(2)
        with col_plot1:
            st.plotly_chart(fig_CPU, use_container_width=True)
        with col_plot2:
            st.plotly_chart(fig_MEM, use_container_width=True)
    else:
        st.write("Please select a date range and at least one metric to display.")


def get_version():
    # 直接获取列表第一个元素的版本号
    latest_version = updates_data[0]["version"]
    return latest_version


def navigate_to(page_name):
    st.session_state.current_page = page_name


def show_server_monitor_system():
    version = get_version()
    st.markdown(
        f"<h1 class='main-title'>Server Monitor System <span class='version'>v.{version}</span></h1>",
        unsafe_allow_html=True,
    )
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


def calculate_wavelength_frequency(
    frequency, frequency_unit, wavelength, wavelength_unit
):
    c = 299792458  # 光速 (m/s)
    unit_conversion = {"nm": 1e-9, "μm": 1e-6, "mm": 1e-3, "cm": 1e-2, "m": 1}
    unit_factors = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}

    # 將輸入的頻率和波長轉換為基礎單位
    calculated_wavelength = None
    calculated_frequency = None

    if frequency is not None:
        frequency_hz = frequency * unit_factors[frequency_unit]
        calculated_wavelength_m = c / frequency_hz
        calculated_wavelength = (
            calculated_wavelength_m / unit_conversion[wavelength_unit]
        )

    if wavelength is not None:
        wavelength_m = wavelength * unit_conversion[wavelength_unit]
        calculated_frequency_hz = c / wavelength_m
        calculated_frequency = calculated_frequency_hz / unit_factors[frequency_unit]

    return calculated_wavelength, calculated_frequency


def show_calculator():
    if "switch" not in st.session_state:
        st.session_state.switch = False

    def switch_input():
        st.session_state.switch = not st.session_state.switch

    st.title("波長頻率換算器")
    st.button("顛倒轉換", on_click=switch_input)

    col1, col2 = st.columns(2)
    with col1:
        use_scientific_notation = st.checkbox("使用科學記號", value=False)

        col3, col4 = st.columns(2)
        with col3:
            # 單位選擇框
            frequency_unit = st.selectbox(
                "選擇頻率單位",
                ["Hz", "kHz", "MHz", "GHz", "THz"],
                index=3,
                key="frequency_unit_display",
            )

            if st.session_state.switch:
                frequency = st.number_input(
                    "頻率 (f)", min_value=0.0, value=1.0, step=0.1, key="frequency"
                )
                wavelength = None
            else:
                wavelength = st.number_input(
                    "波長 (λ)", min_value=0.0, value=300.0, step=0.1, key="wavelength"
                )
                frequency = None

        with col4:
            # 計算波長和頻率
            wavelength_unit = st.selectbox(
                "選擇波長單位",
                ["nm", "μm", "mm", "cm", "m"],
                index=4,
                key="wavelength_unit_display",
            )
            calculated_wavelength, calculated_frequency = (
                calculate_wavelength_frequency(
                    frequency, frequency_unit, wavelength, wavelength_unit
                )
            )

            # 顯示結果
            if calculated_wavelength is not None:
                if use_scientific_notation:
                    st.write(f"對應的波長:")
                    st.write(f"{calculated_wavelength:.4e} {wavelength_unit}")
                else:
                    st.write(f"對應的波長: ")
                    st.write(f"{calculated_wavelength:.4f} {wavelength_unit}")

            if calculated_frequency is not None:
                if use_scientific_notation:
                    st.write(f"對應的頻率: ")
                    st.write(f"{calculated_frequency:.4e} {frequency_unit}")
                else:
                    st.write(f"對應的頻率:")
                    st.write(f"{calculated_frequency:.4f} {frequency_unit}")

    with col2:
        st.write("### 公式")
        col9, col10 = st.columns(2)
        with col9:
            st.latex(r"\lambda = \frac{c}{f}")
            st.latex(r"c = \lambda \cdot f")
            st.latex(r"f = \frac{c}{\lambda}")
        with col10:
            st.write("c = 光速 (299,792,458 m/s)")
            st.write("f = 頻率 (Hz)")
            st.write("λ = 波長 (m)")


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
    st.sidebar.markdown(
        create_open_new_page_button("公告欄 ", bulletin_ip), unsafe_allow_html=True
    )
    if st.sidebar.button("Server Monitor System", key="server_monitor_button"):
        navigate_to("Server Monitor System")
    if st.sidebar.button("Useful Caculator", key="calculator_button"):
        navigate_to("Calculator")

    if st.session_state.current_page == "Calculator":
        show_calculator()
    elif st.session_state.current_page == "Server Monitor System":
        st_autorefresh(interval=20000, key="server_monitor_autorefresh")
        show_server_monitor_system()
    # 在侧边栏中添加按钮

    # 添加一個新的按鈕，點擊後在新分頁中打開連結
    st.sidebar.markdown(
        create_open_new_page_button("ASUS KM", library_ip), unsafe_allow_html=True
    )

    st.sidebar.markdown(
        create_open_new_page_button("Git", git_ip), unsafe_allow_html=True
    )

    st.sidebar.markdown(
        create_open_new_page_button("file station", filestation_ip),
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        create_open_new_page_button("Via Wizard", via_wizard_ip), unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
