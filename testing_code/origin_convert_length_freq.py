import streamlit as st

# 單位轉換字典
wavelength_unit = {
    'mil': 0.0000254,
    'nm': 1e-9,
    'μm': 1e-6,
    'mm': 1e-3,
    'cm': 1e-2,
    'm': 1
}
frequency_unit = {
    'Hz': 1,
    'kHz': 1e3,
    'MHz': 1e6,
    'GHz': 1e9,
    'THz': 1e12
}

# 初始化狀態
def initialize_state():
    if "wavelength" not in st.session_state:
        st.session_state.wavelength = ""
    if "frequency" not in st.session_state:
        st.session_state.frequency = ""
    if "wavelength_unit" not in st.session_state:
        st.session_state.wavelength_unit = "mil"
    if "frequency_unit" not in st.session_state:
        st.session_state.frequency_unit = "GHz"
    if "use_scientific" not in st.session_state:
        st.session_state.use_scientific = False
    if "input_type" not in st.session_state:
        st.session_state.input_type = "完整波長"  # 默認為完整波長

    if "length" not in st.session_state:
        st.session_state.length = ""
    if "input_unit" not in st.session_state:
        st.session_state.input_unit = "mm"
    if "output_unit" not in st.session_state:
        st.session_state.output_unit = "mil"

    if "wavelength_tab2" not in st.session_state:
        st.session_state.wavelength_tab2 = ""
    if "frequency_tab2" not in st.session_state:
        st.session_state.frequency_tab2 = ""
    if "wavelength_unit_tab2" not in st.session_state:
        st.session_state.wavelength_unit_tab2 = "m"
    if "frequency_unit_tab2" not in st.session_state:
        st.session_state.frequency_unit_tab2 = "GHz"
    if "calculated_wave_tab2" not in st.session_state:
        st.session_state.calculated_wave_tab2 = ""
    if "calculated_frequency_tab2" not in st.session_state:
        st.session_state.calculated_frequency_tab2 = ""

    if "calculated_frequency_unit_tab2" not in st.session_state:
        st.session_state.calculated_frequency_unit_tab2 = ""
    if "calculated_wavelength_unit_tab2" not in st.session_state:
        st.session_state.calculated_wavelength_unit_tab2 = ""

    if "rerun_required" not in st.session_state:
        st.session_state.rerun_required = False

# 計算邏輯
def calculate_frequency_from_wavelength(wavelength, wavelength_unit_key, frequency_unit_key):
    c = 299792458  # 光速 (m/s)
    wavelength_m = wavelength * wavelength_unit[wavelength_unit_key]
    frequency_hz = c / wavelength_m
    return frequency_hz / frequency_unit[frequency_unit_key]

def calculate_wavelength_from_frequency(frequency, frequency_unit_key, wavelength_unit_key):
    c = 299792458  # 光速 (m/s)
    frequency_hz = frequency * frequency_unit[frequency_unit_key]
    wavelength_m = c / frequency_hz
    return wavelength_m / wavelength_unit[wavelength_unit_key]

# 自動單位切換
def auto_adjust_unit(value, key, unit):
    index = list(unit.keys()).index(key)
    length = len(unit)

    if value > 1000 and index == length - 1:
        return value, key

    if value < 1 and (index == 0 or key == 'nm'):
        return value, key

    while value > 1000 and index < length - 1:
        value /= 1000
        index += 1

    while value < 1 and (index == 0 or list(unit.keys())[index] != 'nm'):
        value *= 1000
        index -= 1

    return value, list(unit.keys())[index]

# 更新頻率
def update_frequency():
    global frequency_unit, wavelength_unit
    try:
        wavelength = float(st.session_state.wavelength)
        if st.session_state.input_type == "半波長":
            wavelength *= 2  # 將半波長轉為完整波長
        elif st.session_state.input_type == "1/4 波長":
            wavelength *= 4  # 將 1/4 波長轉為完整波長

        frequency = calculate_frequency_from_wavelength(
            wavelength,
            st.session_state.wavelength_unit,
            st.session_state.frequency_unit
        )

        frequency, frequency_unit_uu = auto_adjust_unit(frequency, st.session_state.frequency_unit, frequency_unit)
        st.session_state.frequency = f"{frequency:.2f}"
        st.session_state.frequency_unit = frequency_unit_uu

        wavelength, wavelength_unit_uu = auto_adjust_unit(wavelength, st.session_state.wavelength_unit, wavelength_unit)

        if st.session_state.input_type == "半波長":
            wavelength /= 2  # 將半波長轉為完整波長
            st.session_state.wavelength = f"{wavelength:.2f}"
        elif st.session_state.input_type == "1/4 波長":
            wavelength /= 4  # 將 1/4 波長轉為完整波長
            st.session_state.wavelength = f"{wavelength:.2f}"
        elif st.session_state.input_type == "完整波長":
            st.session_state.wavelength = f"{wavelength:.2f}"

        st.session_state.wavelength_unit = wavelength_unit_uu

    except ValueError:
        st.session_state.frequency = ""

# 更新波長
def update_wavelength():
    global frequency_unit, wavelength_unit
    try:
        frequency = float(st.session_state.frequency)
        wavelength = calculate_wavelength_from_frequency(
            frequency,
            st.session_state.frequency_unit,
            st.session_state.wavelength_unit
        )

        wavelength, wavelength_unit_uu = auto_adjust_unit(wavelength, st.session_state.wavelength_unit, wavelength_unit)
        if st.session_state.input_type == "半波長":
            wavelength /= 2  # 將半波長轉為完整波長
            st.session_state.wavelength = f"{wavelength:.2f}"
        elif st.session_state.input_type == "1/4 波長":
            wavelength /= 4  # 將 1/4 波長轉為完整波長
            st.session_state.wavelength = f"{wavelength:.2f}"
        elif st.session_state.input_type == "完整波長":
            st.session_state.wavelength = f"{wavelength:.2f}"

        st.session_state.wavelength_unit = wavelength_unit_uu

        frequency, frequency_unit_uu = auto_adjust_unit(frequency, st.session_state.frequency_unit, frequency_unit)
        st.session_state.frequency = f"{frequency:.2f}"
        st.session_state.frequency_unit = frequency_unit_uu

    except ValueError:
        st.session_state.wavelength = ""

# 統一顯示結果
def display_result(value, unit):
    if st.session_state.use_scientific:
        return f"{float(value):.2e} {unit}"
    else:
        return f"{value} {unit}"

def transfer_wavelength_to_tab2():
    try:
        st.session_state.length = st.session_state.wavelength
        st.session_state.input_unit = st.session_state.wavelength_unit
        st.success("波長已成功傳遞到長度換算")
    except KeyError:
        st.error("無法傳遞波長，請檢查輸入值。")

# 長度換算邏輯
def convert_length(length, input_unit, output_unit):
    # 基於米 (m) 為基礎單位的轉換因子
    base_conversion_factors = {
        "m": 1,
        "cm": 1e-2,
        "mm": 1e-3,
        "μm": 1e-6,
        "nm": 1e-9,
        "mil": 0.0000254,
        "inch": 0.0254
    }

    try:
        # 轉換到基礎單位 (m)，再轉換到目標單位
        length_in_meters = length * base_conversion_factors[input_unit]
        converted_length = length_in_meters / base_conversion_factors[output_unit]
        return converted_length
    except KeyError:
        # 如果輸入或輸出單位不存在於定義中
        return None

def swap_units():
    st.session_state.input_unit, st.session_state.output_unit = st.session_state.output_unit, st.session_state.input_unit

# TAB1波長與頻率換算器
def wave_length_freq_cal():
    st.title("波長與頻率換算器")
    st.session_state.use_scientific = st.checkbox("使用科學記號顯示結果", value=st.session_state.use_scientific)

    st.session_state.input_type = st.radio(
        "選擇波長類型",
        ["完整波長", "半波長", "1/4 波長"],
        on_change=update_frequency
    )

    col1, col2, col3 = st.columns([1, 0.3, 1])

    with col1:
        st.text_input("輸入波長 (λ)", key="wavelength", on_change=update_frequency)
        st.text_input("輸入頻率 (f)", key="frequency", on_change=update_wavelength)
        st.selectbox("波長單位", ['mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="wavelength_unit", on_change=update_frequency)
        st.selectbox("頻率單位", ['Hz', 'kHz', 'MHz', 'GHz', 'THz'], key="frequency_unit", on_change=update_wavelength)

    with col3:
        st.text_input("輸入長度值", key="length")
        st.selectbox("選擇輸入單位", ['inch', 'mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="input_unit")
        st.button("互換單位", on_click=swap_units)
        st.selectbox("選擇輸出單位", ['inch', 'mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="output_unit")

    with col1:
        st.button("將波長傳遞到長度換算", on_click=transfer_wavelength_to_tab2)

    if st.session_state.length:
        try:
            h = float(st.session_state.length)
            converted_length = convert_length(h, st.session_state.input_unit, st.session_state.output_unit)
            if converted_length is not None:
                with col3:
                    st.subheader("換算結果")
                    st.write(f"{st.session_state.length} {st.session_state.input_unit} = {converted_length:.2f} {st.session_state.output_unit}")
            else:
                st.error("無法完成換算，請檢查單位設置。")
        except ValueError:
            st.error("請輸入有效的數值！")

    if st.session_state.wavelength or st.session_state.input_type and st.session_state.wavelength:
        try:
            wavelength = float(st.session_state.wavelength)

            if st.session_state.input_type == "半波長":
                st.write(f"1/2 波長：{display_result(st.session_state.wavelength, st.session_state.wavelength_unit)}")
            elif st.session_state.input_type == "1/4 波長":
                st.write(f"1/4 波長：{display_result(st.session_state.wavelength, st.session_state.wavelength_unit)}")
            elif st.session_state.input_type == "完整波長":
                st.write(f"波長：{display_result(st.session_state.wavelength, st.session_state.wavelength_unit)}")

            if st.session_state.input_type == "完整波長":
                st.write(f"1/2 波長：{display_result(wavelength / 2, st.session_state.wavelength_unit)}")
                st.write(f"1/4 波長：{display_result(wavelength / 4, st.session_state.wavelength_unit)}")

        except ValueError:
            st.error("請輸入有效的波長值！")

    if st.session_state.frequency:
        st.write(f"頻率：{display_result(st.session_state.frequency, st.session_state.frequency_unit)}")

def swap_freq():
    if st.session_state.calculated_frequency_tab2:
        st.session_state.frequency_tab2 = st.session_state["calculated_frequency_tab2"]
        st.session_state.frequency_unit_tab2 = st.session_state.calculated_frequency_unit_tab2
        st.session_state.wavelength_tab2 = ""

    if st.session_state.calculated_wave_tab2:
        st.session_state.wavelength_tab2 = st.session_state["calculated_wave_tab2"]
        st.session_state.wavelength_unit_tab2 = st.session_state.calculated_wavelength_unit_tab2
        st.session_state.frequency_tab2 = ""

def length_conversion_tab():
    st.title("波長與頻率單一換算器")

    global frequency_unit, wavelength_unit
    col1, col2 = st.columns(2)

    # 左側輸入波長
    with col1:
        st.text_input(
            "輸入波長 (λ)",
            key="wavelength_tab2",
            on_change=lambda: st.session_state.update({"frequency_tab2": ""})
        )
        st.selectbox(
            "波長單位",
            ['mil', 'nm', 'μm', 'mm', 'cm', 'm'],
            key="wavelength_unit_tab2",
            on_change=lambda: st.session_state.update({"frequency_tab2": ""})
        )

    # 右側輸入頻率
    with col2:
        st.text_input(
            "輸入頻率 (f)",
            key="frequency_tab2",
            on_change=lambda: st.session_state.update({"wavelength_tab2": ""})
        )
        st.selectbox(
            "頻率單位",
            ['Hz', 'kHz', 'MHz', 'GHz', 'THz'],
            key="frequency_unit_tab2",
            on_change=lambda: st.session_state.update({"wavelength_tab2": ""})
        )

    st.button("互換", on_click=swap_freq)

    # 計算波長轉頻率
    if st.session_state.wavelength_tab2:
        try:
            wavelength = float(st.session_state.wavelength_tab2)

            # 計算頻率並調整單位
            frequency = calculate_frequency_from_wavelength(
                wavelength,
                st.session_state.wavelength_unit_tab2,
                st.session_state.frequency_unit_tab2
            )
            frequency, frequency_unit_tab2 = auto_adjust_unit(frequency, st.session_state.frequency_unit_tab2, frequency_unit)

            # 保存計算結果到中間狀態變數
            st.session_state["calculated_frequency_tab2"] = f"{frequency:.2f}"
            st.session_state.calculated_frequency_unit_tab2 = frequency_unit_tab2

            # 重製中間狀態變數
            st.session_state["calculated_wave_tab2"] = ""
            st.session_state.calculated_wavelength_unit_tab2 = ""

            # 顯示結果
            st.write(f"波長：{display_result(wavelength, st.session_state.wavelength_unit_tab2)}")
            st.write(f"1/2 波長：{display_result(wavelength / 2, st.session_state.wavelength_unit_tab2)}")
            st.write(f"1/4 波長：{display_result(wavelength / 4, st.session_state.wavelength_unit_tab2)}")
            st.write(f"頻率：{display_result(frequency, frequency_unit_tab2)}")

        except ValueError:
            st.error("請輸入有效的波長值！")

    # 顯示頻率轉波長
    if st.session_state.frequency_tab2:
        try:
            frequency = float(st.session_state.frequency_tab2)

            # 計算波長並調整單位
            wavelength = calculate_wavelength_from_frequency(
                frequency,
                st.session_state.frequency_unit_tab2,
                st.session_state.wavelength_unit_tab2
            )
            wavelength, wavelength_unit_tab2 = auto_adjust_unit(wavelength, st.session_state.wavelength_unit_tab2, wavelength_unit)

            # 保存計算結果到中間狀態變數
            st.session_state["calculated_wave_tab2"] = f"{wavelength:.2f}"
            st.session_state.calculated_wavelength_unit_tab2 = wavelength_unit_tab2

            # 保存計算結果到中間狀態變數
            st.session_state["calculated_frequency_tab2"] = ""
            st.session_state.calculated_frequency_unit_tab2 = ""

            # 顯示結果
            st.write(f"頻率：{display_result(frequency, st.session_state.frequency_unit_tab2)}")
            st.write(f"波長：{display_result(wavelength, wavelength_unit_tab2)}")
            st.write(f"1/2 波長：{display_result(wavelength / 2, wavelength_unit_tab2)}")
            st.write(f"1/4 波長：{display_result(wavelength / 4, wavelength_unit_tab2)}")
        except ValueError:
            st.error("請輸入有效的頻率值！")

# 主程式
def main():
    initialize_state()

    tab1, tab2 = st.tabs(["波長與頻率換算", "單一變化"])

    with tab1:
        wave_length_freq_cal()

    with tab2:
        length_conversion_tab()

if __name__ == "__main__":
    main()