import streamlit as st
from plotly import graph_objs as go
from db_config import DefaultConfig

library_ip =DefaultConfig.LIBRARY_IP
# 給定連接狀態，返回對應的顏色標記

def get_status_color(is_connectable):
    return "🟢" if is_connectable else "🔴"

def inject_custom_css():
    with open('custom.css', 'r', encoding='utf-8') as f:  # 指定文件编码为utf-8
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        
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
    # 根据百分比选择颜色
    color = get_progress_bar_color(usage_percentage)
    # 使用自定义样式的HTML来创建长方形进度条，文字加粗，并显示已用容量和总容量
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

def create_progress_bar(percentage):
    # 根据百分比选择颜色
    color = get_progress_bar_color(percentage)
    # 使用自定义样式的HTML来创建长方形进度条，文字加粗
    progress_bar_style = f"""
    <div style="background-color: #d0d3d8; border-radius: 0; position: relative; height: 1.5em; width: 100%;">
        <div style="background-color: {color}; width: {percentage}%; height: 100%; border-radius: 0;"></div>
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold; font-size: 1em;">{percentage}%</div>
    </div>
    """
    return progress_bar_style

def create_chart( df_recent):
    cpu_trace = go.Scatter(
        x=df_recent['timestamp'],
        y=df_recent['cpu_usage'],
        name='CPU Usage',
        mode='lines',
        line=dict(color='blue'),
        hoverinfo='text+y',  # 显示自定义文本和y值
        hovertemplate='CPU: %{y:.2f}%<extra></extra>',  # 定义悬停文本格式，不显示额外的悬停信息
    )
    mem_trace = go.Scatter(
        x=df_recent['timestamp'],
        y=df_recent['memory_usage'],
        name='Memory Usage',
        mode='lines',
        line=dict(color='green'),
        hoverinfo='text+y',  # 显示自定义文本和y值
        hovertemplate='MEM: %{y:.2f}%<extra></extra>',  # 定义悬停文本格式，不显示额外的悬停信息
    )
    layout = go.Layout(
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=True, range=[0, 100]),
        height=200,
        # width=300,
        hovermode='x unified', # 同一x位置的点共享悬停框，并显示在图表的上方
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),  # 设置图表的上下左右边距，t为上边距，b为下边距，l为左边距，r为右边距
        # plot_bgcolor='rgba(200,200,200,0.3)'  # 设置图表背景颜色为灰色
    )
    
    fig = go.Figure(data=[cpu_trace, mem_trace], layout=layout)
        # 添加边框的另一种方式是使用 shapes 参数来定义一个矩形边框
    fig.add_shape(
        type='rect',
        x0=0,  # X轴起始位置（根据实际坐标调整）
        y0=0,  # Y轴起始位置
        x1=1,  # X轴结束位置（根据实际坐标调整）
        y1=100,  # Y轴结束位置
        line=dict(
            color='black',
            width=1
        ),
        xref='paper',  # 相对于图表的宽度
        yref='y'  # 相对于Y轴
    )
    st.plotly_chart(fig, use_container_width=False)
    
def create_open_new_page_button(button_text, url):
    # 使用 HTML 和 CSS 來模仿 Streamlit 按鈕的樣式，并使文字居中
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
            margin: 0 0 0.5em 0;  /* 添加下边距 */
        }}
        .custom-button:link, .custom-button:visited {{
            color: #2894FF;
            text-decoration: none; /* 移除下划线 */
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