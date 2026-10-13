"""One-at-a-time sensitivity analysis of the converter efficiency.

For every user input parameter, the parameter is swept around its nominal value
(all others kept at nominal) and the total efficiency of the two-level inverter and
of the BI-MMC is evaluated at a given operating point (speed, torque, SOC).

Usage:
    python sens.py [--speed-pu 1.0] [--torque-pu 0.8] [--variation 0.3] [--points 7]
"""

import argparse
import os
from copy import deepcopy
from pathlib import Path

import casadi as ca
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

import calc as daf

RESULTS_DIR = Path("results_sens")
DATA_DIR = Path(__file__).parent / "data"

OCV = {
    "soc": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
    "NMC": [4.13, 4.03, 3.92, 3.83, 3.75, 3.70, 3.66, 3.63, 3.59, 3.53, 3.34],
    "LFP": [3.39, 3.33, 3.31, 3.32, 3.31, 3.29, 3.27, 3.26, 3.25, 3.18, 2.89],
    "LTO": [2.69, 2.42, 2.35, 2.32, 2.28, 2.23, 2.20, 2.19, 2.18, 2.15, 2.11],
    "NaB": [3.9, 3.74, 3.61, 3.47, 3.29, 3.12, 2.99, 2.87, 2.75, 2.55, 2.22],
}

# Nominal user inputs (same defaults as the dashboard)
NOMINAL = {
    # operating point / general
    "soc": 0.5,
    # PMSM
    "pp": 4,
    "PBase": 400e3,  # [W]
    "wmBase": 3000.0,  # [rpm]
    "Vdc": 700.0,  # [V]
    "rs_pu": 0.01,
    "ld_pu": 0.55,
    "lq_pu": 0.85,
    # two-level inverter ("Wolfspeed" or "custom")
    "mosfet": "Wolfspeed",
    "fsw": 10e3,  # [Hz]
    "Rdson_2l": 4.6e-3,  # [Ohm]
    "ImosRated_RMS": 320.0,  # [A]
    "Rth_jc_2l": 0.08,  # [°C/W]
    "Rth_ca_2l": 0.05,  # [°C/W]
    "Tambient": 25.0,  # [°C]
    # custom MOSFET switching slopes (only used if mosfet == "custom")
    "didt_on_2l": 8.0,
    "didt_off_2l": 15.0,
    "dvdt_on_2l": 25.0,
    "dvdt_off_2l": 25.0,
    # battery
    "chemistry": "NMC",
    "Ebatt": 400e3,  # [Wh]
    "Qcell": 24.0,  # [Ah]
    "R0_nom": 1.2e-3,  # [Ohm]
    "R1_nom": 0.7e-3,  # [Ohm]
    # BI-MMC
    "Nsm": 12,
    "Nsm_redundant_pu": 0.0,
    "Rdson_bimmc": 0.3e-3,  # [Ohm]
    "Imax_mosfet": 400.0,  # [A]
    "didt_on_bimmc": 1.0,
    "didt_off_bimmc": 1.0,
    "dvdt_on_bimmc": 0.5,
    "dvdt_off_bimmc": 0.5,
    "mf_bimmc": 2,
    "Rth_jc_bimmc": 0.5,
    "Rth_ca_bimmc": 0.2,
}

# Parameters swept in the analysis (continuous: relative variation; integer: rounded)
SWEPT = [
    "soc",
    "PBase",
    "wmBase",
    "Vdc",
    "rs_pu",
    "ld_pu",
    "lq_pu",
    "fsw",
    "Rdson_2l",
    "ImosRated_RMS",
    "Rth_jc_2l",
    "Rth_ca_2l",
    "Tambient",
    "Ebatt",
    "Qcell",
    "R0_nom",
    "R1_nom",
    "Nsm",
    "Nsm_redundant_pu",
    "Rdson_bimmc",
    "Imax_mosfet",
    "didt_on_bimmc",
    "didt_off_bimmc",
    "dvdt_on_bimmc",
    "dvdt_off_bimmc",
    "mf_bimmc",
    "Rth_jc_bimmc",
    "Rth_ca_bimmc",
]
INTEGER_PARAMS = {"Nsm", "mf_bimmc", "pp"}
# Parameters that can't be scaled multiplicatively (nominal value of zero) use an absolute span
ABSOLUTE_SPAN = {"Nsm_redundant_pu": (0.0, 0.2), "soc": (0.1, 1.0)}
# Custom-MOSFET-only parameters are swept only when mosfet == "custom"
CUSTOM_ONLY = {"didt_on_2l", "didt_off_2l", "dvdt_on_2l", "dvdt_off_2l"}


def _slope_function(df: pd.DataFrame, name: str):
    return interp1d(
        df[f"{name}_X"],
        df[f"{name}_Y"],
        kind="linear",
        bounds_error=False,
        fill_value=(df[f"{name}_Y"].iloc[0], df[f"{name}_Y"].iloc[-1]),
    )


def _mosfet_data(p, ImosRated):
    """Return the switching slope functions and the Rdson(Tj) function."""
    if p["mosfet"] == "Wolfspeed":
        raw = pd.read_csv(DATA_DIR / "Wolfspeed_MOSFET_dvdt_didt_data.csv")
        rdson_raw = pd.read_csv(DATA_DIR / "Wolfspeed_MOSFET_Rdson_vs_Tj_data.csv")
    else:
        raw = pd.DataFrame(
            {
                f"{k}_{ax}": ([0, ImosRated] if ax == "X" else [p[f"{k}_2l"]] * 2)
                for k in ("didt_on", "didt_off", "dvdt_on", "dvdt_off")
                for ax in ("X", "Y")
            }
        )
        rdson_raw = pd.DataFrame({"Tj": [0, 25, 175], "Rdson_normalized": [1, 1, 2]})
    slopes = daf.SwitchingSlopes(
        *[_slope_function(raw, k) for k in ("didt_on", "didt_off", "dvdt_on", "dvdt_off")]
    )
    return slopes


def evaluate(p, speed_pu=1.0, torque_pu=1.0):
    """Total efficiency [-] of the two-level inverter and the BI-MMC at one operating point."""
    # --- PMSM
    VBase = p["Vdc"] / 2
    VMax = VBase * 2 / np.sqrt(3)
    wmBase_rads = p["wmBase"] * 2 * np.pi / 60
    TBase = p["PBase"] / wmBase_rads
    psi_f = VBase / (wmBase_rads * p["pp"])
    ZBase = (VBase / np.sqrt(2) * np.sqrt(3)) ** 2 / p["PBase"]
    Ibase = np.ceil(2 * p["PBase"] / (3 * VBase) / 50) * 50
    Rs = p["rs_pu"] * ZBase
    Ld = p["ld_pu"] * ZBase / (wmBase_rads * p["pp"])
    Lq = p["lq_pu"] * ZBase / (wmBase_rads * p["pp"])
    wmMax = VMax / (psi_f - Ld * Ibase) / p["pp"] * 60 / (2 * np.pi)

    # --- operating point (speed and torque in pu of the base values)
    wm = speed_pu * p["wmBase"]
    Tau = torque_pu * TBase
    Pout = wm * 2 * np.pi / 60 * Tau
    if wm > wmMax or abs(Pout) > p["PBase"]:
        return np.nan, np.nan

    # --- battery
    ocv = OCV[p["chemistry"]]
    Vnom = ocv[OCV["soc"].index(0.5)]
    soc = p["soc"]
    Vcell = float(np.interp(soc, OCV["soc"][::-1], ocv[::-1]))
    poly_r = lambda s: 1.3 * s**2 - 1.3 * s + 1.3
    poly_c = lambda s: -1.3 * s**2 + 1.3 * s + 1.3
    C1_nom = 1 / (2 * np.pi * 250 * p["R1_nom"])
    R0, R1, C1 = (
        p["R0_nom"] * poly_r(soc),
        p["R1_nom"] * poly_r(soc),
        C1_nom * poly_c(soc),
    )

    # --- MTPA
    motor = daf.MotorParameters(Rs, Ld, Lq, psi_f, p["pp"])
    opti, x, (Tau_ref, wm_ref, vmax) = daf.create_mtpa_optimization_problem(motor)
    Nscells_2l = int(np.ceil(2 * VBase / Vnom))
    Npcells_2l = int(np.ceil(p["Ebatt"] / (p["Qcell"] * (Vnom * Nscells_2l))))
    V_dc = Vcell * Nscells_2l / 2
    opti.set_value(vmax, V_dc * 2 / np.sqrt(3))
    opti.set_value(Tau_ref, Tau)
    opti.set_value(wm_ref, wm * 2 * np.pi / 60)
    try:
        sol = opti.solve()
    except RuntimeError:
        return np.nan, np.nan
    Id = np.array([[sol.value(x[0])]])
    Iq = np.array([[sol.value(x[1])]])
    if Id**2 + Iq**2 > Ibase**2:
        return np.nan, np.nan
    wr = wm * 2 * np.pi / 60 * p["pp"]
    Vd = Id * Rs - wr * Lq * Iq
    Vq = Iq * Rs + wr * (psi_f + Ld * Id)

    # --- two-level inverter
    ImosRated = p["ImosRated_RMS"] * np.sqrt(2)
    Npmos_2l = np.ceil(Ibase / ImosRated)
    slopes_2l = _mosfet_data(p, ImosRated)
    Pc, Ps, Pb, _, _ = daf.calc_losses_2l(
        Id,
        Iq,
        Vd,
        Vq,
        daf.TwoLevelLossConfig(
            dc_voltage=2 * V_dc,  # full DC-link voltage
            on_resistance=p["Rdson_2l"],
            parallel_devices=Npmos_2l,
            switching_frequency=p["fsw"],
            battery=daf.BatteryParameters(R0, R1, C1, Nscells_2l, Npcells_2l),
            thermal=daf.ThermalParameters(
                p["Tambient"], p["Rth_jc_2l"], p["Rth_ca_2l"]
            ),
            switching=slopes_2l,
        ),
    )
    eff_2l = (Pout / (Pout + Pc + Ps + Pb)).item()

    # --- BI-MMC
    Nsm = int(p["Nsm"])
    Nscells_b = int(np.ceil(2 * VBase / np.sqrt(3) / (Vnom * Nsm)))
    Npcells_b = int(
        np.ceil(p["Ebatt"] / (3 * Nsm * Vnom * Nscells_b * p["Qcell"]))
    )
    Npmos_b = max(int(np.ceil(Ibase / p["Imax_mosfet"])), 4)
    Vs_b = Vcell * Nscells_b
    # NOTE: same switching-frequency definition as in main.py
    fsw_b = p["mf_bimmc"] * np.array([[wr / (2 * np.pi)]])  # [Hz]
    Pc, Ps, Pb, _, _ = daf.calc_losses_bimmc(
        Id,
        Iq,
        Vd,
        Vq,
        np.array([wm * 2 * np.pi / 60]),
        np.array([Tau]),
        daf.BimmcLossConfig(
            submodules_per_phase=Nsm,
            submodules_redundant_pu=p["Nsm_redundant_pu"],
            submodule_voltage=Vs_b,
            on_resistance=p["Rdson_bimmc"],
            parallel_devices=Npmos_b,
            switching_frequency=fsw_b,
            thermal=daf.ThermalParameters(
                p["Tambient"], p["Rth_jc_bimmc"], p["Rth_ca_bimmc"]
            ),
            switching=daf.SwitchingSlopes(
                p["didt_on_bimmc"],
                p["didt_off_bimmc"],
                p["dvdt_on_bimmc"],
                p["dvdt_off_bimmc"],
            ),
            battery=daf.BatteryParameters(R0, R1, C1, Nscells_b, Npcells_b),
            pole_pairs=p["pp"],
        ),
    )
    eff_b = (Pout / (Pout + Pc + Ps + Pb)).item()
    return eff_2l, eff_b


def sweep_values(name, nominal, variation, points):
    if name in ABSOLUTE_SPAN:
        values = np.linspace(*ABSOLUTE_SPAN[name], points)
        if name == "soc":
            values = np.round(values, 2)
    else:
        values = np.linspace(
            nominal * (1 - variation), nominal * (1 + variation), points
        )
    if name in INTEGER_PARAMS:
        values = np.unique(np.maximum(np.round(values), 1)).astype(int)
    return values


def run_sensitivity(speed_pu, torque_pu, variation, points):
    base_2l, base_b = evaluate(NOMINAL, speed_pu, torque_pu)
    print(f"Nominal efficiency: 2L = {base_2l * 100:.3f} %, BI-MMC = {base_b * 100:.3f} %")

    rows = []
    for name in SWEPT:
        if name in CUSTOM_ONLY and NOMINAL["mosfet"] != "custom":
            continue
        for value in sweep_values(name, NOMINAL[name], variation, points):
            p = deepcopy(NOMINAL)
            p[name] = value
            e2l, eb = evaluate(p, speed_pu, torque_pu)
            rows.append(
                {
                    "parameter": name,
                    "value": value,
                    "relative_change": value / NOMINAL[name] - 1
                    if NOMINAL[name]
                    else np.nan,
                    "eff_2l_pct": e2l * 100,
                    "eff_bimmc_pct": eb * 100,
                }
            )
        print(f"  done: {name}")
    return pd.DataFrame(rows), (base_2l * 100, base_b * 100)


def plot_results(df, base, speed_pu, torque_pu):
    params = list(dict.fromkeys(df["parameter"]))
    ncols = 4
    nrows = int(np.ceil(len(params) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows))
    for ax, name in zip(axes.ravel(), params):
        d = df[df["parameter"] == name]
        ax.plot(d["value"], d["eff_2l_pct"], "o-", label="2L")
        ax.plot(d["value"], d["eff_bimmc_pct"], "s-", label="BI-MMC")
        ax.axhline(base[0], color="C0", ls=":", lw=0.8)
        ax.axhline(base[1], color="C1", ls=":", lw=0.8)
        ax.set_xlabel(name)
        ax.set_ylabel("Efficiency [%]")
        ax.grid(alpha=0.3)
    for ax in axes.ravel()[len(params) :]:
        ax.axis("off")
    axes.ravel()[0].legend()
    fig.suptitle(f"Efficiency sensitivity (speed={speed_pu} pu, torque={torque_pu} pu)")
    fig.tight_layout()

    # Tornado chart: efficiency span over each sweep
    span = (
        df.groupby("parameter")[["eff_2l_pct", "eff_bimmc_pct"]]
        .agg(lambda s: s.max() - s.min())
        .sort_values("eff_2l_pct")
    )
    fig2, (a1, a2) = plt.subplots(1, 2, figsize=(12, 0.3 * len(span) + 2), sharey=False)
    for ax, col, title in zip(
        (a1, a2), ("eff_2l_pct", "eff_bimmc_pct"), ("Two-level inverter", "BI-MMC")
    ):
        s = span[col].sort_values()
        ax.barh(s.index, s.values)
        ax.set_xlabel("Efficiency span [pp]")
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="x")
    fig2.tight_layout()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--speed-pu", type=float, default=1.0, help="speed / wmBase")
    parser.add_argument("--torque-pu", type=float, default=0.8, help="torque / TBase")
    parser.add_argument("--variation", type=float, default=0.3, help="relative sweep span")
    parser.add_argument("--points", type=int, default=7, help="points per sweep")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    df, base = run_sensitivity(args.speed_pu, args.torque_pu, args.variation, args.points)
    xlsx_path = RESULTS_DIR / "sensitivity_results.xlsx"
    with pd.ExcelWriter(xlsx_path) as writer:
        df.to_excel(writer, sheet_name="sweeps", index=False)
        pd.DataFrame(
            {
                "quantity": ["speed_pu", "torque_pu", "variation", "points"]
                + ["nominal_eff_2l_pct", "nominal_eff_bimmc_pct"],
                "value": [args.speed_pu, args.torque_pu, args.variation, args.points]
                + list(base),
            }
        ).to_excel(writer, sheet_name="setup", index=False)
    print(f"Results saved in {xlsx_path.resolve()}")
    plot_results(df, base, args.speed_pu, args.torque_pu)
    plt.show()


if __name__ == "__main__":
    main()
