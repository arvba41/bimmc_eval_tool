"""Streamlit entry point; launch with ``streamlit run main.py``.

The sidebar collects the user inputs into a parameter dict in the format of
``model.NOMINAL``; the MTPA, loss and efficiency maps are computed by ``model`` and
drawn by ``plots``.
"""

import time
from pathlib import Path

import numpy as np
import streamlit as st

import model
import plots as dpf

RESULTS_DIR = Path("results_mtpa_soc")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# efficiency values below this threshold are not plotted
EFF_MIN = 0.9

RPM_PER_RADS = 60 / (2 * np.pi)


# ------------------------------------------------------------------------------------
# User inputs
# ------------------------------------------------------------------------------------
def pmsm_inputs(p):
    st.header("PMSM parameters")
    p["pp"] = st.number_input("Pole pairs [-]", min_value=1, value=4, step=1)
    p["PBase"] = st.number_input("Base mechanical power [W]", min_value=0.0, value=400e3)
    p["wmBase"] = st.number_input(
        "Base mechanical speed [rpm]", min_value=1.0, value=3000.0
    )
    p["Vdc"] = st.number_input("DC-link voltage [V]", min_value=0.0, value=700.0)
    p["rs_pu"] = st.number_input(
        "Stator phase resistance [pu]", min_value=0.0, value=0.01
    )
    p["ld_pu"] = st.number_input("d-axis inductance [pu]", min_value=0.0, value=0.55)
    p["lq_pu"] = st.number_input("q-axis inductance [pu]", min_value=0.0, value=0.85)


def mosfet_inputs(p):
    st.header("MOSFET inverter parameters")
    which = st.selectbox(
        "Select the MOSFET device for the inverter",
        options=["Wolfspeed EDB005M12TM4", "Costumized MOSFET"],
    )
    p["fsw"] = st.number_input("Switching frequency [Hz]", min_value=1.0, value=10e3)

    if which == "Wolfspeed EDB005M12TM4":
        # https://assets.wolfspeed.com/uploads/2025/10/Wolfspeed_EDB005M12TM4_EDB005M12TM4L_data_sheet.pdf
        # Rdson, current rating (320 A RMS at 175 °C), Rth_jc and Tjmax are datasheet
        # values; the 100 °C case limit is taken from
        # https://www.guchen-eac.com/who/news/the-thermal-management-system-of-xpeng-x7.html
        p["mosfet"] = "Wolfspeed"
        p["Rdson_2l"] = 4.6e-3
        p["ImosRated_RMS"] = 320.0
        p["Rth_jc_2l"] = 0.08
        p["Tjmax_2l"] = 175.0
        p["Tcmax_2l"] = 100.0
        # TODO: CAB760M12HM3 (Wolfspeed_CAB760M12HM3_data_sheet.pdf)
    else:
        p["mosfet"] = "custom"
        p["Rdson_2l"] = st.number_input("Rdson [mOhm]", min_value=0.0, value=4.6) * 1e-3
        p["ImosRated_RMS"] = st.number_input(
            "MOSFET continuous RMS current rating [A]", min_value=0.0, value=400.0
        )
        p["didt_on_2l"] = st.number_input(
            "di/dt (on) [A/ns]", min_value=0.01, value=8.0, step=0.1
        )
        p["didt_off_2l"] = st.number_input(
            "di/dt (off) [A/ns]", min_value=0.01, value=15.0, step=0.1
        )
        p["dvdt_on_2l"] = st.number_input(
            "dv/dt (on) [V/ns]", min_value=0.01, value=25.0, step=0.1
        )
        p["dvdt_off_2l"] = st.number_input(
            "dv/dt (off) [V/ns]", min_value=0.01, value=25.0, step=0.1
        )
        p["Tjmax_2l"] = st.number_input(
            "Maximum junction temperature [°C]", min_value=0.0, value=175.0
        )
        p["Tcmax_2l"] = st.number_input(
            "Maximum case temperature [°C]", min_value=0.0, value=100.0
        )
        p["Rth_jc_2l"] = st.number_input(
            "Thermal resistance junction-to-case [°C/W]", min_value=0.0, value=0.08
        )
        st.markdown(
            "Rdson(Tj) / Rdson(25 °C) as a 3rd order polynomial: "
            "$c_3 T_j^3 + c_2 T_j^2 + c_1 T_j + c_0$ (Tj in °C)"
        )
        p["Rdson_poly"] = [
            st.number_input(
                f"Rdson polynomial coefficient c{k}",
                value=float(c),
                format="%.6e",
                key=f"rdson_poly_c{k}",
            )
            for k, c in zip((3, 2, 1, 0), model.RDSON_POLY_DEFAULT)
        ]

    # Liquid-cooled traction inverters typically have a combined case-to-ambient thermal
    # resistance (Rth_CA = Rth_CS + Rth_SA) of 0.05-0.10 K/W per module or inverter leg.
    # References:
    # 1. https://scholarworks.uark.edu/etd/6014/
    # 2. https://www.mdpi.com/1996-1073/18/22/6020
    # 3. https://www.automotive-iq.com/thermal-management/articles/800v-sic-thermal-management-explained-why-the-whole-cooling-system-has-to-change
    p["Rth_ca_2l"] = st.number_input(
        "Thermal resistance case-to-ambient [°C/W]", min_value=0.0, value=0.05
    )
    p["Tambient"] = st.number_input("Ambient temperature [°C]", min_value=0.0, value=25.0)


def battery_inputs(p):
    st.header("Battery parameters")
    p["chemistry"] = st.selectbox(
        "Select the battery chemistry", options=list(model.OCV)[1:]
    )
    p["Ebatt"] = (
        st.number_input("Battery energy [kWh]", min_value=0.0, value=400.0) * 1e3
    )  # [Wh]
    cell = st.selectbox("Select the cell", options=["Samsung PHEV2 24Ah", "Custom cell"])

    if cell == "Samsung PHEV2 24Ah":
        # internal resistances are based on empirical data; C1 follows from a 250 Hz RC corner
        p["Qcell"] = 24.0
        p["R0_nom"] = 1.2e-3
        p["R1_nom"] = 0.7e-3
        p["poly_r"] = model.CELL_POLY_R_DEFAULT
        p["poly_c"] = model.CELL_POLY_C_DEFAULT
    else:
        p["Qcell"] = st.number_input("Cell capacity [Ah]", min_value=0.0, value=24.0)
        p["R0_nom"] = (
            st.number_input("Cell internal resistance R0 [mOhm]", min_value=0.0, value=1.2)
            * 1e-3
        )
        p["R1_nom"] = (
            st.number_input("Cell internal resistance R1 [mOhm]", min_value=0.0, value=0.7)
            * 1e-3
        )
        p["C1_nom"] = st.number_input(
            "Cell RC branch capacitance C1 [F]",
            min_value=0.0,
            value=1 / (2 * np.pi * 250 * p["R1_nom"]),
        )
        st.markdown(
            "SOC dependence of the cell parameters (SOC in 0-1): R0 and R1 are scaled by "
            "$a_2 SOC^2 + a_1 SOC + a_0$ and C1 by the corresponding polynomial"
        )
        for key, label, default in (
            ("poly_r", "R0/R1", model.CELL_POLY_R_DEFAULT),
            ("poly_c", "C1", model.CELL_POLY_C_DEFAULT),
        ):
            p[key] = [
                st.number_input(
                    f"{label} polynomial coefficient a{k}",
                    value=float(c),
                    format="%.4f",
                    key=f"{key}_a{k}",
                )
                for k, c in zip((2, 1, 0), default)
            ]


def bimmc_inputs(p):
    st.header("AC-battery parameters")
    p["bimmc_sizing"] = "ceil"  # exactly Nsm submodules, cells per submodule rounded up
    p["Nsm"] = st.number_input(
        "Number of submodules per phase", min_value=1, value=12, step=1
    )
    p["Nsm_redundant_pu"] = st.number_input(
        "Number of redundant submodules per phase [pu]",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )
    # Rdson and current rating: example taken from the Infineon IQDH29NE2LM5CGSC
    bimmc_mosfet = st.selectbox(
        "Rdson(Tj) of the BI-MMC MOSFET",
        options=["Fit of Infineon IQDH29NE2LM5CGSC datasheet", "Custom polynomial"],
    )
    if bimmc_mosfet == "Custom polynomial":
        st.markdown(
            "Rdson(Tj) / Rdson(25 °C) as a 3rd order polynomial: "
            "$c_3 T_j^3 + c_2 T_j^2 + c_1 T_j + c_0$ (Tj in °C)"
        )
        p["Rdson_poly_bimmc"] = [
            st.number_input(
                f"Rdson polynomial coefficient c{k}",
                value=float(c),
                format="%.6e",
                key=f"rdson_poly_bimmc_c{k}",
            )
            for k, c in zip((3, 2, 1, 0), model.RDSON_POLY_BIMMC_DATASHEET)
        ]
    else:
        p["Rdson_poly_bimmc"] = None
    p["Rdson_bimmc"] = (
        st.number_input("Rdson at 25 °C [mOhm]", min_value=0.0, value=0.3, step=0.1) * 1e-3
    )
    p["Imax_mosfet"] = st.number_input(
        "MOSFET continuous RMS current rating [A]", min_value=1.0, value=400.0
    )
    # NOTE: the switching slopes are assumed constant; replace them with datasheet or
    # experimental data of the actual device.
    p["didt_on_bimmc"] = st.number_input(
        "didt (on) [A/ns]", min_value=0.01, value=1.0, step=0.1
    )
    p["didt_off_bimmc"] = st.number_input(
        "didt (off) [A/ns]", min_value=0.01, value=1.0, step=0.1
    )
    p["dvdt_on_bimmc"] = st.number_input(
        "dvdt (on) [V/ns]", min_value=0.01, value=0.5, step=0.1
    )
    p["dvdt_off_bimmc"] = st.number_input(
        "dvdt (off) [V/ns]", min_value=0.01, value=0.5, step=0.1
    )
    p["mf_bimmc"] = st.number_input(
        "Pulse number (switching frequency multiplier) [-]",
        min_value=1,
        value=2,
        step=1,
    )
    p["Rth_jc_bimmc"] = st.number_input(
        "Thermal resistance junction-to-case [°C/W]", min_value=0.0, value=0.5
    )
    # cooling system thermal resistance from the case to the ambient
    p["Rth_ca_bimmc"] = st.number_input(
        "Thermal resistance case-to-ambient [°C/W]", min_value=0.0, value=0.2
    )


# ------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------
def bullets(items):
    return "\n".join(f"- {label}: `{value}`" for label, value in items)


def efficiency_maps(Pout, Pc, Ps, Pb):
    """Efficiency of each loss component and in total; points below EFF_MIN are NaN."""
    total = model.efficiency(Pout, Pc + Ps + Pb)
    parts = [model.efficiency(Pout, P) for P in (Pc, Ps, Pb)]
    with np.errstate(invalid="ignore"):
        low = total < EFF_MIN
    for eff in (*parts, total):
        eff[low] = np.nan
    return (*parts, total)


def show(fig):
    st.pyplot(fig, width="stretch")


# ------------------------------------------------------------------------------------
# Page
# ------------------------------------------------------------------------------------
st.set_page_config(page_title="AC battery evaluator", layout="wide")
title_column, logo_column = st.columns([5, 1])
with title_column:
    st.title("AC battery evaluator")
with logo_column:
    logo_files = sorted((Path(__file__).parent / "logo").glob("*_white.png"))
    if logo_files:
        st.image(logo_files[0], width="content")

tab1, tab2, tab3 = st.tabs(["Parameters", "MTPA maps", "Loss and Efficiency maps"])

p = dict(model.NOMINAL)
with st.sidebar:
    soc = st.selectbox(
        "Select the SOC value for the MTPA and Efficiency maps",
        options=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        index=4,
    )
    for section in (pmsm_inputs, mosfet_inputs, battery_inputs, bimmc_inputs):
        st.divider()
        section(p)

try:
    d = model.design(p)
except ValueError:
    st.error(
        "d-axis inductance too large: Ld*Ibase >= magnet flux (no finite maximum speed)."
    )
    st.stop()

motor = d.motor
Vcell = float(model.cell_state(p, soc)[0])  # cell voltage at the selected SOC [V]
ZBase = (d.VBase / np.sqrt(2) * np.sqrt(3)) ** 2 / p["PBase"]  # base impedance [Ohm]
xi = (motor.d_axis_inductance - motor.q_axis_inductance) * d.Ibase / motor.magnet_flux

# ------------------------------------------------------------------------------------
# Parameters tab
# ------------------------------------------------------------------------------------
with tab1:
    st.header("User inputs")
    st.write(
        "Below are the user inputs and the derived parameters for the PMSM, inverter, battery, and AC Battery."
    )
    st.subheader("PMSM parameters")
    st.write(
        bullets(
            [
                ("Pole pairs", p["pp"]),
                ("Base mechanical power", f"{p['PBase'] / 1e3:.0f} kW"),
                ("Base mechanical speed", f"{p['wmBase']:.0f} rpm"),
                ("Base torque", f"{d.TBase:.0f} N.m"),
                ("Base phase voltage (peak)", f"{d.VBase:.0f} V"),
                ("Maximum phase voltage (peak)", f"{d.VMax:.0f} V"),
                ("Permanent magnet flux linkage", f"{motor.magnet_flux * 1e3:.2f} mWb"),
                ("Base impedance", f"{ZBase * 1e3:.2f} mOhm"),
                ("Base current", f"{d.Ibase:.2f} A"),
                ("Stator phase resistance", f"{motor.stator_resistance * 1e3:.2f} mOhm"),
                ("d-axis inductance", f"{motor.d_axis_inductance * 1e6:.2f} uH"),
                ("q-axis inductance", f"{motor.q_axis_inductance * 1e6:.2f} uH"),
                ("Maximum mechanical speed", f"{d.wmMax * RPM_PER_RADS:.1f} rpm"),
                ("Saliency ratio", f"{xi:.4f}"),
            ]
        )
    )
    st.subheader("Inverter parameters")
    st.write(
        bullets(
            [
                ("Rdson", f"{p['Rdson_2l'] * 1e3:.2f} mOhm"),
                ("Number of parallel MOSFETs", f"{d.Npmos_2l:.0f}"),
                ("Switching frequency", f"{p['fsw'] / 1e3:.0f} kHz"),
                ("Fundamental frequency", f"{p['wmBase'] * p['pp'] / 60:.2f} Hz"),
                ("Thermal resistance junction-to-case", f"{p['Rth_jc_2l']:.3f} °C/W"),
                ("Thermal resistance case-to-ambient", f"{p['Rth_ca_2l']:.3f} °C/W"),
                ("Maximum junction temperature", f"{p['Tjmax_2l']:.1f} °C"),
                ("Maximum case temperature", f"{p['Tcmax_2l']:.1f} °C"),
                ("Ambient temperature", f"{p['Tambient']:.1f} °C"),
            ]
        )
    )
    st.subheader("Battery parameters")
    st.write(
        bullets(
            [
                ("Battery energy", f"{p['Ebatt'] / 1e3:.0f} kWh"),
                ("Selected battery chemistry", p["chemistry"]),
                ("Cell capacity", f"{p['Qcell']:.0f} Ah"),
                ("Number of series (equivalent) cells", d.Nscells_2l),
                ("Number of parallel (equivalent) cells", d.Npcells_2l),
            ]
        )
    )
    st.subheader("BI-MMC parameters")
    st.write(
        bullets(
            [
                ("Number of submodules per phase", d.Nsm),
                (
                    "Number of redundant submodules per phase",
                    f"{p['Nsm_redundant_pu'] * 100}%",
                ),
                ("BI-MMC Rdson", f"{p['Rdson_bimmc'] * 1e3:.2f} mOhm"),
                ("Number of parallel MOSFETs", d.Npmos_b),
                ("BI-MMC Vmax", f"{d.Vnom * d.Nsm * d.Nscells_b:.2f} V"),
                ("Number of series cells per SM", d.Nscells_b),
                ("SM battery voltage", f"{Vcell * d.Nscells_b:.2f} V"),
            ]
        )
    )

    mosfet_plot, battery_plots = st.columns(2)
    with mosfet_plot:
        slopes, Rdson_Tj_fun = model.mosfet_data(p)
        slopes_raw, Rdson_raw = model.mosfet_raw(p)
        st.subheader("MOSFET switching slopes")
        show(
            dpf.plot_switching_slopes(
                slopes_raw,
                slopes.didt_on,
                slopes.didt_off,
                slopes.dvdt_on,
                slopes.dvdt_off,
                save_path=RESULTS_DIR / "switching_slopes.png",
            )
        )
        st.subheader("MOSFET Rdson vs Tj")
        show(
            dpf.plot_Rdson_vs_Tj(
                Rdson_raw, Rdson_Tj_fun, save_path=RESULTS_DIR / "Rdson_vs_Tj.png"
            )
        )
        st.subheader("BI-MMC MOSFET Rdson vs Tj")
        show(
            dpf.plot_Rdson_vs_Tj(
                model.bimmc_rdson_raw() if p["Rdson_poly_bimmc"] is None else None,
                model.bimmc_rdson_fun(p),
                save_path=RESULTS_DIR / "Rdson_vs_Tj_bimmc.png",
            )
        )
    with battery_plots:
        st.subheader("Cell OCV curve")
        show(
            dpf.plot_cell_ocv_vs_soc(
                model.OCV, p["chemistry"], save_path=RESULTS_DIR / "battery_ocv.png"
            )
        )
        st.subheader("Cell RC parameters")
        show(
            dpf.plot_battery_parameters(
                lambda s: model.cell_state(p, s)[1],
                lambda s: model.cell_state(p, s)[2],
                lambda s: model.cell_state(p, s)[3],
                save_path=RESULTS_DIR / "battery_parameters.png",
            )
        )

# ------------------------------------------------------------------------------------
# Analysis: MTPA and loss maps of both converters
# ------------------------------------------------------------------------------------
wm_vec, T_vec = model.default_grid(p)  # [rad/s], [N.m]
t0 = time.perf_counter()
with tab2, st.spinner("Running MTPA and loss analysis..."):
    # the dashboard uses the 2L voltage limit for both converters and a constant Rdson
    res = model.loss_maps(p, soc, wm_vec, T_vec, voltage_limit="2l", rdson_tj=False)
t_analysis = time.perf_counter() - t0

Id, Iq = res["Id_2l"], res["Iq_2l"]
Vd, Vq = model.dq_voltages(d, Id, Iq, wm_vec)
Pout = res["Pout"]
operating_map = dpf.OperatingMap(wm_vec * RPM_PER_RADS, T_vec, p["PBase"], d.TBase)
soc_tag = f"soc_{int(round(soc * 100)):02d}"

converters = {
    key: {
        "Pc": res[f"Pc_{key}"],
        "Ps": res[f"Ps_{key}"],
        "Pb": res[f"Pb_{key}"],
        "Tj": res[f"Tj_{key}"],
        "Tc": res[f"Tc_{key}"],
    }
    for key in ("2l", "bimmc")
}
for conv in converters.values():
    conv["Ploss"] = conv["Pc"] + conv["Ps"] + conv["Pb"]
    conv["eff"] = efficiency_maps(Pout, conv["Pc"], conv["Ps"], conv["Pb"])

# ------------------------------------------------------------------------------------
# MTPA tab
# ------------------------------------------------------------------------------------
with tab2:
    st.header("MTPA analysis results")
    st.write(f"Total computation time of the MTPA and loss analysis: {t_analysis:.1f} s.")
    st.write(
        "Below are the results of the MTPA analysis for the selected SOC value. The plots show the d-axis and q-axis currents, as well as the d-axis and q-axis voltages, as functions of the reference torque and speed."
    )
    mtpa_map_data = dpf.MtpaMapData(
        Id, Iq, Vd, Vq, operating_map, Vcell * d.Nscells_2l / 2, d.Ibase, soc
    )
    col1, col2 = st.columns(2)
    with col1:
        show(
            dpf.plot_mtpa_maps(
                mtpa_map_data,
                dpf.PlotOptions(
                    figure_number=10,
                    save_path=RESULTS_DIR / f"mtpa_maps_{soc_tag}.png",
                ),
            )
        )
    with col2:
        show(
            dpf.plot_mtpa_maps_dqs(
                mtpa_map_data,
                dpf.PlotOptions(
                    figure_number=11,
                    save_path=RESULTS_DIR / f"mtpa_maps_dqs_{soc_tag}.png",
                ),
            )
        )

# ------------------------------------------------------------------------------------
# Loss and efficiency tab
# ------------------------------------------------------------------------------------
with tab3:
    sections = [
        (
            "2l",
            "Two-level inverter",
            "Below are the losses and efficiency maps for the *SiC-based two-level inverter*, based on the MTPA analysis results.",
            20,
        ),
        (
            "bimmc",
            "BI-MMC",
            "Below are the losses and efficiency maps for the *Si-based battery-integrated modular multi-level inverter*, based on the MTPA analysis results.",
            30,
        ),
    ]
    for key, header, text, fig_no in sections:
        conv = converters[key]
        st.header(header)
        st.write(text)
        col1, col2 = st.columns(2)
        with col1:
            show(
                dpf.plot_losses(
                    dpf.LossMapData(
                        conv["Pc"] / 1e3,
                        conv["Ps"] / 1e3,
                        conv["Pb"] / 1e3,
                        operating_map,
                    ),
                    dpf.PlotOptions(
                        figure_number=fig_no,
                        save_path=RESULTS_DIR / f"losses_maps_{key}_{soc_tag}.png",
                    ),
                )
            )
            show(
                dpf.plot_Tc_and_Tj(
                    dpf.TemperatureMapData(conv["Tj"], conv["Tc"], operating_map),
                    dpf.PlotOptions(
                        figure_number=fig_no + 1,
                        save_path=RESULTS_DIR / f"temperature_maps_{key}_{soc_tag}.png",
                    ),
                )
            )
        with col2:
            eff_c, eff_s, eff_b, _ = conv["eff"]
            show(
                dpf.plot_efficiency(
                    dpf.EfficiencyMapData(
                        eff_c * 100, eff_s * 100, eff_b * 100, operating_map
                    ),
                    dpf.PlotOptions(
                        figure_number=fig_no + 2,
                        save_path=RESULTS_DIR / f"efficiency_maps_{key}_{soc_tag}.png",
                    ),
                )
            )
        st.divider()

    st.subheader("Comparison")
    st.write(
        "Below are the comparison plots for the losses and efficiency maps between the *SiC-based two-level inverter* and the *Si-based battery-integrated modular multi-level inverter*."
    )
    c2l, cb = converters["2l"], converters["bimmc"]
    total_map = dpf.TotalLossMapData_comparison(
        c2l["Ploss"], c2l["eff"][3], r"2L", cb["Ploss"], cb["eff"][3], r"BI-MMC", operating_map
    )
    col1, col2 = st.columns(2)
    with col1:
        show(
            dpf.plot_total_loss_comparison(
                total_map,
                dpf.PlotOptions(
                    figure_number=40,
                    save_path=RESULTS_DIR / f"losses_maps_comparison_{soc_tag}.png",
                ),
            )
        )
        show(
            dpf.plot_individual_loss_comparison(
                dpf.IndividualLossMapData_comparison(
                    c2l["Pc"],
                    c2l["Ps"],
                    c2l["Pb"],
                    r"2L",
                    cb["Pc"],
                    cb["Ps"],
                    cb["Pb"],
                    r"BI-MMC",
                    operating_map,
                ),
                dpf.PlotOptions(
                    figure_number=42,
                    save_path=RESULTS_DIR
                    / f"individual_losses_maps_comparison_{soc_tag}.png",
                ),
            )
        )
    with col2:
        show(
            dpf.plot_total_efficiency_comparison(
                total_map,
                dpf.PlotOptions(
                    figure_number=41,
                    save_path=RESULTS_DIR / f"efficiency_maps_comparison_{soc_tag}.png",
                ),
            )
        )
        show(
            dpf.plot_individual_loss_comparison(
                dpf.IndividualLossMapData_comparison(
                    *c2l["eff"][:3],
                    r"2L",
                    *cb["eff"][:3],
                    r"BI-MMC",
                    operating_map,
                    quantity="efficiency",
                ),
                dpf.PlotOptions(
                    figure_number=43,
                    save_path=RESULTS_DIR
                    / f"individual_efficiency_maps_comparison_{soc_tag}.png",
                ),
            )
        )
