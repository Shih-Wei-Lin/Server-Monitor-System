import streamlit as st

# 單位轉換字典
UNIT_CONVERSIONS = {
    'wavelength': {
        'mil': 0.0000254,
        'nm': 1e-9,
        'μm': 1e-6,
        'mm': 1e-3,
        'cm': 1e-2,
        'm': 1
    },
    'frequency': {
        'Hz': 1,
        'kHz': 1e3,
        'MHz': 1e6,
        'GHz': 1e9,
        'THz': 1e12
    }
}

# 初始化狀態
def initialize_state():
    default_values = {
        "wavelength": "",
        "frequency": "",
        "wavelength_unit": "mil",
        "frequency_unit": "GHz",  # 預設頻率單位為 GHz
        "use_scientific": False,
        "input_type": "完整波長",
        "length": "",
        "input_unit": "mm",
        "output_unit": "mil",
        "wavelength_tab2": "",
        "frequency_tab2": "",
        "wavelength_unit_tab2": "m",
        "frequency_unit_tab2": "GHz",  # 預設頻率單位為 GHz
        "calculated_wave_tab2": "",
        "calculated_frequency_tab2": "",
        "calculated_frequency_unit_tab2": "",
        "calculated_wavelength_unit_tab2": "",
        "rerun_required": False
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 計算邏輯
def calculate_frequency_from_wavelength(wavelength, wavelength_unit_key, frequency_unit_key):
    c = 299792458  # 光速 (m/s)
    wavelength_m = wavelength * UNIT_CONVERSIONS['wavelength'][wavelength_unit_key]
    frequency_hz = c / wavelength_m
    return frequency_hz / UNIT_CONVERSIONS['frequency'][frequency_unit_key]

def calculate_wavelength_from_frequency(frequency, frequency_unit_key, wavelength_unit_key):
    c = 299792458  # 光速 (m/s)
    frequency_hz = frequency * UNIT_CONVERSIONS['frequency'][frequency_unit_key]
    wavelength_m = c / frequency_hz
    return wavelength_m / UNIT_CONVERSIONS['wavelength'][wavelength_unit_key]

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
    try:
        wavelength = float(st.session_state.wavelength)
        if st.session_state.input_type == "半波長":
            wavelength *= 2
        elif st.session_state.input_type == "1/4 波長":
            wavelength *= 4

        frequency = calculate_frequency_from_wavelength(
            wavelength,
            st.session_state.wavelength_unit,
            st.session_state.frequency_unit
        )
        frequency, frequency_unit = auto_adjust_unit(frequency, st.session_state.frequency_unit, UNIT_CONVERSIONS['frequency'])
        st.session_state.frequency = f"{frequency:.2f}"
        st.session_state.frequency_unit = frequency_unit

        wavelength, wavelength_unit = auto_adjust_unit(wavelength, st.session_state.wavelength_unit, UNIT_CONVERSIONS['wavelength'])
        if st.session_state.input_type == "半波長":
            wavelength /= 2
        elif st.session_state.input_type == "1/4 波長":
            wavelength /= 4
        st.session_state.wavelength = f"{wavelength:.2f}"
        st.session_state.wavelength_unit = wavelength_unit

    except ValueError:
        st.session_state.frequency = ""

# 更新波長
def update_wavelength():
    try:
        frequency = float(st.session_state.frequency)
        wavelength = calculate_wavelength_from_frequency(
            frequency,
            st.session_state.frequency_unit,
            st.session_state.wavelength_unit
        )

        wavelength, wavelength_unit = auto_adjust_unit(wavelength, st.session_state.wavelength_unit, UNIT_CONVERSIONS['wavelength'])
        if st.session_state.input_type == "半波長":
            wavelength /= 2
        elif st.session_state.input_type == "1/4 波長":
            wavelength /= 4
        st.session_state.wavelength = f"{wavelength:.2f}"
        st.session_state.wavelength_unit = wavelength_unit

        frequency, frequency_unit = auto_adjust_unit(frequency, st.session_state.frequency_unit, UNIT_CONVERSIONS['frequency'])
        st.session_state.frequency = f"{frequency:.2f}"
        st.session_state.frequency_unit = frequency_unit

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
        length_in_meters = length * base_conversion_factors[input_unit]
        converted_length = length_in_meters / base_conversion_factors[output_unit]
        return converted_length
    except KeyError:
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

    col1, col2, col3 = st.columns(3)

    with col1:
        col1_1, col1_2 = st.columns([3, 1])
        with col1_1:
            st.text_input("輸入波長 (λ)", key="wavelength", on_change=update_frequency)
        with col1_2:
            st.selectbox("波長單位", ['mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="wavelength_unit", on_change=update_frequency)

        col1_3, col1_4 = st.columns([3, 1])
        with col1_3:
            st.text_input("輸入頻率 (f)", key="frequency", on_change=update_wavelength)
        with col1_4:
            st.selectbox("頻率單位", ['Hz', 'kHz', 'MHz', 'GHz', 'THz'], key="frequency_unit", on_change=update_wavelength)

        st.button("將波長傳遞到長度換算", on_click=transfer_wavelength_to_tab2)

    with col3:
        col3_1, col3_2 = st.columns([3, 1])
        with col3_1:
            st.text_input("輸入長度值", key="length")
        with col3_2:
            st.selectbox("選擇輸入單位", ['inch', 'mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="input_unit")

        st.button("互換單位", on_click=swap_units)

        col3_3, col3_4 = st.columns([3, 1])
        with col3_4:
            st.selectbox("選擇輸出單位", ['inch', 'mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="output_unit")

        if st.session_state.length:
            try:
                length = float(st.session_state.length)
                converted_length = convert_length(length, st.session_state.input_unit, st.session_state.output_unit)
                if converted_length is not None:
                    st.subheader("換算結果")
                    st.write(f"{st.session_state.length} {st.session_state.input_unit} = {converted_length:.2f} {st.session_state.output_unit}")
                else:
                    st.error("無法完成換算，請檢查單位設置。")
            except ValueError:
                st.error("請輸入有效的數值！")

    if st.session_state.wavelength or st.session_state.input_type:
        try:
            wavelength = float(st.session_state.wavelength)
            if st.session_state.input_type == "完整波長":
                st.write(f"波長：{display_result(st.session_state.wavelength, st.session_state.wavelength_unit)}")
                st.write(f"1/2 波長：{display_result(wavelength / 2, st.session_state.wavelength_unit)}")
                st.write(f"1/4 波長：{display_result(wavelength / 4, st.session_state.wavelength_unit)}")
            elif st.session_state.input_type == "半波長":
                st.write(f"1/2 波長：{display_result(wavelength / 2, st.session_state.wavelength_unit)}")
            elif st.session_state.input_type == "1/4 波長":
                st.write(f"1/4 波長：{display_result(wavelength / 4, st.session_state.wavelength_unit)}")
        except ValueError:
            pass

    if st.session_state.frequency:
        st.write(f"頻率：{display_result(st.session_state.frequency, st.session_state.frequency_unit)}")

def swap_freq():
    if st.session_state.calculated_frequency_tab2:
        st.session_state.frequency_tab2 = st.session_state.calculated_frequency_tab2
        st.session_state.frequency_unit_tab2 = st.session_state.calculated_frequency_unit_tab2
        st.session_state.wavelength_tab2 = ""

    if st.session_state.calculated_wave_tab2:
        st.session_state.wavelength_tab2 = st.session_state.calculated_wave_tab2
        st.session_state.wavelength_unit_tab2 = st.session_state.calculated_wavelength_unit_tab2
        st.session_state.frequency_tab2 = ""

def length_conversion_tab():
    st.title("波長與頻率單一換算器")

    col1, col2 = st.columns(2)

    with col1:
        st.text_input("輸入波長 (λ)", key="wavelength_tab2", on_change=lambda: st.session_state.update({"frequency_tab2": ""}))
        st.selectbox("波長單位", ['mil', 'nm', 'μm', 'mm', 'cm', 'm'], key="wavelength_unit_tab2", on_change=lambda: st.session_state.update({"frequency_tab2": ""}))

    with col2:
        st.text_input("輸入頻率 (f)", key="frequency_tab2", on_change=lambda: st.session_state.update({"wavelength_tab2": ""}))
        st.selectbox("頻率單位", ['Hz', 'kHz', 'MHz', 'GHz', 'THz'], key="frequency_unit_tab2", on_change=lambda: st.session_state.update({"wavelength_tab2": ""}))

    st.button("互換", on_click=swap_freq)

    if st.session_state.wavelength_tab2:
        try:
            wavelength = float(st.session_state.wavelength_tab2)
            frequency = calculate_frequency_from_wavelength(
                wavelength,
                st.session_state.wavelength_unit_tab2,
                st.session_state.frequency_unit_tab2
            )
            frequency, frequency_unit = auto_adjust_unit(frequency, st.session_state.frequency_unit_tab2, UNIT_CONVERSIONS['frequency'])

            st.session_state["calculated_frequency_tab2"] = f"{frequency:.2f}"
            st.session_state.calculated_frequency_unit_tab2 = frequency_unit
            st.session_state["calculated_wave_tab2"] = ""
            st.session_state.calculated_wavelength_unit_tab2 = ""

            st.write(f"波長：{display_result(wavelength, st.session_state.wavelength_unit_tab2)}")
            st.write(f"1/2 波長：{display_result(wavelength / 2, st.session_state.wavelength_unit_tab2)}")
            st.write(f"1/4 波長：{display_result(wavelength / 4, st.session_state.wavelength_unit_tab2)}")
            st.write(f"頻率：{display_result(frequency, frequency_unit)}")
        except ValueError:
            st.error("請輸入有效的波長值！")

    if st.session_state.frequency_tab2:
        try:
            frequency = float(st.session_state.frequency_tab2)
            wavelength = calculate_wavelength_from_frequency(
                frequency,
                st.session_state.frequency_unit_tab2,
                st.session_state.wavelength_unit_tab2
            )
            wavelength, wavelength_unit = auto_adjust_unit(wavelength, st.session_state.wavelength_unit_tab2, UNIT_CONVERSIONS['wavelength'])

            st.session_state["calculated_wave_tab2"] = f"{wavelength:.2f}"
            st.session_state.calculated_wavelength_unit_tab2 = wavelength_unit
            st.session_state["calculated_frequency_tab2"] = ""
            st.session_state.calculated_frequency_unit_tab2 = ""

            st.write(f"頻率：{display_result(frequency, st.session_state.frequency_unit_tab2)}")
            st.write(f"波長：{display_result(wavelength, wavelength_unit)}")
            st.write(f"1/2 波長：{display_result(wavelength / 2, wavelength_unit)}")
            st.write(f"1/4 波長：{display_result(wavelength / 4, wavelength_unit)}")
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