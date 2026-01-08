"""
Main Streamlit application for server monitoring and booking.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pymysql
import streamlit as st
from plotly import graph_objs as go
from streamlit_autorefresh import st_autorefresh

from lib.config import DefaultConfig
from lib.ui import booking
from lib.ui.tool import booking_utils
from lib.ui.tool.db_utils import (
    get_active_users_and_names,
    get_database_connection,
    get_disk_c_usage,
    get_latest_average_timestamp,
    get_latest_timestamp,
    get_server_ids,
    get_server_metrics_averages,
    query_latest_check_time,
    query_latest_server_connectivity,
    query_recent_server_data,
    query_server_usage,
)
from lib.ui.tool.utils import (
    create_chart,
    create_progress_bar,
    create_progress_bar_disk,
    get_status_color,
    inject_custom_css,
)

ROOT_DIR = Path(__file__).resolve().parents[2]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="server_monitor.log",
)
logger = logging.getLogger(__name__)

LIBRARY_IP = DefaultConfig.LIBRARY_IP
GIT_IP = DefaultConfig.GIT_IP
FILESTATION_IP = DefaultConfig.FILE_STATION_PAGE
BULLETIN_IP = DefaultConfig.BULLETIN_BOARD
ASUS_AUTOMATION_IP = DefaultConfig.ASUS_AUTOMATION
PI_AUTOMATION_IP = DefaultConfig.PI_AUTOMATION
OPEN_WEBUI_IP = DefaultConfig.OPEN_WEBUI


def configure_page() -> None:
    """
    Configure Streamlit page settings and inject CSS.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    st.set_page_config(
        page_title=DefaultConfig.PAGE_TITLE,
        page_icon=DefaultConfig.PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": DefaultConfig.HELP_URL,
            "Report a bug": DefaultConfig.BUG_REPORT_URL,
        },
    )
    inject_custom_css()


@st.cache_data(show_spinner=False)
def get_app_version() -> str:
    """
    Fetch the application version from an env override or git.

    Parameters:
        None
    Returns:
        str: Version string.
    Raises:
        None
    """
    env_version = os.environ.get("SERVER_MONITOR_VERSION")
    if env_version:
        return env_version
    try:
        version = (
            subprocess.check_output(["git", "describe", "--tags", "--always"], cwd=ROOT_DIR)
            .decode()
            .strip()
        )
        return version
    except Exception as exc:
        logger.warning("Unable to read git version: %s", exc)
        return "unknown"


@st.cache_data(ttl=30)
def get_cached_server_connectivity(check_time_str: str):
    """
    Cache server connectivity data for a short time window.

    Parameters:
        check_time_str (str): Cache key derived from latest check time.
    Returns:
        Optional[List[Dict[str, Any]]]: Connectivity data or None.
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        return query_latest_server_connectivity(connection)
    except Exception as exc:
        logger.error("Error fetching server connectivity: %s", exc)
        return None
    finally:
        connection.close()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_server_metrics(server_id: int, start_date, end_date):
    """
    Cached fetch of metrics for a server and time range.

    Parameters:
        server_id (int): Server identifier.
        start_date: Start date time.
        end_date: End date time.
    Returns:
        List[Dict[str, Any]]: Metrics records.
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        return get_server_metrics_averages(connection, server_id, start_date, end_date)
    finally:
        connection.close()


def display_latest_server_connectivity(latest_check_time) -> None:
    """
    Display connectivity status for all servers.

    Parameters:
        latest_check_time: Latest connectivity timestamp.
    Returns:
        None
    Raises:
        None
    """
    formatted_time = latest_check_time.strftime("%Y-%m-%d %H:%M:%S") if latest_check_time else "Unknown"
    st.markdown(f"###### Last connectivity check: {formatted_time}")

    check_time_str = str(latest_check_time) if latest_check_time else "none"
    connectivity_data = get_cached_server_connectivity(check_time_str)

    if not connectivity_data:
        st.info("No server connection data available.")
        return

    try:
        df = pd.DataFrame(connectivity_data)
        df["status"] = df["is_connectable"].apply(get_status_color)
        df.columns = [col.replace("_info", "") for col in df.columns]
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
                "status": "Status",
                "server_id": "Server ID",
                "host": "IP",
                "core": "#Core",
                "logical_process": "#Logical Process",
                "Memory_size": "Memory Size",
                "System_OS": "OS",
            },
            inplace=True,
        )

        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Server ID": st.column_config.TextColumn("Server ID"),
                "IP": st.column_config.TextColumn("IP", width="small"),
                "CPU": st.column_config.TextColumn("CPU", width="medium"),
                "GPU": st.column_config.TextColumn("GPU", width="medium"),
                "#Core": st.column_config.NumberColumn("#Core", format="%d", width="small"),
                "#Logical Process": st.column_config.NumberColumn(
                    "#Logical Process", format="%d", width="small"
                ),
                "Memory Size": st.column_config.TextColumn("Memory Size"),
                "OS": st.column_config.TextColumn("OS", width="medium"),
            },
        )
    except Exception as exc:
        logger.error("Error processing connectivity data: %s", exc)
        st.error("Error processing server connectivity data.")


def display_server_usage_data(usage_data, latest_timestamp) -> None:
    """
    Display a data table of server usage data.

    Parameters:
        usage_data: Usage data list.
        latest_timestamp: Latest usage timestamp.
    Returns:
        None
    Raises:
        None
    """
    if not latest_timestamp or not usage_data:
        st.warning("No usage data available.")
        return

    formatted_timestamp = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"###### Last usage check: {formatted_timestamp}")

    try:
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
    except Exception as exc:
        logger.error("Error processing usage data: %s", exc)
        st.error("Error processing server usage data.")


def get_disk_c_usage_percentage(connection, server_id: int):
    """
    Calculate disk usage percentage for a server.

    Parameters:
        connection: Database connection.
        server_id (int): Server identifier.
    Returns:
        tuple: (percentage, total_gb, used_gb).
    Raises:
        None
    """
    try:
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
    except Exception as exc:
        logger.error("Error calculating disk usage for server %s: %s", server_id, exc)

    return 0, 0, 0


def generate_lights_html(num_active_users: int, max_lights: int = 4) -> str:
    """
    Generate HTML dots for user activity indicators.

    Parameters:
        num_active_users (int): Number of active users.
        max_lights (int): Maximum lights to display.
    Returns:
        str: HTML string with colored dots.
    Raises:
        None
    """
    light_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
    lights = []
    for i in range(max_lights):
        light_color = (
            light_colors[min(num_active_users, max_lights) - 1]
            if i < num_active_users
            else "#6c757d"
        )
        lights.append(
            "<div style='width: 0.6em; height: 0.6em; border-radius: 50%; "
            "margin-right: 0.3em; background-color: "
            f"{light_color};'></div>"
        )
    return "".join(lights)


def show_expanded_info(connection, server_id: int, active_users, active_usernames) -> None:
    """
    Display detailed metrics and active user details for a server.

    Parameters:
        connection: Database connection.
        server_id (int): Server identifier.
        active_users: List of active user records.
        active_usernames: List of active user name records.
    Returns:
        None
    Raises:
        None
    """
    try:
        recent_data = query_recent_server_data(connection, server_id)
        if recent_data:
            df_recent = pd.DataFrame(recent_data)
            df_recent["timestamp"] = pd.to_datetime(df_recent["timestamp"])
            create_chart(df_recent)
        else:
            st.info(f"No usage data available for server ID {server_id}.")

        if active_users or active_usernames:
            df_active_users = (
                pd.DataFrame(active_users) if active_users else pd.DataFrame(columns=["username", "timestamp"])
            )
            df_active_usernames = (
                pd.DataFrame(active_usernames)
                if active_usernames
                else pd.DataFrame(columns=["user_name", "timestamp"])
            )

            df_merged = pd.concat([df_active_users, df_active_usernames], axis=1)
            df_merged = df_merged.rename(columns={"username": "Account", "user_name": "User"})
            if "timestamp" in df_merged.columns:
                df_merged = df_merged.drop(columns=["timestamp"])
            df_merged["User"] = df_merged["User"].fillna("Duplicate users")

            st.table(df_merged)
        else:
            st.info(f"No active accounts or users for server {server_id}.")
    except Exception as exc:
        logger.error("Error showing expanded info for server %s: %s", server_id, exc)
        st.error("Error retrieving server details. Please try again.")


def show_server_data(
    connection: pymysql.connections.Connection,
    row: pd.Series,
    latest_timestamp: datetime,
    booking_state: booking_utils.BookingState,
) -> None:
    """
    Render a single server card with usage data.

    Parameters:
        connection (pymysql.connections.Connection): Database connection.
        row (pd.Series): Usage row for the server.
        latest_timestamp (datetime): Latest usage timestamp.
        booking_state (booking_utils.BookingState): Current booking state.
    Returns:
        None
    Raises:
        None
    """
    try:
        server_id = int(row["Server ID"])
        active_users, active_usernames = get_active_users_and_names(connection, server_id, latest_timestamp)
        num_active_users = len(active_users) if active_users else 0

        disk_c_usage_percentage, total_capacity_gb, used_capacity_gb = get_disk_c_usage_percentage(
            connection, server_id
        )

        lights_html = generate_lights_html(num_active_users)

        booked_html = ""
        for booking_info in booking_state.values():
            if booking_info.get("server_id") == str(server_id) and booking_info.get("actual_release_at") is None:
                user = booking_info.get("user", "N/A")
                booked_html = f"<span class='booked-by-badge'>Booked by {user}</span>"
                break

        header_html = (
            "<div style='display: flex; justify-content: flex-start; align-items: center;'>"
            f"<div style='display: flex; align-items: center; margin-right: 0.6em;'>{lights_html}</div>"
            "<div style='display: flex; align-items: center;'>"
            f"<h4 style='font-weight: bold; margin: 0;'>{server_id}</h4>{booked_html}"
            "</div></div>"
        )
        st.html(header_html)

        st.markdown(create_progress_bar(row["CPU Usage (%)"], label="CPU"), unsafe_allow_html=True)
        st.markdown(create_progress_bar(row["Memory Usage (%)"], label="MEM"), unsafe_allow_html=True)

        disk_progress = create_progress_bar_disk(
            disk_c_usage_percentage, "Disk C", used_capacity_gb, total_capacity_gb
        )
        st.markdown(disk_progress, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 0.6em;'></div>", unsafe_allow_html=True)

        with st.expander(f"{server_id} more info", expanded=False):
            show_expanded_info(connection, server_id, active_users, active_usernames)
    except Exception as exc:
        logger.error("Error displaying server data: %s", exc)
        st.error(f"Error displaying server data for server {row.get('Server ID', 'unknown')}.")


def display_server_usage(
    connection: pymysql.connections.Connection,
    usage_data: Optional[List[Dict[str, Any]]],
    latest_timestamp: Optional[datetime],
) -> None:
    """
    Display usage data for all servers in a grid.

    Parameters:
        connection (pymysql.connections.Connection): Database connection.
        usage_data (Optional[List[Dict[str, Any]]]): Usage data list.
        latest_timestamp (Optional[datetime]): Latest usage timestamp.
    Returns:
        None
    Raises:
        None
    """
    booking_state = booking_utils.get_booking_state()

    try:
        if not usage_data:
            st.warning("No server usage data available.")
            return

        df_usage = pd.DataFrame(usage_data)
        df_usage["server_id"] = df_usage["server_id"].astype(int)
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

        for row_index in range(rows):
            cols = st.columns(cols_per_row)
            for col_index, index in enumerate(
                range(row_index * cols_per_row, (row_index + 1) * cols_per_row)
            ):
                if index < len(df_usage):
                    with cols[col_index]:
                        show_server_data(
                            connection,
                            df_usage.iloc[index],
                            latest_timestamp,
                            booking_state,
                        )
                else:
                    with cols[col_index]:
                        st.empty()

            if row_index < rows - 1:
                st.markdown(
                    "<hr style='margin-top: 1rem; margin-bottom: 1rem; border-top: 1px solid #ccc;' />",
                    unsafe_allow_html=True,
                )
    except Exception as exc:
        logger.error("Error displaying server usage: %s", exc)
        st.error("Error displaying server usage data.")


def show_statistics(connection, server_ids, latest_average_time) -> None:
    """
    Display aggregated CPU and memory statistics.

    Parameters:
        connection: Database connection.
        server_ids: List of server IDs.
        latest_average_time: Latest average timestamp.
    Returns:
        None
    Raises:
        None
    """
    try:
        if not server_ids:
            st.warning("No server IDs available for statistics.")
            return

        if not latest_average_time:
            st.warning("No data available for statistics.")
            return

        default_end_date = latest_average_time
        default_start_date = latest_average_time - timedelta(days=7)

        col_top1, col_top2 = st.columns([2, 1])
        with col_top1:
            st.markdown("**Select Servers**")
            selected_servers = st.multiselect(
                "Servers",
                options=server_ids,
                default=[],
                placeholder="Choose one or more servers",
                label_visibility="collapsed",
            )
        with col_top2:
            preset = st.radio("Quick range", ["1d", "3d", "7d", "Custom"], horizontal=True, index=2)

        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Start", default_start_date)
        with col_date2:
            end_date = st.date_input("End (latest statistical time)", default_end_date)

        if preset != "Custom":
            days = int(preset.replace("d", ""))
            start_date = end_date - timedelta(days=days)
            st.info(f"Using quick range: last {days} day(s)")

        if start_date and end_date:
            if start_date > end_date:
                st.error("Start date cannot be after end date.")
                return
            if not selected_servers:
                st.warning("Please select at least one server.")
                return

            all_times = pd.date_range(start=start_date, end=end_date, freq="10min")
            df_all_times = pd.DataFrame(all_times, columns=["Time"])

            cpu_traces = []
            mem_traces = []

            with st.spinner("Loading statistics..."):
                for server_id in selected_servers:
                    data = fetch_server_metrics(server_id, start_date, end_date)
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
                            visible=True,
                        )
                        mem_trace = go.Scatter(
                            x=df_merged["Time"],
                            y=df_merged["average_memory_usage"],
                            mode="lines",
                            name=f"{server_id}",
                            connectgaps=False,
                            visible=True,
                        )

                        cpu_traces.append(cpu_trace)
                        mem_traces.append(mem_trace)

            if not cpu_traces:
                st.info("No data available for the selected date range.")
                return

            def create_layout(title: str, yaxis_title: str) -> go.Layout:
                """
                Build a Plotly layout configuration.

                Parameters:
                    title (str): Chart title.
                    yaxis_title (str): Y-axis title.
                Returns:
                    go.Layout: Layout configuration.
                Raises:
                    None
                """
                return go.Layout(
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

            fig_cpu = go.Figure(data=cpu_traces, layout=create_layout("Servers CPU Usage", "CPU (%)"))
            fig_mem = go.Figure(data=mem_traces, layout=create_layout("Servers Memory Usage", "Memory (%)"))

            col_plot1, col_plot2 = st.columns(2)
            with col_plot1:
                st.plotly_chart(fig_cpu, width="stretch")
            with col_plot2:
                st.plotly_chart(fig_mem, width="stretch")
        else:
            st.info("Please select a valid date range to display statistics.")
    except Exception as exc:
        logger.error("Error showing statistics: %s", exc)
        st.error("Error displaying statistics. Please try again later.")


def show_server_monitor_system() -> None:
    """
    Render the main monitor tabs.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    try:
        st.markdown("<h1 class='main-title'>Server Monitor System</h1>", unsafe_allow_html=True)
        st.caption(f"Version: {get_app_version()}")

        tab_usage, tab_status, tab_stats = st.tabs(["Server Usage", "Server Status", "Statistics"])

        with tab_usage:
            st_autorefresh(interval=DefaultConfig.REFRESH_INTERVAL_MS, key="server_monitor_autorefresh")
            render_usage_fragment()

        with tab_status:
            render_status_fragment()

        with tab_stats:
            render_statistics_fragment()
    except Exception as exc:
        logger.error("Error in server monitor system: %s", exc)
        st.error("An error occurred while loading the server monitor. Please refresh the page.")


@st.cache_resource(ttl=300)
def get_global_active_users() -> Dict[str, float]:
    """
    Access the global active user tracking map.

    Parameters:
        None
    Returns:
        Dict[str, float]: Session activity timestamps.
    Raises:
        None
    """
    if "active_users" not in st.session_state:
        st.session_state.active_users = {}
    return st.session_state.active_users


def update_user_activity(session_id: str) -> None:
    """
    Update activity timestamp for a session.

    Parameters:
        session_id (str): Session identifier.
    Returns:
        None
    Raises:
        None
    """
    active_users = get_global_active_users()
    active_users[session_id] = time.time()


def clean_offline_users(active_users: Dict[str, float], threshold: int = DefaultConfig.USER_OFFLINE_THRESHOLD_S) -> None:
    """
    Remove inactive sessions from the active user map.

    Parameters:
        active_users (Dict[str, float]): Active user map.
        threshold (int): Inactivity threshold in seconds.
    Returns:
        None
    Raises:
        None
    """
    current_time = time.time()
    offline_users = [key for key, value in list(active_users.items()) if current_time - value > threshold]
    for key in offline_users:
        del active_users[key]


def setup_sidebar(active_users_count: int) -> None:
    """
    Build the sidebar navigation panel.

    Parameters:
        active_users_count (int): Current active session count.
    Returns:
        None
    Raises:
        None
    """
    with st.sidebar:
        st.title("ASUS SIPI")
        st.markdown(f"**Active users: {active_users_count}**")
        st.divider()
        st.markdown("### Links")

        if BULLETIN_IP:
            st.link_button("Announcement", BULLETIN_IP, width="stretch")
        if LIBRARY_IP:
            st.link_button("ASUS KM", LIBRARY_IP, width="stretch")
        if GIT_IP:
            st.link_button("ASUS Gitea", GIT_IP, width="stretch")
        if FILESTATION_IP:
            st.link_button("File Station", FILESTATION_IP, width="stretch")
        if ASUS_AUTOMATION_IP:
            st.link_button("SI Automation", ASUS_AUTOMATION_IP, width="stretch")
        if PI_AUTOMATION_IP:
            st.link_button("PI Automation", PI_AUTOMATION_IP, width="stretch")
        if OPEN_WEBUI_IP:
            st.link_button("SIPI AI Hub", OPEN_WEBUI_IP, width="stretch")


def render_usage_fragment() -> None:
    """
    Render server usage data with its own DB lifecycle.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        latest_timestamp = get_latest_timestamp(connection)
        usage_data = query_server_usage(connection, latest_timestamp)
        display_server_usage(connection, usage_data, latest_timestamp)
    finally:
        connection.close()


def render_status_fragment() -> None:
    """
    Render server connectivity status.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        latest_check_time = query_latest_check_time(connection)
    finally:
        connection.close()

    display_latest_server_connectivity(latest_check_time)


def render_statistics_fragment() -> None:
    """
    Render statistics charts.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    connection = get_database_connection()
    try:
        latest_average_time = get_latest_average_timestamp(connection)
        server_ids = get_server_ids(connection)
        show_statistics(connection, server_ids, latest_average_time)
    finally:
        connection.close()


def render_server_monitor_page() -> None:
    """
    Navigation wrapper for the monitor page.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    show_server_monitor_system()


def render_booking_page() -> None:
    """
    Navigation wrapper for the booking page.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    booking.show_booking_page()


def main() -> None:
    """
    Application entry point.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    try:
        configure_page()

        st.markdown("<div class='credit'>Created by Sean Lin</div>", unsafe_allow_html=True)

        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

        update_user_activity(st.session_state.session_id)
        active_users = get_global_active_users()
        clean_offline_users(active_users)

        setup_sidebar(len(active_users))

        pages = [
            st.Page(render_server_monitor_page, title="Server Monitor", icon=":bar_chart:"),
            st.Page(render_booking_page, title="Server Booking", icon=":clipboard:"),
        ]
        nav = st.navigation(pages)
        nav.run()

    except Exception as exc:
        logger.error("Fatal application error: %s", exc)
        st.error("An unexpected error occurred. Please refresh the page or contact support.")


if __name__ == "__main__":
    main()
