"""Drive-cycle figures for the PCIM synopsis (Fig. 2 and Fig. 3) and their numbers.

Reads the cached loss maps and cycle results of python/cycle_eval.py (run it first):
    python/venv/bin/python python/cycle_eval.py
    python/venv/bin/python doc/figures/make_cycle_figures.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import applications as apps  # noqa: E402
import cycle_eval as ce  # noqa: E402
import model  # noqa: E402

OUT = Path(__file__).resolve().parent
SOC_MAP = 0.5
MAP_APPS = ("offroad", "truck")  # contrasting cases shown in Fig. 2
GRID = (50, 100)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})
W = 17.6 / 2.54  # text width [in]
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
# categorical slots 1-3 (conduction, switching, battery) of the reference palette
COMP_COLORS = {"Pc": "#2a78d6", "Ps": "#eb6834", "Pb": "#1baf7a"}
COMP_LABELS = {"Pc": "Conduction", "Ps": "Switching", "Pb": "Battery"}
# direct-label offsets in Fig. 3(b) (points, alignment) where labels would collide
LABEL_OFFSET = {"offroad": (0, 8, "center"), "marine": (-5, 0, "right")}
SHORT = {"car": "Car", "bus": "Bus", "truck": "Truck", "offroad": "Off-road",
         "marine": "Marine", "train": "Train"}
# diverging: red = 2L better, gray = equal, blue = BI-MMC better
DIVERGING = LinearSegmentedColormap.from_list(
    "delta", ["#a33232", "#e34948", "#f0efec", "#2a78d6", "#104281"]
)


def delta_eta_map(maps):
    """BI-MMC - 2L total efficiency [pp] on the map, NaN outside the common envelope."""
    eta = {
        c: model.efficiency(maps["Pout"], sum(maps[f"{k}_{c}"] for k in ce.COMPONENTS))
        for c in ce.CONVERTERS
    }
    return (eta["bimmc"] - eta["2l"]) * 100


def fig_maps(results):
    fig, axes = plt.subplots(1, len(MAP_APPS), figsize=(W, 1.6), sharey=True, layout="constrained")
    levels = np.linspace(-2, 2, 17)
    for ax, key in zip(axes, MAP_APPS):
        app = apps.APPLICATIONS[key]
        d = model.design(app["params"])
        maps = ce.compute_maps(key, SOC_MAP, *GRID)
        dz = delta_eta_map(maps)
        x = maps["wm"] / d.wmBase
        y = maps["T"] / d.TBase
        cf = ax.contourf(x, y, dz.T, levels=levels, cmap=DIVERGING, extend="both")
        ax.contour(x, y, dz.T, levels=[0], colors=INK, linewidths=0.8)

        # cycle energy |P| dt binned on a coarse (speed x torque) grid; area ~ energy share
        prof = pd.read_csv(ce.RESULTS_DIR / f"losses_{key}_soc{int(SOC_MAP * 100):02d}.csv")
        prof = {c: prof[c].to_numpy() for c in ("wm", "T", "dt")}  # delivered torque T
        e = np.abs(prof["wm"] * prof["T"]) * prof["dt"]
        H, xe, ye = np.histogram2d(
            prof["wm"] / d.wmBase, prof["T"] / d.TBase, bins=(np.linspace(0, x[-1], 19),
            np.linspace(-1, 1, 17)), weights=e,
        )
        xc, yc = np.meshgrid((xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2, indexing="ij")
        share = H / H.sum()
        keep = share > 0.002
        ax.scatter(xc[keep], yc[keep], s=1500 * share[keep], facecolor=INK,
                   edgecolor=SURFACE, linewidth=0.6)
        r = results[(key, SOC_MAP)]
        ax.set_title(f"{SHORT[key]} ({r['cycle']}): "
                     f"$\\Delta\\eta_\\mathrm{{cycle}}$ = {r['delta_eta_pp']:+.2f} pp", color=INK)
        ax.set_xlabel(r"Speed $\omega_\mathrm{m}/\omega_\mathrm{b}$ [pu]")
        ax.axhline(0, color=INK2, lw=0.4)
    axes[0].set_ylabel(r"Torque $T/T_\mathrm{b}$ [pu]")
    cb = fig.colorbar(cf, ax=axes, shrink=0.9, ticks=[-2, -1, 0, 1, 2])
    cb.set_label(r"$\eta_\mathrm{BI\text{-}MMC}-\eta_\mathrm{2L}$ [pp]")
    fig.savefig(OUT / "cycle_maps_soc50.pdf")
    plt.close(fig)


def fig_summary(results, keys):
    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(W, 1.7), layout="constrained", width_ratios=[1.5, 1]
    )

    # (a) cycle loss breakdown, % of traction energy throughput
    width, gap = 0.36, 0.04
    xt, xl = [], []
    for i, key in enumerate(keys):
        r = results[(key, SOC_MAP)]
        throughput = r["E_motoring_kWh"] + r["E_regen_kWh"]
        for j, (conv, tag) in enumerate((("2l", "2L"), ("bimmc", "BI"))):
            x = i + (j - 0.5) * (width + gap)
            bottom = 0.0
            for c in ce.COMPONENTS:
                h = r[f"E_{c}_{conv}_kWh"] / throughput * 100
                ax_a.bar(x, h, width, bottom=bottom, color=COMP_COLORS[c],
                         edgecolor=SURFACE, linewidth=1.0,
                         label=COMP_LABELS[c] if i == 0 and j == 0 else None)
                bottom += h
            xt.append(x)
            xl.append(tag)
    ax_a.set_xticks(xt, xl, fontsize=6)
    for i, key in enumerate(keys):
        ax_a.annotate(SHORT[key], (i, 0), xytext=(0, -12),
                      textcoords="offset points", ha="center", va="top", fontsize=7, color=INK)
    ax_a.set_ylabel("Cycle loss [% of energy]")
    ax_a.legend(frameon=False, ncols=3, loc="upper left")
    ax_a.tick_params(axis="x", length=0)

    # (b) cycle efficiency difference vs. share of energy below base speed
    for key in keys:
        rs = [results[(key, s)] for s in sorted({s for k, s in results if k == key})]
        x = results[(key, SOC_MAP)]["share_below_base_speed"] * 100
        y = [r["delta_eta_pp"] for r in rs]
        y_mid = results[(key, SOC_MAP)]["delta_eta_pp"]
        ax_b.errorbar(x, y_mid, yerr=[[y_mid - min(y)], [max(y) - y_mid]], fmt="o",
                      ms=4, color=INK, mec=SURFACE, mew=0.6, elinewidth=0.8, capsize=2)
        dx, dy, ha = LABEL_OFFSET.get(key, (5, 0, "left"))
        ax_b.annotate(SHORT[key], (x, y_mid), xytext=(dx, dy), textcoords="offset points",
                      fontsize=7, color=INK2, ha=ha, va="center")
    ax_b.axhline(0, color=INK2, lw=0.6, ls="--")
    ax_b.set_xlabel("Cycle energy below base speed [%]")
    ax_b.set_ylabel(r"$\Delta\eta_\mathrm{cycle}$ BI-MMC $-$ 2L [pp]")
    ax_b.set_xlim(0, 105)
    for ax, tag in ((ax_a, "(a)"), (ax_b, "(b)")):
        ax.set_title(tag, loc="left", color=INK)
    fig.savefig(OUT / "cycle_summary.pdf")
    plt.close(fig)


def main():
    rows = json.loads((ce.RESULTS_DIR / "cycle_results.json").read_text())
    results = {(r["app"], r["soc_start"]): r for r in rows}
    keys = [k for k in apps.APPLICATIONS if (k, SOC_MAP) in results]
    fig_maps(results)
    fig_summary(results, keys)
    (OUT / "cycle_numbers.json").write_text(json.dumps(rows, indent=2))
    print(f"Figures written to {OUT}")


if __name__ == "__main__":
    main()
