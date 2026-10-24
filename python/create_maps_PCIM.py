"""MTPA, loss, temperature and efficiency maps of the 2L inverter and the BI-MMC for each
application of ``applications.py`` (PCIM figures).

    python create_maps_PCIM.py [--apps car bus ...] [--soc 0.5] [--out results_PCIM] [--no-xlsx]

For every application the drive parameters (PBase, wmBase, Vdc, Ebatt, ...) are taken from
``applications.APPLICATIONS`` and the maps are computed exactly as in the dashboard
(``main.py``): both converters use the 2L voltage limit, a constant Rdson. The figures of ``plots.py`` are saved as PNG (and the plotted data as one
.xlsx workbook) in ``<out>/<application>/``.
"""

import argparse
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # figures are only saved, never shown

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import applications as apps
import export as exporter
import model
import plots as dpf

# same settings as the dashboard (main.py)
EFF_MIN = 0.9  # efficiency values below this threshold are not plotted
VOLTAGE_LIMIT = "2l"
RDSON_TJ = False
RPM_PER_RADS = 60 / (2 * np.pi)
DEFAULT_OUT = Path("results_PCIM")


def efficiency_maps(Pout, Pc, Ps, Pb):
    """Efficiency of each loss component and in total; points below EFF_MIN are NaN
    (same as ``efficiency_maps`` in main.py)."""
    total = model.efficiency(Pout, Pc + Ps + Pb)
    parts = [model.efficiency(Pout, P) for P in (Pc, Ps, Pb)]
    with np.errstate(invalid="ignore"):
        low = total < EFF_MIN
    for eff in (*parts, total):
        eff[low] = np.nan
    return (*parts, total)


def application_params(app_key):
    """Dashboard parameters of an application (model.NOMINAL + the application overrides)."""
    p = dict(apps.APPLICATIONS[app_key]["params"])
    return p


def create_maps(app_key, soc=0.5, out_dir=DEFAULT_OUT, xlsx=True):
    """Compute the maps of one application and save the figures; returns the output folder."""
    app = apps.APPLICATIONS[app_key]
    p = application_params(app_key)
    d = model.design(p)
    folder = Path(out_dir) / app_key
    folder.mkdir(parents=True, exist_ok=True)
    soc_tag = f"soc_{int(round(soc * 100)):02d}"
    Vcell = float(model.cell_state(p, soc)[0])

    wm_vec, T_vec = model.default_grid(p)  # [rad/s], [N.m]
    res = model.loss_maps(
        p, soc, wm_vec, T_vec, voltage_limit=VOLTAGE_LIMIT, rdson_tj=RDSON_TJ
    )
    Id, Iq = res["Id_2l"], res["Iq_2l"]
    Vd, Vq = model.dq_voltages(d, Id, Iq, wm_vec)
    Pout = res["Pout"]
    operating_map = dpf.OperatingMap(wm_vec * RPM_PER_RADS, T_vec, p["PBase"], d.TBase)

    converters = {
        key: {
            "Pc": res[f"Pc_{key}"],
            "Ps": res[f"Ps_{key}"],
            "Pb": res[f"Pb_{key}"],
            "Tj": res[f"Tj_{key}"],
            "Tc": res[f"Tc_{key}"],
            "Tcell": res[f"Tcell_{key}"],
        }
        for key in ("2l", "bimmc")
    }
    for conv in converters.values():
        conv["Ploss"] = conv["Pc"] + conv["Ps"] + conv["Pb"]
        conv["eff"] = efficiency_maps(Pout, conv["Pc"], conv["Ps"], conv["Pb"])

    def options(fig_no, name):
        return dpf.PlotOptions(
            figure_number=fig_no, save_path=folder / f"{name}_{soc_tag}.png"
        )

    # --- MTPA maps
    mtpa = dpf.MtpaMapData(
        Id, Iq, Vd, Vq, operating_map, Vcell * d.Nscells_2l / 2, d.Ibase, soc
    )
    dpf.plot_mtpa_maps(mtpa, options(10, "mtpa_maps"))
    dpf.plot_mtpa_maps_dqs(mtpa, options(11, "mtpa_maps_dqs"))

    # --- loss, temperature and efficiency maps of each converter
    for key, fig_no in (("2l", 20), ("bimmc", 30)):
        conv = converters[key]
        dpf.plot_losses(
            dpf.LossMapData(
                conv["Pc"] / 1e3, conv["Ps"] / 1e3, conv["Pb"] / 1e3, operating_map
            ),
            options(fig_no, f"losses_maps_{key}"),
        )
        dpf.plot_Tc_and_Tj(
            dpf.TemperatureMapData(conv["Tj"], conv["Tc"], operating_map, conv["Tcell"]),
            options(fig_no + 1, f"temperature_maps_{key}"),
        )
        eff_c, eff_s, eff_b, _ = conv["eff"]
        dpf.plot_efficiency(
            dpf.EfficiencyMapData(eff_c * 100, eff_s * 100, eff_b * 100, operating_map),
            options(fig_no + 2, f"efficiency_maps_{key}"),
        )

    # --- comparison of the two converters (blue = BI-MMC better)
    c2l, cb = converters["2l"], converters["bimmc"]
    dpf.plot_total_loss_comparison(
        dpf.TotalLossMapData_comparison(
            c2l["Ploss"], c2l["eff"][3], r"2L", cb["Ploss"], cb["eff"][3], r"BI-MMC",
            operating_map,
        ),
        options(40, "losses_maps_comparison"),
    )
    dpf.plot_total_efficiency_comparison(
        dpf.TotalLossMapData_comparison(
            c2l["Ploss"], c2l["eff"][3], r"2L", cb["Ploss"], cb["eff"][3], r"BI-MMC",
            operating_map,
        ),
        options(41, "efficiency_maps_comparison"),
    )
    dpf.plot_individual_loss_comparison(
        dpf.IndividualLossMapData_comparison(
            c2l["Pc"], c2l["Ps"], c2l["Pb"], r"2L",
            cb["Pc"], cb["Ps"], cb["Pb"], r"BI-MMC",
            operating_map,
        ),
        options(42, "individual_losses_maps_comparison"),
    )
    dpf.plot_individual_loss_comparison(
        dpf.IndividualLossMapData_comparison(
            *c2l["eff"][:3], r"2L", *cb["eff"][:3], r"BI-MMC", operating_map,
            quantity="efficiency",
        ),
        options(43, "individual_efficiency_maps_comparison"),
    )
    plt.close("all")

    if xlsx:
        info = {
            k: p[k]
            for k in ("PBase", "wmBase", "Vdc", "Ebatt", "Qcell", "chemistry", "pp", "fsw")
        }
        info.update(
            {
                "application": app["label"],
                "soc": soc,
                "Vcell_V": Vcell,
                "Nscells_2l": d.Nscells_2l,
                "Npcells_2l": d.Npcells_2l,
                "Nsm": d.Nsm,
                "Nscells_bimmc": d.Nscells_b,
                "Npcells_bimmc": d.Npcells_b,
                "Npmos_2l": d.Npmos_2l,
                "Npmos_bimmc": d.Npmos_b,
                "TBase_Nm": d.TBase,
                "Ibase_A": d.Ibase,
            }
        )
        sheets = {
            "Parameters": pd.DataFrame(
                {"parameter": list(info), "value": list(info.values())}
            ),
            **exporter.mtpa_frames(mtpa),
            **exporter.converter_frames("2l", c2l, operating_map),
            **exporter.converter_frames("bimmc", cb, operating_map),
            **exporter.comparison_frames(c2l, cb, operating_map),
        }
        exporter.write_workbook(
            folder
            / f"plot_data_{app_key}_{soc_tag}_PBase_{p['PBase'] / 1e3:.0f}kW"
            f"_Ebatt_{p['Ebatt'] / 1e3:.0f}kWh.xlsx",
            sheets,
        )
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--apps", nargs="+", default=list(apps.APPLICATIONS), choices=list(apps.APPLICATIONS)
    )
    parser.add_argument("--soc", type=float, default=0.5)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-xlsx", action="store_true", help="skip the Excel export")
    args = parser.parse_args()

    for app_key in args.apps:
        p = application_params(app_key)
        print(
            f"{app_key}: PBase {p['PBase'] / 1e3:.0f} kW, wmBase {p['wmBase']:.0f} rpm, "
            f"Vdc {p['Vdc']:.0f} V, Ebatt {p['Ebatt'] / 1e3:.0f} kWh",
            flush=True,
        )
        t0 = time.perf_counter()
        folder = create_maps(app_key, args.soc, args.out, xlsx=not args.no_xlsx)
        print(f"  saved to {folder} ({time.perf_counter() - t0:.1f} s)", flush=True)


if __name__ == "__main__":
    main()
