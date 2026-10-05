"""Streamlit entry point; launch with ``streamlit run main.py``."""

# %%
import casadi as ca
import numpy as np

# import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

from tqdm import tqdm
from scipy.interpolate import interp1d

import calc as daf
import plots as dpf

import time
import os

import streamlit as st

# %%
# User inputs

st.set_page_config(page_title="AC battery evaluator", layout="wide")
title_column, logo_column = st.columns([5, 1])
with title_column:
    st.title("AC battery evaluator")
with logo_column:
    logo_files = sorted((Path(__file__).parent.parent / "logo").glob("*_white.png"))
    if logo_files:
        st.image(logo_files[0], width="content")

tab1, tab2, tab3 = st.tabs(["Parameters", "MTPA maps", "Loss and Efficiency maps"])

# Create a path object for the results directory and create it if it doesn't exist
RESULTS_DIR = Path("results_mtpa_soc")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

with st.sidebar:

    # --------------------------------------------------------------------------------
    # get the user inputs for the SOC value for the MTPA and Efficiency maps
    soc = st.selectbox(
        "Select the SOC value for the MTPA and Efficiency maps",
        options=[
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
        ],
        index=4,
    )
    # ********************************************************************************
    st.divider()

    # --------------------------------------------------------------------------------
    # get the user inputs for the PMSM parameters
    st.header("PMSM parameters")
    pp = st.number_input("Pole pairs [-]", min_value=1, value=4, step=1)
    PBase = st.number_input("Base mechanical power [W]", min_value=0.0, value=400e3)
    wmBase = st.number_input("Base mechanical speed [rpm]", min_value=1.0, value=3000.0)
    Vdc = st.number_input("DC-link voltage [V]", min_value=0.0, value=700.0)
    VBase = Vdc / 2  # base phase voltage [V]
    VMax = VBase * 2 / ca.sqrt(3)  # maximum phase voltage [V]
    rs_pu = st.number_input("Stator phase resistance [pu]", min_value=0.0, value=0.01)
    ld_pu = st.number_input("d-axis inductance [pu]", min_value=0.0, value=0.55)
    lq_pu = st.number_input("q-axis inductance [pu]", min_value=0.0, value=0.85)

    # deriving the other parameters for the PMSM model based on the user inputs
    TBase = PBase / (wmBase * 2 * ca.pi / 60)  # base torque [N.m]
    psi_f = VBase / (wmBase * pp * 2 * ca.pi / 60)  # permanent magnet flux linkage [Wb]
    ZBase = (VBase / ca.sqrt(2) * ca.sqrt(3)) ** 2 / PBase  # base impedance [Ohm]
    Ibase = 2 * PBase / (3 * VBase)  # base current [A] (limited by the converter)
    # NOTE: the base current is rounded-up to the nearest 50s A.
    Ibase = np.ceil(Ibase / 50) * 50
    Rs = rs_pu * ZBase  # stator phase resistance [Ohm]
    Ld = ld_pu * ZBase / (wmBase * pp * 2 * ca.pi / 60)  # d-axis inductance [H]
    Lq = lq_pu * ZBase / (wmBase * pp * 2 * ca.pi / 60)  # q-axis inductance [H]
    wmMax = (
        VMax / (psi_f - Ld * Ibase) / pp * 60 / (2 * ca.pi)
    )  # maximum mechanical speed [rpm]
    xi = (Ld - Lq) * Ibase / psi_f  # saliency ratio [-] (id / iq \approx xi)
    # ********************************************************************************
    st.divider()

    # --------------------------------------------------------------------------------
    # User inputs for the MOSFET inverter parameters
    st.header("MOSFET inverter parameters")
    which_mosfet = st.selectbox(
        "Select the MOSFET device for the inverter",
        options=[
            "Wolfspeed EDB005M12TM4",
            "Costumized MOSFET",
        ],
    )
    fsw = st.number_input("Switching frequency [Hz]", min_value=1.0, value=10e3)

    if which_mosfet == "Wolfspeed EDB005M12TM4":
        # https://assets.wolfspeed.com/uploads/2025/10/Wolfspeed_EDB005M12TM4_EDB005M12TM4L_data_sheet.pdf
        Rdson_2l = 4.6e-3  # inverter Rdson (taken from datasheet) [Ohm]
        ImosRated = 320 * np.sqrt(
            2
        )  # 320 A is MOSFET continuous RMS current rating (taken from datasheet at 175°C) [A]
        # tr = 50e-9 * 2  # rise time current + fall time voltage (taken from datasheet) [s]
        # tf = 45e-9 * 2  # fall time current + rise time voltage (taken from datasheet) [s]
        rawdata_df = pd.read_csv(
            os.path.join("data", "Wolfspeed_MOSFET_dvdt_didt_data.csv")
        )

        # Link: https://www.guchen-eac.com/who/news/the-thermal-management-system-of-xpeng-x7.html
        # From the link, the case temperature is kept at around. 95°C, but the maximum allowable junction temprater is determined from the datasheet.
        Tjmax_2l = 175  # (from the datasheet) [°C]
        Tcmax_2l = 100  # (from the link) [°C]
        Rth_jc_2l = 0.08  # (from the datasheet) [°C/W]

        Rdson_vs_Tj_rawdata = pd.read_csv(
            os.path.join("data", "Wolfspeed_MOSFET_Rdson_vs_Tj_data.csv")
        )

    elif which_mosfet == "Costumized MOSFET":
        Rdson_2l = st.number_input("Rdson [Ohm]", min_value=0.0, value=4.6e-3)

        ImosRated_RMS = st.number_input(
            "MOSFET continuous RMS current rating [A]", min_value=0.0, value=400.0
        )
        ImosRated = ImosRated_RMS * np.sqrt(2)
        didt_on_val = st.number_input(
            "di/dt (on) [A/ns]", min_value=0.0, value=8.0, step=0.1
        )  # [A/ns] (assumed)
        didt_off_val = st.number_input(
            "di/dt (off) [A/ns]", min_value=0.0, value=15.0, step=0.1
        )  # [A/ns] (assumed)
        dvdt_on_val = st.number_input(
            "dv/dt (on) [V/ns]", min_value=0.0, value=25.0, step=0.1
        )  # [V/ns] (assumed)
        dvdt_off_val = st.number_input(
            "dv/dt (off) [V/ns]", min_value=0.0, value=25.0, step=0.1
        )  # [V/ns] (assumed)
        rawdata_df = pd.DataFrame(
            {
                "didt_on_X": [0, ImosRated],
                "didt_on_Y": [didt_on_val, didt_on_val],
                "didt_off_X": [0, ImosRated],
                "didt_off_Y": [didt_off_val, didt_off_val],
                "dvdt_on_X": [0, ImosRated],
                "dvdt_on_Y": [dvdt_on_val, dvdt_on_val],
                "dvdt_off_X": [0, ImosRated],
                "dvdt_off_Y": [dvdt_off_val, dvdt_off_val],
            }
        )
        Tjmax_2l = st.number_input(
            "Maximum junction temperature [°C]", min_value=0.0, value=175.0
        )
        Tcmax_2l = st.number_input(
            "Maximum case temperature [°C]", min_value=0.0, value=100.0
        )
        Rth_jc_2l = st.number_input(
            "Thermal resistance junction-to-case [°C/W]", min_value=0.0, value=0.08
        )
        Rdson_vs_Tj_rawdata = pd.DataFrame(
            {
                "Tj": [0, 25, 175],
                "Rdson_normalized": [1, 1, 2],
            }
        )

    else:
        raise ValueError("Selected MOSFET device is not supported.")

    # Ambient to case temperature
    # In liquid-cooled traction inverters, which is very commong rtoday, the combined case-to-ambient thermal resistance (Rth_CA = Rth_CS + Rth_SA) is typically in the range of 0.05-0.10 K/W per module or inverter leg. Advanced packaging techniques, including double-sided cooling and silver-sintered die attachment, can reduce thermal resistance by up to 50% compared with conventional single-sided cooled designs.
    # References:
    # 1. https://scholarworks.uark.edu/etd/6014/
    # 2. https://www.mdpi.com/1996-1073/18/22/6020
    # 3. https://www.automotive-iq.com/thermal-management/articles/800v-sic-thermal-management-explained-why-the-whole-cooling-system-has-to-change
    Rth_ca_2l = st.number_input(
        "Thermal resistance case-to-ambient [°C/W]", min_value=0.0, value=0.05
    )
    # include the ambient temperature in the thermal model of the inverter
    Tambient = st.number_input(
        "Ambient temperature [°C]", min_value=0.0, value=25.0
    )  # ambient temperature [°C]

    didt_on_fun = interp1d(
        rawdata_df["didt_on_X"],
        rawdata_df["didt_on_Y"],
        kind="linear",
        bounds_error=False,
        fill_value=(
            rawdata_df["didt_on_Y"].iloc[0],
            rawdata_df["didt_on_Y"].iloc[-1],
        ),
    )
    didt_off_fun = interp1d(
        rawdata_df["didt_off_X"],
        rawdata_df["didt_off_Y"],
        kind="linear",
        bounds_error=False,
        fill_value=(
            rawdata_df["didt_off_Y"].iloc[0],
            rawdata_df["didt_off_Y"].iloc[-1],
        ),
    )
    dvdt_on_fun = interp1d(
        rawdata_df["dvdt_on_X"],
        rawdata_df["dvdt_on_Y"],
        kind="linear",
        bounds_error=False,
        fill_value=(
            rawdata_df["dvdt_on_Y"].iloc[0],
            rawdata_df["dvdt_on_Y"].iloc[-1],
        ),
    )
    dvdt_off_fun = interp1d(
        rawdata_df["dvdt_off_X"],
        rawdata_df["dvdt_off_Y"],
        kind="linear",
        bounds_error=False,
        fill_value=(
            rawdata_df["dvdt_off_Y"].iloc[0],
            rawdata_df["dvdt_off_Y"].iloc[-1],
        ),
    )
    Npmos_2l = np.ceil(Ibase / ImosRated)  # number of parallel MOSFETs [-]
    Rdson_Tj_fun = interp1d(
        Rdson_vs_Tj_rawdata["Tj"],
        Rdson_vs_Tj_rawdata["Rdson_normalized"],
        kind="linear",
        bounds_error=False,
        fill_value=(
            Rdson_vs_Tj_rawdata["Rdson_normalized"].iloc[0],
            Rdson_vs_Tj_rawdata["Rdson_normalized"].iloc[-1],
        ),
    )
    # NOTE: based on fig 24 in the datasheet, the rise/fall time accounts for about 50% of the switching energy, so a multiple by 2 is introduced to account for the total switching energy.
    # TODO: Esw(id, iq, Vd, Vq) \propto di/dt(id, iq, Vd, Vq) and dv/dt(id, iq, Vd, Vq),

    switching_slopes_fig = dpf.plot_switching_slopes(
        rawdata_df,
        didt_on_fun,
        didt_off_fun,
        dvdt_on_fun,
        dvdt_off_fun,
        save_path=RESULTS_DIR / "switching_slopes.png",
    )
    # ********************************************************************************
    Rdson_vs_Tj_fig = dpf.plot_Rdson_vs_Tj(
        Rdson_vs_Tj_rawdata,
        Rdson_Tj_fun,
        save_path=RESULTS_DIR / "Rdson_vs_Tj.png",
    )
    st.divider()

    # --------------------------------------------------------------------------------
    # User inputs for the battery parameters
    st.header("Battery parameters")
    ocv_dict = {
        "soc": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
        "NMC": [4.13, 4.03, 3.92, 3.83, 3.75, 3.70, 3.66, 3.63, 3.59, 3.53, 3.34],
        "LFP": [3.39, 3.33, 3.31, 3.32, 3.31, 3.29, 3.27, 3.26, 3.25, 3.18, 2.89],
        "LTO": [2.69, 2.42, 2.35, 2.32, 2.28, 2.23, 2.20, 2.19, 2.18, 2.15, 2.11],
        "NaB": [3.9, 3.74, 3.61, 3.47, 3.29, 3.12, 2.99, 2.87, 2.75, 2.55, 2.22],
    }

    Select_battery_chem = st.selectbox(
        "Select the battery chemistry",
        options=list(ocv_dict.keys())[1:],
    )
    # nominal voltage [V]
    Vnom = ocv_dict[Select_battery_chem][ocv_dict.get("soc").index(0.5)]

    Ebatt = st.number_input(
        "Battery energy [kWh]", min_value=0.0, value=400.0
    )  # battery energy [kWh]
    Ebatt *= 1e3  # convert to Wh

    select_cell = st.selectbox(
        "Select the cell",
        options=[
            "Samsung PHEV2 24Ah",
            "Custom cell",
        ],
    )

    if select_cell == "Samsung PHEV2 24Ah":

        Qcell = 24  # cell capacity [Ah]

        # battery internal resistance [Ohm] (based on some empirical data)
        R0_nom = 1.2e-3  # [Ohm]
        R1_nom = 0.7e-3  # [Ohm]
        C1_nom = 1 / (2 * np.pi * 250 * R1_nom)  # [F]

    elif select_cell == "Custom cell":

        Qcell = st.number_input("Cell capacity [Ah]", min_value=0.0, value=24.0)

        R0_nom = st.number_input(
            "Cell internal resistance R0 [mOhm]", min_value=0.0, value=1.2
        )
        R0_nom *= 1e-3  # convert to Ohm
        R1_nom = st.number_input(
            "Cell internal resistance R1 [mOhm]", min_value=0.0, value=0.7
        )
        R1_nom *= 1e-3  # convert to Ohm
        C1_nom = st.number_input(
            "Cell RC branch capacitance C1 [F]",
            min_value=0.0,
            value=1 / (2 * np.pi * 250 * R1_nom),
        )

    # polynomial functions for the battery internal resistances and capacitance as a function of SoC
    ar, br, cr = 1.3, -1.3, 1.3  # coefficients for the polynomial functions
    R0_fn = lambda soc: R0_nom * (
        ar * soc**2 + br * soc + cr
    )  # battery internal resistance [Ohm] as a function of SoC
    R1_fn = lambda soc: R1_nom * (
        ar * soc**2 + br * soc + cr
    )  # battery RC branch resistance [Ohm] as a function of SoC
    ac, bc, cc = -1.3, 1.3, 1.3  # coefficients for the polynomial functions
    C1_fn = lambda soc: C1_nom * (
        ac * soc**2 + bc * soc + cc
    )  # battery RC branch capacitance [F] as a function of SoC
    fig_battery_parameters = dpf.plot_battery_parameters(
        R0_fn, R1_fn, C1_fn, save_path=RESULTS_DIR / "battery_parameters.png"
    )
    fig_battery_ocv = dpf.plot_cell_ocv_vs_soc(
        ocv_dict, Select_battery_chem, save_path=RESULTS_DIR / "battery_ocv.png"
    )

    # battery parameters for the equivalent battery pack
    Nscells_2l = np.ceil(2 * VBase / Vnom).astype(int)  # number of series cells [-]
    Npcells_2l = np.ceil(Ebatt / (Qcell * (Vnom * Nscells_2l))).astype(
        int
    )  # number of parallel cells [-]

    # ********************************************************************************
    st.divider()

    # --------------------------------------------------------------------------------
    # User inputs for the BI-MMC parameters
    st.header("AC-battery parameters")
    Nsm = st.number_input(
        "Number of submodules per phase", min_value=1, value=12, step=1
    )  # number of submodules per phase [-]
    Nsm_redundant_pu = st.number_input(
        "Number of redundant submodules per phase [pu]",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )  # number of redundant submodules per phase [pu]
    Rdson_bimmc = st.number_input(
        "Rdson [mOhm]", min_value=0.0, value=0.3, step=0.1
    )  # [Ohm] (example taken from IQDH29NE2LM5CGSC from Infineon)
    Rdson_bimmc *= 1e-3  # convert to Ohm
    Imax_mosfet = st.number_input(
        "MOSFET continuous RMS current rating [A]", min_value=1.0, value=400.0
    )  # [A] (example taken from IQDH29NE2LM5CGSC from Infineon)
    Npmos_bimmc = np.max(
        [np.ceil(Ibase / Imax_mosfet).astype(int), 4]
    )  # number of parallel MOSFETs [-]
    # NOTE: For now the switching slopes are assumed to be constant for the BI-MMC, but they can be updated based on the actual device datasheet or experimental data.
    didt_on_bimmc = st.number_input(
        "didt (on) [A/ns]", min_value=0.0, value=1.0, step=0.1
    )  # [A/ns] (assumed)
    didt_off_bimmc = st.number_input(
        "didt (off) [A/ns]", min_value=0.0, value=1.0, step=0.1
    )  # [A/ns] (assumed)
    dvdt_on_bimmc = st.number_input(
        "dvdt (on) [V/ns]", min_value=0.0, value=0.5, step=0.1
    )  # [V/ns] (assumed)
    dvdt_off_bimmc = st.number_input(
        "dvdt (off) [V/ns]", min_value=0.0, value=0.5, step=0.1
    )  # [V/ns] (assumed)
    mf_bimmc = st.number_input(
        "Pulse number (switching frequency multiplier) [-]",
        min_value=1,
        value=2,
        step=1,
    )  # pulse number (switching frequency multiplier) [-] (assumed)
    Rth_jc_bimmc = st.number_input(
        "Thermal resistance junction-to-case [°C/W]", min_value=0.0, value=0.5
    )  # [°C/W] (example taken from IQDH29NE2LM5CGSC from Infineon)
    # This will be the cooling system thermal resistance from the case to the ambient.
    # Advanced packaging techniques, including double-sided cooling and silver-sintered die attachment, can reduce thermal resistance by up to 50% compared with conventional single-sided cooled designs.
    Rth_ca_bimmc = st.number_input(
        "Thermal resistance case-to-ambient [°C/W]", min_value=0.0, value=0.2
    )  # [°C/W] (assumed)

    Nscells_bimmc = np.ceil(2 * VBase / np.sqrt(3) / (Vnom * Nsm)).astype(int)
    Vmax_bimmc = Vnom * Nsm * Nscells_bimmc
    Npcells_bimmc = np.ceil(Ebatt / (3 * Nsm * Vnom * Nscells_bimmc * Qcell)).astype(
        int
    )

    Vcell = ocv_dict[Select_battery_chem][
        ocv_dict.get("soc").index(soc)
    ]  # cell voltage at the selected SOC [V]
    Vs_bimmc = Vcell * Nscells_bimmc  # AC battery phase voltage [V]

# ------------------------------------------------------------------------------
# # -- Save the user inputs to a markdown file for reference and reproducibility
# results_dir = os.path.join(os.getcwd(), "dashboard_results")
# os.makedirs(results_dir, exist_ok=True)
# results_md_path = os.path.join(results_dir, "dashboard_parameters.md")

# results_md_lines = []
# results_md_lines.append("# Dashboard Parameters\n")
# results_md_lines.append("## PMSM parameters\n")
# results_md_lines.append(f"- pp = {pp}")
# results_md_lines.append(f"- PBase = {PBase / 1e3:.0f} kW")
# results_md_lines.append(f"- wmBase = {wmBase:.0f} rpm")
# results_md_lines.append(f"- TBase = {TBase:.0f} N.m")
# results_md_lines.append(f"- VBase = {VBase:.0f} V")
# results_md_lines.append(f"- VMax = {VMax:.0f} V")
# results_md_lines.append(f"- psi_f = {psi_f * 1e3:.2f} mWb")
# results_md_lines.append(f"- ZBase = {ZBase * 1e3:.2f} mOhm")
# results_md_lines.append(f"- Ibase = {Ibase:.2f} A")
# results_md_lines.append(f"- Rs = {Rs * 1e3:.2f} mOhm")
# results_md_lines.append(f"- Ld = {Ld * 1e6:.2f} uH")
# results_md_lines.append(f"- Lq = {Lq * 1e6:.2f} uH")
# results_md_lines.append(f"- wmMax = {wmMax:.1f} rpm")
# results_md_lines.append(f"- xi = {xi:.4f}")
# results_md_lines.append("\n## Inverter parameters\n")
# results_md_lines.append(f"- Rdson = {Rdson * 1e3:.2f} mOhm")
# results_md_lines.append(f"- Npmos = {Npmos:.0f}")
# results_md_lines.append(f"- fsw = {fsw / 1e3:.0f} kHz")
# results_md_lines.append(f"- f1 = {(wmBase * pp) / 60:.2f} Hz")
# results_md_lines.append("\n## Battery parameters\n")
# results_md_lines.append(f"- Battery energy: {Ebatt / 1e3:.0f} kWh")
# results_md_lines.append(f"- Selected battery chemistry: {Select_battery_chem}")
# results_md_lines.append(f"- Cell capacity: {Qcell:.0f} Ah")
# # results_md_lines.append(f"- Cell internal resistance: {Rcell * 1e3:.2f} mOhm")
# results_md_lines.append(f"- Number of series (equivalent) cells: {Nscells}")
# results_md_lines.append(f"- Number of parallel (equivalent) cells: {Npcells}")
# results_md_lines.append("\n## BI-MMC parameters\n")
# results_md_lines.append(f"- Number of submodules per phase: {Nsm}")
# results_md_lines.append(f"- BI-MMC Rdson: {Rdson_bimmc * 1e3:.2f} mOhm")
# results_md_lines.append(f"- Number of parallel MOSFETs: {Npmos_bimmc}")
# results_md_lines.append(f"- BI-MMC Vmax: {Vmax_bimmc:.2f} V")

# # save the parameters to a markdown file
# with open(results_md_path, "w") as f:
#     f.write("\n".join(results_md_lines) + "\n")
# *******************************************************************************

with tab1:
    st.header("User inputs")
    st.write(
        "Below are the user inputs and the derived parameters for the PMSM, inverter, battery, and AC Battery."
    )
    st.subheader("PMSM parameters")
    st.write(
        f"- Pole pairs: `{pp}`\n- Base mechanical power: `{PBase / 1e3:.0f} kW`\n- Base mechanical speed: `{wmBase:.0f} rpm`\n- Base torque: `{TBase:.0f} N.m`\n- Base phase voltage (peak): `{VBase:.0f} V`\n- Maximum phase voltage (peak): `{VMax:.0f} V`\n- Permanent magnet flux linkage: `{psi_f * 1e3:.2f} mWb`\n- Base impedance: `{ZBase * 1e3:.2f} mOhm`\n- Base current: `{Ibase:.2f} A`\n- Stator phase resistance: `{Rs * 1e3:.2f} mOhm`\n- d-axis inductance: `{Ld * 1e6:.2f} uH`\n- q-axis inductance: `{Lq * 1e6:.2f} uH`\n- Maximum mechanical speed: `{wmMax:.1f} rpm`\n- Saliency ratio: `{xi:.4f}`"
    )
    st.subheader("Inverter parameters")
    st.write(
        f"- Rdson: `{Rdson_2l * 1e3:.2f} mOhm`\n- Number of parallel MOSFETs: `{Npmos_2l:.0f}`\n- Switching frequency: `{fsw / 1e3:.0f} kHz`\n- Fundamental frequency: `{(wmBase * pp) / 60:.2f} Hz`\n- Thermal resistance junction-to-case: `{Rth_jc_2l:.3f} °C/W`\n- Thermal resistance case-to-ambient: `{Rth_ca_2l:.3f} °C/W`\n- Maximum junction temperature: `{Tjmax_2l:.1f} °C`\n- Maximum case temperature: `{Tcmax_2l:.1f} °C`\n- Ambient temperature: `{Tambient:.1f} °C`"
    )
    st.subheader("Battery parameters")
    st.write(
        f"- Battery energy: `{Ebatt / 1e3:.0f} kWh`\n- Selected battery chemistry: `{Select_battery_chem}`\n- Cell capacity: `{Qcell:.0f} Ah`\n- Number of series (equivalent) cells: `{Nscells_2l}`\n- Number of parallel (equivalent) cells: `{Npcells_2l}`"
    )
    st.subheader("BI-MMC parameters")
    st.write(
        f"- Number of submodules per phase: `{Nsm}`\n- Number of redundant submodules per phase: `{Nsm_redundant_pu * 100}%`\n- BI-MMC Rdson: `{Rdson_bimmc * 1e3:.2f} mOhm`\n- Number of parallel MOSFETs: `{Npmos_bimmc}`\n- BI-MMC Vmax: `{Vmax_bimmc:.2f} V`\n Number of series cells per SM: `{Nscells_bimmc}`\n- SM battery voltage: `{Vs_bimmc:.2f} V`"
    )

    # -------------------------------------------------------------------------------
    MOSFET_plot, Battery_plots = st.columns(
        2
    )  # create a two-column layout for the plots
    # MOSFET plots
    if "switching_slopes_fig" in locals():
        with MOSFET_plot:
            st.subheader("MOSFET switching slopes")
            st.pyplot(switching_slopes_fig, width="stretch")
            st.subheader("MOSFET Rdson vs Tj")
            st.pyplot(Rdson_vs_Tj_fig, width="stretch")
    # Cell plots
    if "fig_battery_parameters" in locals():
        with Battery_plots:
            st.subheader("Cell OCV curve")
            st.pyplot(fig_battery_ocv, width="stretch")
            st.subheader("Cell RC parameters")
            st.pyplot(fig_battery_parameters, width="stretch")

# -------------------------------------------------------------------------------
# Analysis
motor = daf.MotorParameters(Rs, Ld, Lq, psi_f, pp)
opti, x, (Tau_ref, wm_ref, vmax) = daf.create_mtpa_optimization_problem(
    motor
)  # Create an optimization problem for MTPA
# print(f"Selected SOC values for the analysis: {soc_vec}") # used only to debug to check the selected SOC values

# Create a vector of reference torque values
Tau_ref_vec = np.linspace(
    -TBase, TBase, 100
)  # Create a vector of reference torque values
wm_ref_vec = np.linspace(0, wmMax, 50)  # Create a vector of reference speed values

# INITIALIZE ARRAYS TO STORE RESULTS
Id_vec = np.zeros((len(wm_ref_vec), len(Tau_ref_vec)))
Iq_vec = np.zeros((len(wm_ref_vec), len(Tau_ref_vec)))
tcom_ns = []  # Initialize a list to store computation times in nanoseconds

# -- MTPA optimization loop
V_max = ocv_dict[Select_battery_chem][ocv_dict.get("soc").index(soc)] * Nscells_2l / 2
opti.set_value(
    vmax, V_max * 2 / np.sqrt(3)
)  # set the maximum voltage for the optimization problem

# # mtpa_status = st.status("Running MTPA analysis...", expanded=False)

with tab2:
    mtpa_progress = st.progress(0, text="MTPA analysis: 0%")

for ii, wm in tqdm(enumerate(wm_ref_vec), desc="wm", total=len(wm_ref_vec), unit="wm"):
    mtpa_progress.progress(
        (ii + 1) / len(wm_ref_vec),
        text=f"MTPA analysis: {ii + 1}/{len(wm_ref_vec)} speed points",
    )
    for jj, Tau in enumerate(Tau_ref_vec):

        # ignore infeasible solutions (i.e., when the requested torque is too high for the given speed)
        if Tau * wm * 2 * ca.pi / 60 > PBase or Tau * wm * 2 * ca.pi / 60 < -PBase:
            Id_vec[ii, jj] = np.nan
            Iq_vec[ii, jj] = np.nan

            continue

        # update the optimization problem parameters
        opti.set_value(Tau_ref, Tau)
        opti.set_value(wm_ref, wm * 2 * ca.pi / 60)

        # solve the optimization problem and record the computation time
        t0 = time.time()
        sol = opti.solve()
        tcom_ns.append((time.time() - t0) * 1e9)

        Id_vec[ii, jj] = sol.value(x[0])
        Iq_vec[ii, jj] = sol.value(x[1])

        # reset the initial guess for the next iteration to the current solution
        opti.set_initial(x, sol.value(x))

        # calculate the d-axis and q-axis voltages for the current solution (for inverter calculations)
        wr = wm * 2 * np.pi / 60 * pp  # electrical speed [rad/s]
        Vd_ = Id_vec[ii, jj] * Rs - wr * Lq * Iq_vec[ii, jj]
        Vq_ = Iq_vec[ii, jj] * Rs + wr * (psi_f + Ld * Id_vec[ii, jj])

    # # mtpa_status.update(label="MTPA analysis complete", state="complete")

# *******************************************************************************

# -------------------------------------------------------------------------------
# preparing the results for plotting

# ignoring the values that exceed the base current (i.e., the maximum current that can be delivered by the inverter)
Id = Id_vec.copy()
Iq = Iq_vec.copy()
over_current_mask = Id_vec**2 + Iq_vec**2 > Ibase**2
Id[over_current_mask] = np.nan
Iq[over_current_mask] = np.nan

# Creating the voltage reference vector
wr = wm_ref_vec[:, None] * pp * 2 * np.pi / 60
Vd = Id_vec * Rs - wr * Lq * Iq
Vq = Iq * Rs + wr * (psi_f + Ld * Id)
# *******************************************************************************

# -------------------------------------------------------------------------------
# Plotting the results

with tab2:
    st.header("MTPA analysis results")
    st.write(
        f"Computation time for the MTPA optimization problem: {np.mean(tcom_ns) * 1e-6:.2f} ms (mean) and {np.std(tcom_ns) * 1e-6:.2f} ms (std) over {len(tcom_ns)} iterations."
    )
    st.write(
        "Below are the results of the MTPA analysis for the selected SOC value. The plots show the d-axis and q-axis currents, as well as the d-axis and q-axis voltages, as functions of the reference torque and speed."
    )

    V_dc = (
        ocv_dict[Select_battery_chem][ocv_dict.get("soc").index(soc)] * Nscells_2l / 2
    )
    soc_tag = f"soc_{int(round(soc * 100)):02d}"
    operating_map = dpf.OperatingMap(wm_ref_vec, Tau_ref_vec, PBase, TBase)
    mtpa_map_data = dpf.MtpaMapData(Id, Iq, Vd, Vq, operating_map, V_dc, Ibase, soc)
    col1, col2 = st.columns(2)
    with col1:
        fig = dpf.plot_mtpa_maps(
            mtpa_map_data,
            dpf.PlotOptions(
                figure_number=10,
                save_path=RESULTS_DIR / f"mtpa_maps_{soc_tag}.png",
            ),
        )
        # fig.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig.savefig(RESULTS_DIR / f"mtpa_maps_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")
    with col2:
        fig2 = dpf.plot_mtpa_maps_dqs(
            mtpa_map_data,
            dpf.PlotOptions(
                figure_number=11,
                save_path=RESULTS_DIR / f"mtpa_maps_dqs_{soc_tag}.png",
            ),
        )
        # fig2.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig2.savefig(RESULTS_DIR / f"mtpa_maps_dqs_{soc_tag}.png", dpi=200)
        st.pyplot(fig2, width="stretch")
    # *******************************************************************************

# %%
# Analysis of the two-level inverter
# -------------------------------------------------------------------------------
(
    Power_loss_inverter_conduction_2l,
    Power_loss_inverter_switching_2l,
    Power_loss_battery_2l,
    Temp_case_2l,
    Temp_junction_2l,
) = daf.calc_losses_2l(
    Id,
    Iq,
    Vd,
    Vq,
    daf.TwoLevelLossConfig(
        dc_voltage=V_dc,
        on_resistance=Rdson_2l,
        parallel_devices=Npmos_2l,
        switching_frequency=fsw,
        battery=daf.BatteryParameters(
            R0_fn(soc), R1_fn(soc), C1_fn(soc), Nscells_2l, Npcells_2l
        ),
        thermal=daf.ThermalParameters(Tambient, Rth_jc_2l, Rth_ca_2l),
        switching=daf.SwitchingSlopes(
            didt_on_fun, didt_off_fun, dvdt_on_fun, dvdt_off_fun
        ),
    ),
)

# masking the losses that exceed the base current (i.e., the maximum current that can be delivered by the inverter)
Power_loss_inverter_conduction_2l[over_current_mask] = np.nan
Power_loss_inverter_switching_2l[over_current_mask] = np.nan
Power_loss_battery_2l[over_current_mask] = np.nan

Power_loss_total_2l = (
    Power_loss_inverter_conduction_2l
    + Power_loss_inverter_switching_2l
    + Power_loss_battery_2l
)

# %%
# Analysis of the BI-MMC inverter
# -------------------------------------------------------------------------------
wm_mesh = np.meshgrid(wm_ref_vec * 2 * ca.pi / 60 * pp, Tau_ref_vec, indexing="ij")[0]
fsw_bimmc = mf_bimmc * wm_mesh  # switching frequency for the BI-MMC inverter [Hz]
(
    Power_loss_inverter_conduction_bimmc,
    Power_loss_inverter_switching_bimmc,
    Power_loss_battery_bimmc,
    Temp_case_bimmc,
    Temp_junction_bimmc,
) = daf.calc_losses_bimmc(
    Id,
    Iq,
    Vd,
    Vq,
    wm_ref_vec * 2 * ca.pi / 60,  # electrical speed [rad/s]
    Tau_ref_vec,  # reference torque [N.m]
    daf.BimmcLossConfig(
        submodules_per_phase=Nsm,
        submodules_redundant_pu=Nsm_redundant_pu,
        submodule_voltage=Vs_bimmc,
        on_resistance=Rdson_bimmc,
        parallel_devices=Npmos_bimmc,
        switching_frequency=fsw_bimmc,
        thermal=daf.ThermalParameters(Tambient, Rth_jc_bimmc, Rth_ca_bimmc),
        switching=daf.SwitchingSlopes(
            didt_on_bimmc,
            didt_off_bimmc,
            dvdt_on_bimmc,
            dvdt_off_bimmc,
        ),
        battery=daf.BatteryParameters(
            R0_fn(soc), R1_fn(soc), C1_fn(soc), Nscells_bimmc, Npcells_bimmc
        ),
        pole_pairs=pp,
    ),
)

# masking the losses that exceed the base current (i.e., the maximum current that can be delivered by the inverter)
Power_loss_inverter_conduction_bimmc[over_current_mask] = np.nan
Power_loss_inverter_switching_bimmc[over_current_mask] = np.nan
Power_loss_battery_bimmc[over_current_mask] = np.nan

Power_loss_total_bimmc = (
    Power_loss_inverter_conduction_bimmc
    + Power_loss_inverter_switching_bimmc
    + Power_loss_battery_bimmc
)

# %%
# Plotting the losses and efficiency maps for the two-level inverter
# -------------------------------------------------------------------------------
with tab3:
    st.header("Two-level inverter")
    st.write(
        "Below are the losses and efficiency maps for the *SiC-based two-level inverter*, based on the MTPA analysis results."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig3 = dpf.plot_losses(
            dpf.LossMapData(
                Power_loss_inverter_conduction_2l / 1e3,
                Power_loss_inverter_switching_2l / 1e3,
                Power_loss_battery_2l / 1e3,
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=20,
                save_path=RESULTS_DIR / f"losses_maps_2l_{soc_tag}.png",
            ),
        )
        # fig3.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig3.savefig(RESULTS_DIR / f"losses_maps_2l_{soc_tag}.png", dpi=200)
        st.pyplot(fig3, width="stretch")
        fig4 = dpf.plot_Tc_and_Tj(
            dpf.TemperatureMapData(Temp_junction_2l, Temp_case_2l, operating_map),
            dpf.PlotOptions(
                figure_number=21,
                save_path=RESULTS_DIR / f"temperature_maps_2l_{soc_tag}.png",
            ),
        )
        # fig4.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig4.savefig(RESULTS_DIR / f"temperature_maps_2l_{soc_tag}.png", dpi=200)
        st.pyplot(fig4, width="stretch")

    with col2:
        Pout_vec = (
            wm_ref_vec[:, None] * Tau_ref_vec[None, :] * 2 * np.pi / 60
        )  # create a vector of output power values [W]

        # calculate the efficiency maps for the two-level inverter
        Efficiency_conduction_2l = Pout_vec / (
            Pout_vec + (Power_loss_inverter_conduction_2l * np.sign(Pout_vec))
        )
        Efficiency_switching_2l = Pout_vec / (
            Pout_vec + (Power_loss_inverter_switching_2l * np.sign(Pout_vec))
        )
        Efficiency_battery_2l = Pout_vec / (
            Pout_vec + (Power_loss_battery_2l * np.sign(Pout_vec))
        )
        Efficiency_total_2l = Pout_vec / (Pout_vec + Power_loss_total_2l)

        # mask the efficiency values that are below 9% (i.e., set them to NaN) to avoid plotting them
        Efficiency_conduction_2l[Efficiency_total_2l < 0.9] = np.nan
        Efficiency_switching_2l[Efficiency_total_2l < 0.9] = np.nan
        Efficiency_battery_2l[Efficiency_total_2l < 0.9] = np.nan
        Efficiency_total_2l[Efficiency_total_2l < 0.9] = np.nan

        # plot the efficiency maps for the two-level inverter
        fig = dpf.plot_efficiency(
            dpf.EfficiencyMapData(
                Efficiency_conduction_2l * 100,
                Efficiency_switching_2l * 100,
                Efficiency_battery_2l * 100,
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=20,
                save_path=RESULTS_DIR / f"efficiency_maps_2l_{soc_tag}.png",
            ),
        )
        fig.savefig(RESULTS_DIR / f"efficiency_maps_2l_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")

    st.divider()
    st.header("BI-MMC")
    st.write(
        "Below are the losses and efficiency maps for the *Si-based battery-integrated modular multi-level inverter*, based on the MTPA analysis results."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig5 = dpf.plot_losses(
            dpf.LossMapData(
                Power_loss_inverter_conduction_bimmc / 1e3,
                Power_loss_inverter_switching_bimmc / 1e3,
                Power_loss_battery_bimmc / 1e3,
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=30,
                save_path=RESULTS_DIR / f"losses_maps_bimmc_{soc_tag}.png",
            ),
        )
        # fig5.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig5.savefig(RESULTS_DIR / f"losses_maps_bimmc_{soc_tag}.png", dpi=200)
        st.pyplot(fig5, width="stretch")
        fig6 = dpf.plot_Tc_and_Tj(
            dpf.TemperatureMapData(Temp_junction_bimmc, Temp_case_bimmc, operating_map),
            dpf.PlotOptions(
                figure_number=31,
                save_path=RESULTS_DIR / f"temperature_maps_bimmc_{soc_tag}.png",
            ),
        )
        # fig6.suptitle(f"SOC={soc * 100:.0f}%", fontsize=10)
        fig6.savefig(RESULTS_DIR / f"temperature_maps_bimmc_{soc_tag}.png", dpi=200)
        st.pyplot(fig6, width="stretch")
    with col2:

        Pout_vec = (
            wm_ref_vec[:, None] * Tau_ref_vec[None, :] * 2 * np.pi / 60
        )  # create a vector of output power values [W]

        # calculate the efficiency maps for the BI-MMC inverter
        Efficiency_conduction_bimmc = Pout_vec / (
            Pout_vec + (Power_loss_inverter_conduction_bimmc * np.sign(Pout_vec))
        )
        Efficiency_switching_bimmc = Pout_vec / (
            Pout_vec + (Power_loss_inverter_switching_bimmc * np.sign(Pout_vec))
        )
        Efficiency_battery_bimmc = Pout_vec / (
            Pout_vec + (Power_loss_battery_bimmc * np.sign(Pout_vec))
        )
        Efficiency_total_bimmc = Pout_vec / (Pout_vec + Power_loss_total_bimmc)

        # mask the efficiency values that are below 90% (i.e., set them to NaN) to avoid plotting them
        Efficiency_conduction_bimmc[Efficiency_total_bimmc < 0.9] = np.nan
        Efficiency_switching_bimmc[Efficiency_total_bimmc < 0.9] = np.nan
        Efficiency_battery_bimmc[Efficiency_total_bimmc < 0.9] = np.nan
        Efficiency_total_bimmc[Efficiency_total_bimmc < 0.9] = np.nan

        # plot the efficiency maps for the BI-MMC inverter
        fig = dpf.plot_efficiency(
            dpf.EfficiencyMapData(
                Efficiency_conduction_bimmc * 100,
                Efficiency_switching_bimmc * 100,
                Efficiency_battery_bimmc * 100,
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=30,
                save_path=RESULTS_DIR / f"efficiency_maps_bimmc_{soc_tag}.png",
            ),
        )
        fig.savefig(RESULTS_DIR / f"efficiency_maps_bimmc_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")

    st.divider()
    st.subheader("Comparison")
    st.write(
        "Below are the comparison plots for the losses and efficiency maps between the *SiC-based two-level inverter* and the *Si-based battery-integrated modular multi-level inverter*."
    )

    Ptotal_2l = (
        Power_loss_inverter_conduction_2l
        + Power_loss_inverter_switching_2l
        + Power_loss_battery_2l
    )
    Ptotal_bimmc = (
        Power_loss_inverter_conduction_bimmc
        + Power_loss_inverter_switching_bimmc
        + Power_loss_battery_bimmc
    )
    efficiency_total_2l = Pout_vec / (Pout_vec + np.sign(Pout_vec) * Ptotal_2l)
    efficiency_total_bimmc = Pout_vec / (Pout_vec + np.sign(Pout_vec) * Ptotal_bimmc)
    efficiency_total_2l[efficiency_total_2l < 0.95] = np.nan
    efficiency_total_bimmc[efficiency_total_bimmc < 0.95] = np.nan

    col1, col2 = st.columns(2)
    with col1:
        fig = dpf.plot_total_loss_comparison(
            dpf.TotalLossMapData_comparison(
                Ptotal_2l,
                efficiency_total_2l,
                r"2L",
                Ptotal_bimmc,
                efficiency_total_bimmc,
                r"BI-MMC",
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=40,
                save_path=RESULTS_DIR / f"losses_maps_comparison_{soc_tag}.png",
            ),
        )
        # fig.savefig(RESULTS_DIR / f"losses_maps_comparison_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")

        fig = dpf.plot_individual_loss_comparison(
            dpf.IndividualLossMapData_comparison(
                Power_loss_inverter_conduction_2l,
                Power_loss_inverter_switching_2l,
                Power_loss_battery_2l,
                r"2L",
                Power_loss_inverter_conduction_bimmc,
                Power_loss_inverter_switching_bimmc,
                Power_loss_battery_bimmc,
                r"BI-MMC",
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=42,
                save_path=RESULTS_DIR
                / f"individual_losses_maps_comparison_{soc_tag}.png",
            ),
        )
        # fig.savefig(RESULTS_DIR / f"individual_losses_maps_comparison_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")

    with col2:
        fig = dpf.plot_total_efficiency_comparison(
            dpf.TotalLossMapData_comparison(
                Ptotal_2l,
                efficiency_total_2l,
                r"2L",
                Ptotal_bimmc,
                efficiency_total_bimmc,
                r"BI-MMC",
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=41,
                save_path=RESULTS_DIR / f"efficiency_maps_comparison_{soc_tag}.png",
            ),
        )
        # fig.savefig(RESULTS_DIR / f"efficiency_maps_comparison_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")

        fig = dpf.plot_individual_loss_comparison(
            dpf.IndividualLossMapData_comparison(
                Efficiency_conduction_2l,
                Efficiency_switching_2l,
                Efficiency_battery_2l,
                r"2L",
                Efficiency_conduction_bimmc,
                Efficiency_switching_bimmc,
                Efficiency_battery_bimmc,
                r"BI-MMC",
                operating_map,
            ),
            dpf.PlotOptions(
                figure_number=43,
                save_path=RESULTS_DIR
                / f"individual_losses_maps_comparison_{soc_tag}.png",
            ),
        )
        # fig.savefig(RESULTS_DIR / f"individual_losses_maps_comparison_{soc_tag}.png", dpi=200)
        st.pyplot(fig, width="stretch")
