import streamlit as st
from plotly import graph_objs as go
from db_config import DefaultConfig

library_ip = DefaultConfig.LIBRARY_IP

# 根據連接狀態返回對應的顏色標記
def get_status_color(is_connectable):
    return "🟢" if is_connectable else "🔴"

# 注入自定義CSS樣式
def inject_custom_css():
    with open('custom.css', 'r', encoding='utf-8') as f:  # 指定文件編碼為utf-8
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 根據百分比返回進度條顏色
def get_progress_bar_color(percentage):
    if percentage < 21:
        return "#4caf50"  # 綠色
    elif percentage < 41:
        return "#2196f3"  # 藍色
    elif percentage < 61:
        return "#ffeb3b"  # 黃色
    elif percentage < 81:
        return "#ff9800"  # 橘色
    else:
        return "#f44336"  # 紅色

# 創建磁盤使用情況的進度條
def create_progress_bar_disk(usage_percentage, label, used_gb, total_gb):
    color = get_progress_bar_color(usage_percentage)
    progress_bar_html = f"""
    <div style='display: flex; align-items: center; margin-top: 0.3em;'>
        <span style='margin-right: 0.7em; white-space: nowrap;'>{label}</span>
        <div style="background-color: #d0d3d8; border-radius: 0; position: relative; height: 1.5em; width: 100%;">
            <div style="background-color: {color}; width: {usage_percentage}%; height: 100%; border-radius: 0;"></div>
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold; font-size: 1em;">
                {used_gb:.2f} / {total_gb:.2f}GB
            </div>
        </div>
    </div>
    """
    return progress_bar_html

# 創建一般進度條
def create_progress_bar(percentage):
    color = get_progress_bar_color(percentage)
    progress_bar_style = f"""
    <div style="background-color: #d0d3d8; border-radius: 0; position: relative; height: 1.5em; width: 100%;">
        <div style="background-color: {color}; width: {percentage}%; height: 100%; border-radius: 0;"></div>
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold; font-size: 1em;">{percentage}%</div>
    </div>
    """
    return progress_bar_style

# 創建CPU和內存使用情況的圖表
def create_chart(df_recent):
    cpu_trace = go.Scatter(
        x=df_recent['timestamp'],
        y=df_recent['cpu_usage'],
        name='CPU Usage',
        mode='lines',
        line=dict(color='blue'),
        hoverinfo='text+y',  # 顯示自定義文本和y值
        hovertemplate='CPU: %{y:.2f}%<extra></extra>',  # 定義懸停文本格式，不顯示額外的懸停信息
    )
    mem_trace = go.Scatter(
        x=df_recent['timestamp'],
        y=df_recent['memory_usage'],
        name='Memory Usage',
        mode='lines',
        line=dict(color='green'),
        hoverinfo='text+y',  # 顯示自定義文本和y值
        hovertemplate='MEM: %{y:.2f}%<extra></extra>',  # 定義懸停文本格式，不顯示額外的懸停信息
    )
    layout = go.Layout(
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=True, range=[0, 100]),
        height=200,
        hovermode='x unified',  # 同一x位置的點共享懸停框，並顯示在圖表的上方
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),  # 設置圖表的上下左右邊距
    )
    
    fig = go.Figure(data=[cpu_trace, mem_trace], layout=layout)
    fig.add_shape(
        type='rect',
        x0=0,  # X軸起始位置（根據實際坐標調整）
        y0=0,  # Y軸起始位置
        x1=1,  # X軸結束位置（根據實際坐標調整）
        y1=100,  # Y軸結束位置
        line=dict(
            color='black',
            width=1
        ),
        xref='paper',  # 相對於圖表的寬度
        yref='y'  # 相對於Y軸
    )
    st.plotly_chart(fig, use_container_width=False)

# 創建打開新頁面的按鈕
def create_open_new_page_button(button_text, url):
    html_code = f"""
    <style>
        .custom-button {{
            background-color: transparent;
            padding: 0.5em 6em;
            border-radius: 0.25em;
            cursor: pointer;
            font-size: 1em;
            display: inline-block;
            text-align: center;
            text-decoration: none;
            margin: 0 0 0.5em 0;  /* 添加下邊距 */
        }}
        .custom-button:link, .custom-button:visited {{
            color: #2894FF;
            text-decoration: none; /* 移除下劃線 */
        }}
        .custom-button:hover {{
            background-color: #22232a;
            color: #dd574b; /* 滑鼠移過去時文字改為紅色 */
        }}
        .button-container {{
            display: flex;
            justify-content: center;
        }}
    </style>
    <div class="button-container">
        <a href="{url}" target="_blank" class="custom-button">
            {button_text}
        </a>
    </div>
    """
    return html_code