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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import model
from model import NOMINAL

RESULTS_DIR = Path("results_sens")

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
    "Nscells_b",
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
INTEGER_PARAMS = {"Nscells_b", "mf_bimmc", "pp"}
# Parameters that can't be scaled multiplicatively (nominal value of zero) use an absolute span
ABSOLUTE_SPAN = {"Nsm_redundant_pu": (0.0, 0.2), "soc": (0.1, 1.0)}
# Custom-MOSFET-only parameters are swept only when mosfet == "custom"
CUSTOM_ONLY = {"didt_on_2l", "didt_off_2l", "dvdt_on_2l", "dvdt_off_2l"}


def evaluate(p, speed_pu=1.0, torque_pu=1.0):
    """Total efficiency [-] of the two-level inverter and the BI-MMC at one operating point."""
    d = model.design(p)
    maps = model.loss_maps(
        p, p["soc"], [speed_pu * d.wmBase], [torque_pu * d.TBase]
    )
    return tuple(
        model.efficiency(
            maps["Pout"], maps[f"Pc_{c}"] + maps[f"Ps_{c}"] + maps[f"Pb_{c}"]
        ).item()
        for c in ("2l", "bimmc")
    )



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
