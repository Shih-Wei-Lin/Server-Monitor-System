import datetime
import logging
import os
import subprocess
import sys
import textwrap
import time
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

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
from lib.UI import ServerBooking
from lib.UI.tool import booking_utils
from lib.UI.tool.db_utils import (get_active_users_and_names,
                                  get_database_connection, get_disk_c_usage,
                                  get_latest_average_timestamp,
                                  get_latest_timestamp, get_server_ids,
                                  get_server_metrics_averages,
                                  query_latest_check_time,
                                  query_latest_server_connectivity,
                                  query_recent_server_data, query_server_usage)
from lib.UI.tool.utils import (create_chart, create_progress_bar,
                               create_progress_bar_disk, get_status_color,
                               inject_custom_css)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="server_monitor.log",
)
logger = logging.getLogger(__name__)

# Constants are now in db_config.py
LIBRARY_IP = DefaultConfig.LIBRARY_IP
GIT_IP = DefaultConfig.GIT_IP
FILESTATION_IP = DefaultConfig.FILE_STATION_PAGE
BULLETIN_IP = DefaultConfig.BULLETIN_BOARD
ASUS_AUTOMATION_IP = DefaultConfig.ASUS_AUTOMATION
PI_AUTOMATION_IP = DefaultConfig.PI_AUTOMATION
OPEN_WEBUI_IP = DefaultConfig.OPEN_WEBUI


# Cache page configuration to avoid recalculation
def configure_page():
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


# Cache version for display; prefer env override, fallback to git describe
@st.cache_data(show_spinner=False)
def get_app_version() -> str:
    env_version = os.environ.get("SERVER_MONITOR_VERSION")
    if env_version:
        return env_version
    try:
        version = (
            subprocess.check_output(
                ["git", "describe", "--tags", "--always"], cwd=root_dir
            )
            .decode()
            .strip()
        )
        return version
    except Exception as e:
        logger.warning(f"Unable to read git version: {e}")
        return "unknown"


# Cache server connectivity data to reduce database queries
@st.cache_data(ttl=30)
def get_cached_server_connectivity(check_time_str: str):
    """Cache server connectivity data based on check time string to avoid hammering DB"""
    connection = get_database_connection()
    try:
        return query_latest_server_connectivity(connection)
    except Exception as e:
        logger.error(f"Error fetching server connectivity: {e}")
        return None
    finally:
        connection.close()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_server_metrics(server_id: int, start_date, end_date):
    """Cached wrapper to fetch metrics per server and date range."""
    connection = get_database_connection()
    try:
        return get_server_metrics_averages(connection, server_id, start_date, end_date)
    finally:
        connection.close()


def display_latest_server_connectivity(latest_check_time):
    """Display server connectivity with better error handling"""
    formatted_time = (
        latest_check_time.strftime("%Y-%m-%d %H:%M:%S")
        if latest_check_time
        else "Unknown"
    )
    st.markdown(f"###### Last connect checked: {formatted_time}")

    # Use the check time string as a cache key
    check_time_str = str(latest_check_time) if latest_check_time else "none"
    connectivity_data = get_cached_server_connectivity(check_time_str)

    if connectivity_data:
        try:
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

            with st.container():
                st.dataframe(
                    df,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "status": st.column_config.TextColumn("Status", width="small"),
                        "server_id": st.column_config.TextColumn("Server ID"),
                        "host": st.column_config.TextColumn("IP", width="small"),
                        "CPU": st.column_config.TextColumn("CPU", width="medium"),
                        "GPU": st.column_config.TextColumn("GPU", width="medium"),
                        "core": st.column_config.NumberColumn(
                            "#Core", format="%d", width="small"
                        ),
                        "logical_process": st.column_config.NumberColumn(
                            "#Logical Process", format="%d", width="small"
                        ),
                        "Memory_size": st.column_config.TextColumn("Memory Size"),
                        "System_OS": st.column_config.TextColumn("OS", width="medium"),
                    },
                )
        except Exception as e:
            logger.error(f"Error processing connectivity data: {e}")
            st.error("Error processing server connectivity data.")
    else:
        st.info("No server connection data available.")


def display_server_usage_data(usage_data, latest_timestamp):
    """Display server usage data with improved error handling"""
    if not latest_timestamp or not usage_data:
        st.warning("No usage data available.")
        return

    # Format timestamp
    formatted_timestamp = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"###### Last usage checked: {formatted_timestamp}")

    # Convert to DataFrame
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

        # Create expandable section for raw data
        with st.expander("Server Usage Data", expanded=False):
            st.dataframe(df_usage)
    except Exception as e:
        logger.error(f"Error processing usage data: {e}")
        st.error("Error processing server usage data.")


def get_disk_c_usage_percentage(connection, server_id):
    """Calculate disk usage with error handling"""
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
    except Exception as e:
        logger.error(f"Error calculating disk usage for server {server_id}: {e}")

    # Return default values if there's an error
    return 0, 0, 0


def generate_lights_html(num_active_users, max_lights=4):
    """Generate HTML for user activity indicators"""
    light_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
    lights = []
    for i in range(max_lights):
        light_color = (
            light_colors[min(num_active_users, max_lights) - 1]
            if i < num_active_users
            else "#6c757d"
        )
        lights.append(
            f'<div style="width: 0.6em; height: 0.6em; border-radius: 50%; margin-right: 0.3em; background-color: {light_color};"></div>'
        )
    return "".join(lights)


def show_expanded_info(connection, server_id, active_users, active_usernames):
    """Show expanded server info with error handling"""
    try:
        recent_data = query_recent_server_data(connection, server_id)
        if recent_data:
            df_recent = pd.DataFrame(recent_data)
            df_recent["timestamp"] = pd.to_datetime(df_recent["timestamp"])
            create_chart(df_recent)
        else:
            st.info(f"No usage data available for server ID {server_id}")

        # Process user data
        if active_users or active_usernames:
            # Merge user data
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

            # Create merged user data
            df_merged = pd.concat([df_active_users, df_active_usernames], axis=1)
            df_merged = df_merged.rename(
                columns={"username": "Account", "user_name": "User"}
            )
            if "timestamp" in df_merged.columns:
                df_merged = df_merged.drop(columns=["timestamp"])
            df_merged["User"] = df_merged["User"].fillna("Duplicate users")

            st.table(df_merged)
        else:
            st.info(f"No active accounts or users at server {server_id}")
    except Exception as e:
        logger.error(f"Error showing expanded info for server {server_id}: {e}")
        st.error("Error retrieving server details. Please try again.")


def show_server_data(
    connection: pymysql.connections.Connection,
    row: pd.Series,
    latest_timestamp: datetime.datetime,
    booking_state: booking_utils.BookingState,
) -> None:
    """Display an individual server's data card in the usage tab.

    This includes CPU, Memory, and Disk usage, as well as the number of
    active users and the current booking status.

    Args:
        connection: The database connection object.
        row (pd.Series): A row from the usage DataFrame containing this server's data.
        latest_timestamp (datetime.datetime): The timestamp of the latest data.
        booking_state (booking_utils.BookingState): The current booking state.
    """
    try:
        server_id = int(row["Server ID"])
        active_users, active_usernames = get_active_users_and_names(
            connection, server_id, latest_timestamp
        )
        num_active_users = len(active_users) if active_users else 0

        # Get disk C usage
        disk_c_usage_percentage, total_capacity_gb, used_capacity_gb = (
            get_disk_c_usage_percentage(connection, server_id)
        )

        # Generate HTML for user indicators
        lights_html = generate_lights_html(num_active_users)

        # Check booking status
        booked_html = ""
        for booking_id, booking_info in booking_state.items():
            if (
                booking_info.get("server_id") == str(server_id)
                and booking_info.get("actual_release_at") is None
            ):
                user = booking_info.get("user", "N/A")
                booked_html = f'<span class="booked-by-badge">Booked by {user}</span>'
                break  # Found the active booking for this server

        # Create server header with user indicators
        header_html = f"""
<div style='display: flex; justify-content: flex-start; align-items: center;'>
    <div style='display: flex; align-items: center; margin-right: 0.6em;'>{lights_html}</div>
    <div style='display: flex; align-items: center;'>
        <h4 style='font-weight: bold; margin: 0;'>{server_id}</h4>
        {booked_html}
    </div>
</div>
"""
        st.html(header_html)

        # CPU and Memory Progress Bars
        st.markdown(
            create_progress_bar(row["CPU Usage (%)"], "CPU"), unsafe_allow_html=True
        )
        st.markdown(
            create_progress_bar(row["Memory Usage (%)"], "MEM"), unsafe_allow_html=True
        )

        # Add disk usage bar
        disk_progress = create_progress_bar_disk(
            disk_c_usage_percentage, "Disk C", used_capacity_gb, total_capacity_gb
        )
        st.markdown(disk_progress, unsafe_allow_html=True)

        # Add spacing
        st.markdown("<div style='margin-top: 0.6em;'></div>", unsafe_allow_html=True)

        # Add expandable section for more server details
        with st.expander(f" {server_id} more info", expanded=False):
            show_expanded_info(connection, server_id, active_users, active_usernames)
    except Exception as e:
        logger.error(f"Error displaying server data: {e}")
        st.error(
            f"Error displaying server data for server {row.get('Server ID', 'unknown')}."
        )


def display_server_usage(
    connection: pymysql.connections.Connection,
    usage_data: Optional[List[Dict[str, Any]]],
    latest_timestamp: Optional[datetime.datetime],
) -> None:
    """Display server usage in a grid layout with error handling.

    This function fetches the current booking state and iterates through
    the usage data to display a card for each server.

    Args:
        connection: The database connection object.
        usage_data (Optional[List[Dict[str, Any]]]): A list of dictionaries,
            where each dictionary contains usage data for a server.
        latest_timestamp (Optional[datetime.datetime]): The timestamp of the
            latest usage data check.
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

        # Calculate grid layout
        cols_per_row = 5
        rows = (len(df_usage) + cols_per_row - 1) // cols_per_row

        # Create grid of server cards
        for i in range(rows):
            cols = st.columns(cols_per_row)
            for j, index in enumerate(range(i * cols_per_row, (i + 1) * cols_per_row)):
                if index < len(df_usage):
                    with cols[j]:
                        show_server_data(
                            connection,
                            df_usage.iloc[index],
                            latest_timestamp,
                            booking_state,
                        )
                else:
                    with cols[j]:
                        st.empty()

            # Add separator between rows (except after the last row)
            if i < rows - 1:
                st.markdown(
                    "<hr style='margin-top: 1rem; margin-bottom: 1rem; border-top: 1px solid #ccc;'/>",
                    unsafe_allow_html=True,
                )
    except Exception as e:
        logger.error(f"Error displaying server usage: {e}")
        st.error("Error displaying server usage data.")


def show_statistics(connection, server_ids, latest_average_time):
    """Show server statistics with improved date range controls"""
    try:
        if not server_ids:
            st.warning("No server IDs available for statistics.")
            return

        if not latest_average_time:
            st.warning("No data available for statistics.")
            return

        # Calculate default date range
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
            preset = st.radio(
                "Quick range",
                ["1d", "3d", "7d", "Custom"],
                horizontal=True,
                index=2,
            )

        # Create date range selector
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Start", default_start_date)
        with col_date2:
            end_date = st.date_input("End (latest statistical time)", default_end_date)

        # Apply quick preset if not custom
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

            # Create time series for all expected data points
            all_times = pd.date_range(start=start_date, end=end_date, freq="10min")
            df_all_times = pd.DataFrame(all_times, columns=["Time"])

            cpu_traces, mem_traces = [], []

            # Process data for each server
            with st.spinner("Loading statistics..."):
                for server_id in selected_servers:
                    data = fetch_server_metrics(server_id, start_date, end_date)
                    if data:
                        # Convert to DataFrame and merge with time series
                        df = pd.DataFrame(data)
                        df.rename(columns={"average_timestamp": "Time"}, inplace=True)
                        df_merged = pd.merge(df_all_times, df, on="Time", how="outer")

                        # Create traces for CPU and memory
                        cpu_trace = go.Scatter(
                            x=df_merged["Time"],
                            y=df_merged["average_cpu_usage"],
                            mode="lines",
                            name=f"{server_id}",
                            connectgaps=False,
                            visible=True,  # show by default since user selected
                        )
                        mem_trace = go.Scatter(
                            x=df_merged["Time"],
                            y=df_merged["average_memory_usage"],
                            mode="lines",
                            name=f"{server_id}",
                            connectgaps=False,
                            visible=True,  # show by default since user selected
                        )

                        cpu_traces.append(cpu_trace)
                        mem_traces.append(mem_trace)

            # Exit early if no data was found
            if not cpu_traces:
                st.info("No data available for the selected date range.")
                return

            # Create layout function for charts
            def create_layout(title, yaxis_title):
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

            # Create figures
            fig_CPU = go.Figure(
                data=cpu_traces, layout=create_layout("Servers CPU Usage", "CPU(%)")
            )
            fig_MEM = go.Figure(
                data=mem_traces,
                layout=create_layout("Servers Memory Usage", "Memory (%)"),
            )

            # Display charts in columns
            col_plot1, col_plot2 = st.columns(2)
            with col_plot1:
                st.plotly_chart(fig_CPU, width="stretch")
            with col_plot2:
                st.plotly_chart(fig_MEM, width="stretch")
        else:
            st.info("Please select a valid date range to display statistics.")
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        st.error("Error displaying statistics. Please try again later.")


def show_server_monitor_system():
    """Main function to display the server monitor system with tabs"""
    try:
        st.markdown(
            f"<h1 class='main-title'>Server Monitor System</h1>",
            unsafe_allow_html=True,
        )
        st.caption(f"Version: {get_app_version()}")

        tab1, tab2, tab3 = st.tabs(["Server Usage", "Server Status", "Statistics"])

        with tab1:
            st_autorefresh(
                interval=DefaultConfig.REFRESH_INTERVAL_MS,
                key="server_monitor_autorefresh",
            )
            render_usage_fragment()

        with tab2:
            render_status_fragment()

        with tab3:
            render_statistics_fragment()
    except Exception as e:
        logger.error(f"Error in server monitor system: {e}")
        st.error(
            "An error occurred while loading the server monitor. Please try refreshing the page."
        )


@st.cache_resource(ttl=300)
def get_global_active_users():
    if "active_users" not in st.session_state:
        st.session_state.active_users = {}
    return st.session_state.active_users


def update_user_activity(session_id):
    active_users = get_global_active_users()
    active_users[session_id] = time.time()


def clean_offline_users(active_users, threshold=DefaultConfig.USER_OFFLINE_THRESHOLD_S):
    current_time = time.time()
    # Filter out offline users
    offline_users = [
        k for k, v in list(active_users.items()) if current_time - v > threshold
    ]
    for k in offline_users:
        del active_users[k]


def setup_sidebar(active_users_count):
    """Creates and manages the sidebar navigation and displays."""
    with st.sidebar:
        st.title("ASUS SIPI")
        st.markdown(f"**當前線上人數：{active_users_count}**")
        st.divider()
        st.markdown("### Link Page")

        st.link_button("Announcement", BULLETIN_IP, width="stretch")
        st.link_button("ASUS KM", LIBRARY_IP, width="stretch")
        st.link_button("ASUS Gitea", GIT_IP, width="stretch")
        st.link_button("File Station", FILESTATION_IP, width="stretch")
        st.link_button("SI_Automation", ASUS_AUTOMATION_IP, width="stretch")
        st.link_button("PI_Automation", PI_AUTOMATION_IP, width="stretch")
        st.link_button("SIPI AI Hub", OPEN_WEBUI_IP, width="stretch")


def render_usage_fragment():
    """Render server usage with its own DB lifecycle to reduce rerun side effects."""
    connection = get_database_connection()
    try:
        latest_timestamp = get_latest_timestamp(connection)
        usage_data = query_server_usage(connection, latest_timestamp)
        display_server_usage(connection, usage_data, latest_timestamp)
    finally:
        connection.close()


def render_status_fragment():
    """Render server status; separated so other UI is not rerun unnecessarily."""
    connection = get_database_connection()
    try:
        latest_check_time = query_latest_check_time(connection)
    finally:
        connection.close()

    display_latest_server_connectivity(latest_check_time)


def render_statistics_fragment():
    """Render statistics charting with isolated DB lifecycle."""
    connection = get_database_connection()
    try:
        latest_average_time = get_latest_average_timestamp(connection)
        server_ids = get_server_ids(connection)
        show_statistics(connection, server_ids, latest_average_time)
    finally:
        connection.close()


def render_server_monitor_page():
    """Page wrapper for navigation API."""
    show_server_monitor_system()


def render_booking_page():
    """Navigation target for booking system to avoid auto-refresh interference."""
    ServerBooking.show_booking_page()


def main():
    """Main application entry point"""
    try:
        # Configure the page
        configure_page()

        # Add credit
        st.markdown(
            '<div class="credit">Created by Sean Lin</div>', unsafe_allow_html=True
        )

        active_users = get_global_active_users()

        # Generate unique Session ID
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

        # Update user activity
        update_user_activity(st.session_state.session_id)

        # Clean offline users
        active_users = get_global_active_users()
        clean_offline_users(active_users)

        setup_sidebar(len(active_users))

        pages = [
            st.Page(
                render_server_monitor_page, title="Server Monitor System", icon="🖥️"
            ),
            st.Page(render_booking_page, title="Server Booking", icon="📅"),
        ]
        nav = st.navigation(pages)
        nav.run()

    except Exception as e:
        logger.error(f"Fatal application error: {e}")
        st.error(
            "An unexpected error occurred. Please refresh the page or contact support."
        )


if __name__ == "__main__":
    main()
