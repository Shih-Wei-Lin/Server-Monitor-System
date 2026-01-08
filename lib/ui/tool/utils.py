"""
UI helper functions for Streamlit components.
"""

from pathlib import Path
from typing import Optional

import streamlit as st
from plotly import graph_objs as go


def get_status_color(is_connectable: bool) -> str:
    """
    Convert connectivity state to a status label.

    Parameters:
        is_connectable (bool): True if the server is reachable.
    Returns:
        str: Status label.
    Raises:
        None
    """
    return "UP" if is_connectable else "DOWN"


def inject_custom_css() -> None:
    """
    Inject the custom CSS stylesheet into the Streamlit app.

    Parameters:
        None
    Returns:
        None
    Raises:
        OSError: If the CSS file cannot be read.
    """
    css_path = Path(__file__).resolve().parent / "custom.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def get_progress_bar_color(percentage: float) -> str:
    """
    Choose a color based on usage percentage.

    Parameters:
        percentage (float): Usage percentage.
    Returns:
        str: Hex color string.
    Raises:
        None
    """
    if percentage < 21:
        return "#4caf50"
    if percentage < 41:
        return "#2196f3"
    if percentage < 61:
        return "#ffeb3b"
    if percentage < 81:
        return "#ff9800"
    return "#f44336"


def create_progress_bar_disk(usage_percentage: float, label: str, used_gb: float, total_gb: float) -> str:
    """
    Build a disk usage progress bar HTML snippet.

    Parameters:
        usage_percentage (float): Usage percentage.
        label (str): Label text.
        used_gb (float): Used capacity in GB.
        total_gb (float): Total capacity in GB.
    Returns:
        str: HTML markup for the progress bar.
    Raises:
        None
    """
    color = get_progress_bar_color(usage_percentage)
    return (
        "<div class='progress-bar-container'>"
        f"<span class='progress-bar-label'>{label}</span>"
        "<div class='progress-bar-wrapper'>"
        f"<div class='progress-bar-inner' style='background-color: {color}; width: {usage_percentage}%'></div>"
        "<div class='progress-bar-text'>"
        f"{used_gb:.2f} / {total_gb:.2f} GB"
        "</div>"
        "</div>"
        "</div>"
    )


def create_progress_bar(percentage: float, label: Optional[str] = None) -> str:
    """
    Build a generic usage progress bar HTML snippet.

    Parameters:
        percentage (float): Usage percentage.
        label (Optional[str]): Optional label text.
    Returns:
        str: HTML markup for the progress bar.
    Raises:
        None
    """
    color = get_progress_bar_color(percentage)
    if label:
        return (
            "<div class='progress-bar-container'>"
            f"<span class='progress-bar-label'>{label}</span>"
            "<div class='progress-bar-wrapper'>"
            f"<div class='progress-bar-inner' style='background-color: {color}; width: {percentage}%'></div>"
            "<div class='progress-bar-text'>"
            f"{percentage:.0f}%"
            "</div>"
            "</div>"
            "</div>"
        )

    return (
        "<div class='progress-bar-wrapper'>"
        f"<div class='progress-bar-inner' style='background-color: {color}; width: {percentage}%'></div>"
        "<div class='progress-bar-text'>"
        f"{percentage:.0f}%"
        "</div>"
        "</div>"
    )


def create_chart(df_recent) -> None:
    """
    Render a CPU and memory usage chart.

    Parameters:
        df_recent: DataFrame with timestamp, cpu_usage, memory_usage.
    Returns:
        None
    Raises:
        None
    """
    cpu_trace = go.Scatter(
        x=df_recent["timestamp"],
        y=df_recent["cpu_usage"],
        name="CPU Usage",
        mode="lines",
        line=dict(color="blue"),
        hoverinfo="text+y",
        hovertemplate="CPU: %{y:.2f}%<extra></extra>",
    )
    mem_trace = go.Scatter(
        x=df_recent["timestamp"],
        y=df_recent["memory_usage"],
        name="Memory Usage",
        mode="lines",
        line=dict(color="green"),
        hoverinfo="text+y",
        hovertemplate="MEM: %{y:.2f}%<extra></extra>",
    )
    layout = go.Layout(
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=True, range=[0, 100]),
        height=200,
        hovermode="x unified",
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
    )

    fig = go.Figure(data=[cpu_trace, mem_trace], layout=layout)
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=1,
        y1=100,
        line=dict(color="black", width=1),
        xref="paper",
        yref="y",
    )
    st.plotly_chart(fig, use_container_width=False)


def create_open_new_page_button(button_text: str, url: str) -> str:
    """
    Build a simple HTML link button.

    Parameters:
        button_text (str): Button label.
        url (str): Destination URL.
    Returns:
        str: HTML markup for the button.
    Raises:
        None
    """
    return (
        "<div class='button-container'>"
        f"<a href='{url}' target='_blank' class='custom-button'>{button_text}</a>"
        "</div>"
    )
