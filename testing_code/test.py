import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# 定義轉換函數
def frequency_to_wavelength(frequency, unit):
    # 將頻率轉換為赫茲
    if unit == 'GHz':
        frequency_hz = frequency * 1e9
    elif unit == 'MHz':
        frequency_hz = frequency * 1e6
    else:
        st.error("不支持的頻率單位")
        return None
    
    # 計算波長 (c = 299,792,458 m/s)
    wavelength_m = 299792458 / frequency_hz
    
    return wavelength_m

def convert_wavelength(wavelength_m, unit):
    if unit == 'mm':
        return wavelength_m * 1e3
    elif unit == 'cm':
        return wavelength_m * 1e2
    elif unit == 'm':
        return wavelength_m
    elif unit == 'mil':
        return wavelength_m * 1e3 / 25.4
    else:
        st.error("不支持的波長單位")
        return None

def rise_time_to_frequency(rise_time, unit):
    if unit == 'ps':
        rise_time_s = rise_time * 1e-12
    elif unit == 'ns':
        rise_time_s = rise_time * 1e-9
    elif unit == 'us':
        rise_time_s = rise_time * 1e-6
    else:
        st.error("不支持的上升時間單位")
        return None
    frequency_hz = 0.35 / rise_time_s
    frequency_ghz = frequency_hz / 1e9
    return frequency_ghz

def plot_knee_frequency():
    fig, ax = plt.subplots()
    f = np.logspace(-2, 1, 400)
    response = 1 / np.sqrt(1 + (f/1)**2)
    response_db = 20 * np.log10(response)
    
    ax.plot(f, response_db)
    ax.axvline(x=1, color='r', linestyle='--')
    ax.text(1.1, -3, 'Knee Frequency', color='r')
    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Response (dB)')
    ax.set_title('Knee Frequency示意圖')
    ax.grid(True, which="both", ls="--")
    
    st.pyplot(fig)

# Streamlit 應用
st.title("頻率-波長和上升時間-頻率轉換器")

tab1, tab2 = st.tabs(["頻率-波長轉換", "上升時間-頻率轉換"])

with tab1:
    st.header("頻率-波長轉換")
    
    col1, col2 = st.columns(2)
    with col1:
        frequency = st.number_input("輸入頻率", min_value=0.0, value=1.0)
    with col2:
        frequency_unit = st.selectbox("單位", ("GHz", "MHz"))
    
    # 計算波長
    wavelength_m = frequency_to_wavelength(frequency, frequency_unit)
    
    if wavelength_m is not None:
        col3, col4 = st.columns(2)
        with col3:
            wavelength_unit = st.selectbox("波長單位", ("mil", "mm", "cm", "m"))
        converted_wavelength = convert_wavelength(wavelength_m, wavelength_unit)
        
        if converted_wavelength is not None:
            with col4:
                st.write(f"波長：{converted_wavelength:.3f} {wavelength_unit}")

with tab2:
    st.header("上升時間-頻率轉換")
    
    col5, col6 = st.columns(2)
    with col5:
        rise_time = st.number_input("輸入上升時間", min_value=0.0, value=1.0)
    with col6:
        rise_time_unit = st.selectbox("單位", ("ps", "ns", "us"))
    
    if rise_time > 0:
        frequency_ghz = rise_time_to_frequency(rise_time, rise_time_unit)
        st.write(f"對應的頻率：{frequency_ghz:.3f} GHz")
    
    st.subheader("Knee Frequency 示意圖")
    plot_knee_frequency()