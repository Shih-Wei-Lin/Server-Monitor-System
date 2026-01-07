import os
import textwrap

import streamlit as st
from plotly import graph_objs as go

from lib.db_config import DefaultConfig

library_ip = DefaultConfig.LIBRARY_IP
# 給定連接狀態，返回對應的顏色標記


def get_status_color(is_connectable):
    return "🟢" if is_connectable else "🔴"


def inject_custom_css():
    try:
        css_path = os.path.join(os.path.dirname(__file__), "custom.css")
        with open(css_path, "r", encoding="utf-8") as f:  # 指定文件编码为utf-8
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"CSS 載入失敗：{e}")


def get_progress_bar_color(percentage):
    if percentage < 21:
        return "#4caf50"  # 绿色
    elif percentage < 41:
        return "#2196f3"  # 蓝色
    elif percentage < 61:
        return "#ffeb3b"  # 黄色
    elif percentage < 81:
        return "#ff9800"  # 橘色
    else:
        return "#f44336"  # 红色


def create_progress_bar_disk(usage_percentage, label, used_gb, total_gb):
    color = get_progress_bar_color(usage_percentage)
    progress_bar_html = f"""
    <div class='progress-bar-container'>
        <span class='progress-bar-label'>{label}</span>
        <div class='progress-bar-wrapper'>
            <div class='progress-bar-inner' style="background-color: {color}; width: {usage_percentage}%;"></div>
            <div class='progress-bar-text'>
                {used_gb:.2f} / {total_gb:.2f}GB
            </div>
        </div>
    </div>
    """
    return textwrap.dedent(progress_bar_html).strip()


def create_progress_bar(percentage, label):
    color = get_progress_bar_color(percentage)
    margin_map = {"CPU": "1.5em", "MEM": "1.25em"}
    margin = margin_map.get(label, "1.5em")
    progress_bar_style = f"""
    <div class="progress-bar-container">
        <span style="margin-right: {margin};">{label}</span>
        <div class="progress-bar-wrapper">
            <div class="progress-bar-inner" style="background-color: {color}; width: {percentage}%;"></div>
            <div class="progress-bar-text">{percentage}%</div>
        </div>
    </div>
    """
    return textwrap.dedent(progress_bar_style).strip()


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
        # plot_bgcolor='rgba(200,200,200,0.3)'  # 设置图表背景颜色为灰色
    )

    fig = go.Figure(data=[cpu_trace, mem_trace], layout=layout)
    # 添加边框的另一种方式是使用 shapes 参数来定义一个矩形边框
    fig.add_shape(
        type="rect",
        x0=0,  # X轴起始位置（根据实际坐标调整）
        y0=0,  # Y轴起始位置
        x1=1,  # X轴结束位置（根据实际坐标调整）
        y1=100,  # Y轴结束位置
        line=dict(color="black", width=1),
        xref="paper",  # 相对于图表的宽度
        yref="y",  # 相对于Y轴
    )
    st.plotly_chart(fig, width="content")


def create_open_new_page_button(button_text, url):
    html_code = f"""
    <div class="button-container">
        <a href="{url}" target="_blank" class="custom-button">
            {button_text}
        </a>
    </div>
    """
    return html_code


def create_link_button(button_text, url):
    html_code = f"""
    <div class="button-container">
        <a href="{url}" target="_blank" class="custom-button">
            {button_text}
        </a>
    </div>
    """
    return html_code
