import streamlit as st
import pymysql
import pandas as pd
from plotly import graph_objs as go
from streamlit_autorefresh import st_autorefresh
from datetime import timedelta
import logging
from functools import lru_cache

# Optimize imports by importing only what's needed
from utils import get_status_color, inject_custom_css, create_progress_bar, create_progress_bar_disk, create_chart, create_open_new_page_button
from version_updates import display_version_updates, updates_data
from db_utils import (
    get_database_connection,
    query_latest_check_time,
    query_latest_server_connectivity,
    query_server_usage,
    get_disk_c_usage,
    get_latest_timestamp,
    get_active_users_and_names,
    get_server_metrics_averages,
    get_server_ids,
    get_latest_average_timestamp,
    query_recent_server_data
)
from db_config import DefaultConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='server_monitor.log'
)
logger = logging.getLogger(__name__)

# Constants - move to top for better readability and maintenance
LIBRARY_IP = DefaultConfig.LIBRARY_IP
GIT_IP = DefaultConfig.GIT_IP
FILESTATION_IP = DefaultConfig.FILE_STATION_PAGE
BULLETIN_IP = DefaultConfig.BULLETIN_BOARD
REFRESH_INTERVAL = 20000  # 20 seconds
PAGE_TITLE = "ASUS SI/PI"
PAGE_ICON = ":desktop_computer:"

# Cache page configuration to avoid recalculation
@st.cache_resource
def configure_page():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

# Cache server connectivity data to reduce database queries
@lru_cache(maxsize=32)
def get_cached_server_connectivity(check_time_str):
    """Cache server connectivity data based on check time"""
    connection = get_database_connection()
    try:
        data = query_latest_server_connectivity(connection)
        return data
    except Exception as e:
        logger.error(f"Error fetching server connectivity: {e}")
        return None
    finally:
        connection.close()

def display_latest_server_connectivity(latest_check_time):
    """Display server connectivity with better error handling"""
    formatted_time = latest_check_time.strftime('%Y-%m-%d %H:%M:%S') if latest_check_time else "Unknown"
    st.markdown(f"###### Last connect checked: {formatted_time}")
    
    # Use the check time string as a cache key
    check_time_str = str(latest_check_time) if latest_check_time else "none"
    connectivity_data = get_cached_server_connectivity(check_time_str)
    
    if connectivity_data:
        try:
            df = pd.DataFrame(connectivity_data)
            df['status'] = df['is_connectable'].apply(get_status_color)
            df.rename(columns=lambda x: x.replace('_info', ''), inplace=True)
            df = df[['status', 'server_id', 'host', 'CPU', 'GPU', 'core', 'logical_process', 'Memory_size', 'System_OS']]
            df.rename(columns={
                'server_id': 'Server ID',
                'host': 'IP',
                'core': '#Core',
                'logical_process': '#Logical Process',
                'Memory_size': 'Memory Size',
                'OS': 'OS'
            }, inplace=True)
            
            # Use a container to ensure proper styling
            with st.container():
                st.dataframe(df.style.map(lambda v: 'color: green;' if v == "🟢" else 'color: red;', subset=['status']))
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
    formatted_timestamp = latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    st.markdown(f"###### Last usage checked: {formatted_timestamp}")
    
    # Convert to DataFrame
    try:
        df_usage = pd.DataFrame(usage_data)
        df_usage.rename(columns={
            'server_id': 'Server ID',
            'cpu_usage': 'CPU Usage (%)',
            'memory_usage': 'Memory Usage (%)',
        }, inplace=True)
        
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
            total_capacity_gb = disk_c_data['total_capacity_gb']
            remaining_capacity_gb = disk_c_data['remaining_capacity_gb']
            used_capacity_gb = total_capacity_gb - remaining_capacity_gb
            return round((used_capacity_gb / total_capacity_gb) * 100, 2), total_capacity_gb, used_capacity_gb
    except Exception as e:
        logger.error(f"Error calculating disk usage for server {server_id}: {e}")
    
    # Return default values if there's an error
    return 0, 0, 0

def generate_lights_html(num_active_users, max_lights=4):
    """Generate HTML for user activity indicators"""
    light_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
    lights = []
    for i in range(max_lights):
        light_color = light_colors[min(num_active_users, max_lights) - 1] if i < num_active_users else "#6c757d"
        lights.append(f"<div style='width: 0.6em; height: 0.6em; border-radius: 50%; margin-right: 0.3em; background-color: {light_color}; transform: translateY(-0.5em);'></div>")
    return "".join(lights)

def show_expanded_info(connection, server_id, active_users, active_usernames):
    """Show expanded server info with error handling"""
    try:
        recent_data = query_recent_server_data(connection, server_id)
        if recent_data:
            df_recent = pd.DataFrame(recent_data)
            df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'])
            create_chart(df_recent)
        else:
            st.info(f"No usage data available for server ID {server_id}")
            
        # Process user data
        if active_users or active_usernames:
            # Merge user data
            df_active_users = pd.DataFrame(active_users) if active_users else pd.DataFrame(columns=['username', 'timestamp'])
            df_active_usernames = pd.DataFrame(active_usernames) if active_usernames else pd.DataFrame(columns=['user_name', 'timestamp'])
            
            # Create merged user data
            df_merged = pd.concat([df_active_users, df_active_usernames], axis=1)
            df_merged = df_merged.rename(columns={'username': 'Account', 'user_name': 'User'})
            if 'timestamp' in df_merged.columns:
                df_merged = df_merged.drop(columns=['timestamp'])
            df_merged['User'] = df_merged['User'].fillna('Duplicate users')
            
            st.table(df_merged)
        else:
            st.info(f"No active accounts or users at server {server_id}")
    except Exception as e:
        logger.error(f"Error showing expanded info for server {server_id}: {e}")
        st.error(f"Error retrieving server details. Please try again.")

def show_server_data(connection, row, latest_timestamp):
    """Display server data with user count indicators"""
    try:
        server_id = int(row['Server ID'])
        active_users, active_usernames = get_active_users_and_names(connection, server_id, latest_timestamp)
        num_active_users = len(active_users) if active_users else 0

        # Get disk C usage
        disk_c_usage_percentage, total_capacity_gb, used_capacity_gb = get_disk_c_usage_percentage(connection, server_id)

        # Generate HTML for user indicators
        lights_html = generate_lights_html(num_active_users)

        # Create server header with user indicators
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
            unsafe_allow_html=True
        )

        # Add disk usage bar
        disk_progress = create_progress_bar_disk(disk_c_usage_percentage, 'Disk C', used_capacity_gb, total_capacity_gb)
        st.markdown(
            f"{disk_progress}",
            unsafe_allow_html=True
        )
        
        # Add spacing
        st.markdown("<div style='margin-top: 0.6em;'></div>", unsafe_allow_html=True)
        
        # Add expandable section for more server details
        with st.expander(f" {server_id} more info", expanded=False):
            show_expanded_info(connection, server_id, active_users, active_usernames)
    except Exception as e:
        logger.error(f"Error displaying server data: {e}")
        st.error(f"Error displaying server data for server {row.get('Server ID', 'unknown')}.")

def display_server_usage(connection, usage_data, latest_timestamp):
    """Display server usage in a grid layout with error handling"""
    try:
        if not usage_data:
            st.warning("No server usage data available.")
            return
            
        df_usage = pd.DataFrame(usage_data)
        df_usage['server_id'] = df_usage['server_id'].astype(int)
        df_usage.rename(columns={
            'server_id': 'Server ID',
            'cpu_usage': 'CPU Usage (%)',
            'memory_usage': 'Memory Usage (%)'
        }, inplace=True)
        
        # Calculate grid layout
        cols_per_row = 5
        rows = (len(df_usage) + cols_per_row - 1) // cols_per_row
        
        # Create grid of server cards
        for i in range(rows):
            cols = st.columns(cols_per_row)
            for j, index in enumerate(range(i * cols_per_row, (i + 1) * cols_per_row)):
                if index < len(df_usage):
                    with cols[j]:
                        show_server_data(connection, df_usage.iloc[index], latest_timestamp)
                else:
                    with cols[j]:
                        st.empty()
            
            # Add separator between rows (except after the last row)
            if i < rows - 1:
                st.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem; border-top: 1px solid #ccc;'/>", unsafe_allow_html=True)
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
        
        # Create date range selector
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Start", default_start_date)
        with col_date2:
            end_date = st.date_input("End (latest statistical time)", default_end_date)
        
        if start_date and end_date:
            if start_date > end_date:
                st.error("Start date cannot be after end date.")
                return
                
            # Create time series for all expected data points
            all_times = pd.date_range(start=start_date, end=end_date, freq='10min')
            df_all_times = pd.DataFrame(all_times, columns=['Time'])
            
            cpu_traces, mem_traces = [], []
            
            # Process data for each server
            with st.spinner("Loading statistics..."):
                for server_id in server_ids:
                    data = get_server_metrics_averages(connection, server_id, start_date, end_date)
                    if data:
                        # Convert to DataFrame and merge with time series
                        df = pd.DataFrame(data)
                        df.rename(columns={'average_timestamp': 'Time'}, inplace=True)
                        df_merged = pd.merge(df_all_times, df, on='Time', how='outer')
                        
                        # Create traces for CPU and memory
                        cpu_trace = go.Scatter(
                            x=df_merged['Time'],
                            y=df_merged['average_cpu_usage'],
                            mode='lines',
                            name=f'{server_id}',
                            connectgaps=False,
                            visible='legendonly'
                        )
                        mem_trace = go.Scatter(
                            x=df_merged['Time'],
                            y=df_merged['average_memory_usage'],
                            mode='lines',
                            name=f'{server_id}',
                            connectgaps=False,
                            visible='legendonly'
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
                        xanchor='center',
                        yanchor='top',
                        font=dict(size=20)
                    ),
                    xaxis=dict(title='Time', range=[start_date, end_date]),
                    yaxis=dict(title=yaxis_title, range=[0, 100]),
                    height=600,
                    hovermode='x unified',
                    legend=dict(
                        orientation='h',
                        x=0,
                        y=1.18,
                        bgcolor='rgba(200,200,200,0.5)',
                        font=dict(size=15, family="Arial, sans-serif")
                    )
                )
            
            # Create figures
            fig_CPU = go.Figure(data=cpu_traces, layout=create_layout("Servers CPU Usage", 'CPU(%)'))
            fig_MEM = go.Figure(data=mem_traces, layout=create_layout("Servers Memory Usage", 'Memory (%)'))
            
            # Display charts in columns
            col_plot1, col_plot2 = st.columns(2)
            with col_plot1:
                st.plotly_chart(fig_CPU, use_container_width=True)
            with col_plot2:
                st.plotly_chart(fig_MEM, use_container_width=True)
        else:
            st.info("Please select a valid date range to display statistics.")
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        st.error("Error displaying statistics. Please try again later.")

def get_version():
    """Get the current version from updates data"""
    try:
        # Get the first element's version (latest version)
        return updates_data[0]['version']
    except (IndexError, KeyError):
        logger.error("Error retrieving version information")
        return "Unknown"

def calculate_wavelength_frequency(frequency, frequency_unit, wavelength, wavelength_unit):
    """Calculate wavelength or frequency based on speed of light"""
    c = 299792458  # Speed of light (m/s)
    unit_conversion = {'nm': 1e-9, 'μm': 1e-6, 'mm': 1e-3, 'cm': 1e-2, 'm': 1}
    unit_factors = {'Hz': 1, 'kHz': 1e3, 'MHz': 1e6, 'GHz': 1e9, 'THz': 1e12}
    
    # Convert input to base units
    calculated_wavelength = None
    calculated_frequency = None

    try:
        if frequency is not None:
            frequency_hz = frequency * unit_factors[frequency_unit]
            calculated_wavelength_m = c / frequency_hz
            calculated_wavelength = calculated_wavelength_m / unit_conversion[wavelength_unit]
        
        if wavelength is not None:
            wavelength_m = wavelength * unit_conversion[wavelength_unit]
            calculated_frequency_hz = c / wavelength_m
            calculated_frequency = calculated_frequency_hz / unit_factors[frequency_unit]
    except ZeroDivisionError:
        return None, None

    return calculated_wavelength, calculated_frequency

def show_calculator():
    """Display the wavelength/frequency calculator with improved layout"""
    # Initialize state if not present
    if 'switch' not in st.session_state:
        st.session_state.switch = False

    def switch_input():
        st.session_state.switch = not st.session_state.switch

    st.title("Wavelength/Frequency Converter")
    
    # Create main container
    with st.container():
        st.button('Reverse Conversion Direction', on_click=switch_input)
        
        col1, col2 = st.columns(2)
        
        with col1:
            use_scientific_notation = st.checkbox("Use Scientific Notation", value=False)
            
            col3, col4 = st.columns(2)
            
            with col3:
                # Select units
                frequency_unit = st.selectbox(
                    "Frequency Unit", 
                    ['Hz', 'kHz', 'MHz', 'GHz', 'THz'], 
                    index=3, 
                    key='frequency_unit_display'
                )
                
                # Input based on selected direction
                if st.session_state.switch:
                    frequency = st.number_input(
                        "Frequency (f)", 
                        min_value=0.0, 
                        value=1.0, 
                        step=0.1, 
                        key='frequency'
                    )
                    wavelength = None
                else:
                    wavelength = st.number_input(
                        "Wavelength (λ)", 
                        min_value=0.0, 
                        value=300.0, 
                        step=0.1, 
                        key='wavelength'
                    )
                    frequency = None
            
            with col4:
                # Select wavelength unit
                wavelength_unit = st.selectbox(
                    "Wavelength Unit", 
                    ['nm', 'μm', 'mm', 'cm', 'm'], 
                    index=4, 
                    key='wavelength_unit_display'
                )
                
                # Calculate and display results
                calculated_wavelength, calculated_frequency = calculate_wavelength_frequency(
                    frequency, 
                    frequency_unit, 
                    wavelength, 
                    wavelength_unit
                )
                
                # Display wavelength result if available
                if calculated_wavelength is not None:
                    st.write("Corresponding Wavelength:")
                    if use_scientific_notation:
                        st.write(f"{calculated_wavelength:.4e} {wavelength_unit}")
                    else:
                        st.write(f"{calculated_wavelength:.4f} {wavelength_unit}")
                
                # Display frequency result if available
                if calculated_frequency is not None:
                    st.write("Corresponding Frequency:")
                    if use_scientific_notation:
                        st.write(f"{calculated_frequency:.4e} {frequency_unit}")
                    else:
                        st.write(f"{calculated_frequency:.4f} {frequency_unit}")

        # Show formulas in second column
        with col2:
            st.write("### Formulas")
            col9, col10 = st.columns(2)
            with col9:
                st.latex(r"\lambda = \frac{c}{f}")
                st.latex(r"c = \lambda \cdot f")
                st.latex(r"f = \frac{c}{\lambda}")
            with col10:
                st.write("c = Speed of light (299,792,458 m/s)")
                st.write("f = Frequency (Hz)")
                st.write("λ = Wavelength (m)")

def show_server_monitor_system():
    """Main function to display the server monitor system with tabs"""
    try:
        # Get the current version
        version = get_version()
        
        # Display title with version
        st.markdown(f"<h1 class='main-title'>Server Monitor System <span class='version'>v.{version}</span></h1>", unsafe_allow_html=True)
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Server Usage", "Server Status", "Statistics", "Version Updates"])
        
        # Establish database connection
        connection = get_database_connection()
        
        # Tab 1: Server Usage
        with tab1:
            latest_timestamp = get_latest_timestamp(connection)
            usage_data = query_server_usage(connection, latest_timestamp)
            display_server_usage_data(usage_data, latest_timestamp)
            display_server_usage(connection, usage_data, latest_timestamp)
        
        # Tab 2: Server Status
        with tab2:
            latest_check_time = query_latest_check_time(connection)
            display_latest_server_connectivity(latest_check_time)
        
        # Tab 3: Statistics
        with tab3:
            latest_average_time = get_latest_average_timestamp(connection)
            server_ids = get_server_ids(connection)
            show_statistics(connection, server_ids, latest_average_time)
        
        # Tab 4: Version Updates
        with tab4:
            display_version_updates(st)
        
        # Close the database connection
        connection.close()
    except Exception as e:
        logger.error(f"Error in server monitor system: {e}")
        st.error("An error occurred while loading the server monitor. Please try refreshing the page.")

def navigate_to(page_name):
    """Navigate to a specific page"""
    st.session_state.current_page = page_name

def main():
    """Main application entry point"""
    try:
        # Configure the page
        configure_page()
        
        # Add credit
        st.markdown('<div class="credit">Created by Sean Lin</div>', unsafe_allow_html=True)

        # Initialize session state for navigation
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Server Monitor System'

        # Sidebar navigation
        st.sidebar.title("ASUS SIPI")
        
        # Create sidebar navigation buttons
        st.sidebar.markdown(create_open_new_page_button("Announcement Board", BULLETIN_IP), unsafe_allow_html=True)
        
        if st.sidebar.button("Server Monitor System", key="server_monitor_button"):
            navigate_to('Server Monitor System')
            
        if st.sidebar.button("Useful Calculator", key="calculator_button"):
            navigate_to('Calculator')

        # Display the selected page
        if st.session_state.current_page == 'Calculator':
            show_calculator()
        elif st.session_state.current_page == 'Server Monitor System':
            # Add auto-refresh for server monitor
            st_autorefresh(interval=REFRESH_INTERVAL, key='server_monitor_autorefresh')
            show_server_monitor_system()
        
        # Add external navigation links
        st.sidebar.markdown(create_open_new_page_button("ASUS KM", LIBRARY_IP), unsafe_allow_html=True)
        st.sidebar.markdown(create_open_new_page_button("Git", GIT_IP), unsafe_allow_html=True)
        st.sidebar.markdown(create_open_new_page_button("File Station", FILESTATION_IP), unsafe_allow_html=True)
    
    except Exception as e:
        logger.error(f"Fatal application error: {e}")
        st.error("An unexpected error occurred. Please refresh the page or contact support.")

if __name__ == "__main__":
    main()