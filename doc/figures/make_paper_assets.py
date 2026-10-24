"""Figures and LaTeX tables of the full paper (doc/PCIM_paper.tex).

Everything is generated from the cached results of the python package, so no number of
the paper is typed by hand:

    python/venv/bin/python python/cycle_eval.py            # results_cycles/*.json, *.csv
    python/venv/bin/python doc/figures/make_cycle_figures.py   # cycle_summary.pdf
    python/venv/bin/python doc/figures/make_paper_assets.py    # this script

Output: doc/figures/paper_*.pdf and doc/tables/*.tex.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy.signal import sawtooth  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import applications as apps  # noqa: E402
import calc as daf  # noqa: E402
import cycle_eval as ce  # noqa: E402
import cycles  # noqa: E402
import model  # noqa: E402

OUT = Path(__file__).resolve().parent
TAB = OUT.parent / "tables"
TAB.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})
W = 17.6 / 2.54
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
C2L, CBI, CGREEN = "#2a78d6", "#eb6834", "#1baf7a"
DIVERGING = LinearSegmentedColormap.from_list(
    "delta", ["#a33232", "#e34948", "#f0efec", "#2a78d6", "#104281"]
)
SHORT = {"car": "Passenger car", "bus": "City bus", "truck": "Heavy-duty truck",
         "offroad": "Off-road machine", "marine": "Marine vessel", "train": "Regional train"}
KEYS = list(apps.APPLICATIONS)
SOC_MAP = 0.5


def rows():
    return json.loads((ce.RESULTS_DIR / "cycle_results.json").read_text())


def results():
    return {(r["app"], r["soc_start"]): r for r in rows()}


def trace(key, soc=SOC_MAP):
    return pd.read_csv(ce.RESULTS_DIR / f"losses_{key}_soc{int(soc * 100):02d}.csv")


def write(name, text):
    """Table body without the final row terminator: the .tex adds `\\\\` after \\input, because a
    file ending in `\\\\` directly before \\bottomrule breaks the tabular (Misplaced \\noalign)."""
    text = text.rstrip()
    if text.endswith("\\\\"):
        text = text[:-2].rstrip()
    (TAB / name).write_text(text + "\n")


# ----------------------------------------------------------------------------- tables
def table_design():
    lines = []
    for key in KEYS:
        p = apps.APPLICATIONS[key]["params"]
        d = model.design(p)
        m = d.motor
        lines.append(
            f"{SHORT[key]} & {p['PBase'] / 1e3:.0f} & {p['wmBase']:.0f} & {p['Vdc']:.0f} & "
            f"{p['Ebatt'] / 1e3:.0f} & {d.TBase:.0f} & {d.Ibase:.0f} & "
            f"{d.wmMax * 60 / (2 * np.pi):.0f} & {m.magnet_flux * 1e3:.1f} & "
            f"{m.stator_resistance * 1e3:.2f} & {m.d_axis_inductance * 1e6:.0f} & "
            f"{m.q_axis_inductance * 1e6:.0f} \\\\"
        )
    write("design_machine.tex", "\n".join(lines) + "\n")

    lines = []
    for key in KEYS:
        p = apps.APPLICATIONS[key]["params"]
        d = model.design(p)
        lines.append(
            f"{SHORT[key]} & ${d.Nscells_2l}\\mathrm{{s}}{d.Npcells_2l}\\mathrm{{p}}$ & "
            f"{d.Npmos_2l} & ${d.Nsm}\\times{d.Nscells_b}$ & {d.Npcells_b:.2f} & {d.Npmos_b} & "
            f"{d.Nscells_2l * d.Npcells_2l} & {3 * d.Nsm * d.Nscells_b * d.Npcells_b:.0f} \\\\"
        )
    write("design_converters.tex", "\n".join(lines) + "\n")


def table_cycles():
    res = results()
    lines = []
    for key in KEYS:
        r = res[(key, SOC_MAP)]
        t = trace(key)
        d = model.design(apps.APPLICATIONS[key]["params"])
        dist = f"{r['distance_km']:.1f}" if r["distance_km"] else "--"
        gear = f"{r['gear_ratio']:.1f}" if r["gear_ratio"] else "--"
        lines.append(
            f"{SHORT[key]} & {r['cycle'].replace('-', '--')} & {r['duration_s'] / 60:.1f} & {dist} & {gear} & "
            f"{r['E_motoring_kWh']:.1f} & {r['E_regen_kWh']:.1f} & "
            f"{np.max(t['P']) / 1e3:.0f} & {np.min(t['P']) / 1e3:.0f} & "
            f"{r['share_below_base_speed'] * 100:.0f} & "
            f"{r['E_clipped_motoring_kWh']:.2f} & {r['E_clipped_regen_kWh']:.2f} \\\\"
        )
    write("cycles.tex", "\n".join(lines) + "\n")


def table_results():
    res = results()
    lines = []
    for key in KEYS:
        for soc in (0.2, 0.5, 0.9):
            r = res[(key, soc)]
            name = SHORT[key] if soc == 0.2 else ""
            lines.append(
                f"{name} & {soc * 100:.0f} & {r['E_Pc_2l_kWh']:.3f} & {r['E_Ps_2l_kWh']:.3f} & "
                f"{r['E_Pb_2l_kWh']:.3f} & {r['E_Pc_bimmc_kWh']:.3f} & {r['E_Ps_bimmc_kWh']:.3f} & "
                f"{r['E_Pb_bimmc_kWh']:.3f} & {r['eta_cycle_2l'] * 100:.2f} & "
                f"{r['eta_cycle_bimmc'] * 100:.2f} & {r['delta_eta_pp']:+.2f} \\\\"
            )
        if key != KEYS[-1]:
            lines.append("\\midrule")
    write("results_full.tex", "\n".join(lines) + "\n")

    lines = []
    for key in KEYS:
        r = res[(key, SOC_MAP)]
        semi2 = r["E_Pc_2l_kWh"] + r["E_Ps_2l_kWh"]
        semib = r["E_Pc_bimmc_kWh"] + r["E_Ps_bimmc_kWh"]
        kwh = (
            f"{r['kWh_per_100km_2l']:.1f} & {r['kWh_per_100km_bimmc']:.1f}"
            if r.get("kWh_per_100km_2l") else "-- & --"
        )
        lines.append(
            f"{SHORT[key]} & {(1 - semib / semi2) * 100:.0f} & "
            f"{r['E_Pb_bimmc_kWh'] / r['E_Pb_2l_kWh']:.1f} & {r['delta_loss_pct']:+.0f} & {kwh} & "
            f"{r['soc_end_2l'] * 100:.1f} & {r['soc_end_bimmc'] * 100:.1f} \\\\"
        )
    write("results_ratios.tex", "\n".join(lines) + "\n")

    lines = []
    for key in KEYS:
        r = res[(key, SOC_MAP)]
        lines.append(
            f"{SHORT[key]} & {r['Tj_max_2l']:.0f} & {r['Tj_max_bimmc']:.0f} & "
            f"{r['Tc_max_2l']:.0f} & {r['Tc_max_bimmc']:.0f} & "
            f"{r['Tcell_max_2l']:.1f} & {r['Tcell_max_bimmc']:.1f} \\\\"
        )
    write("results_temps.tex", "\n".join(lines) + "\n")


def table_vehicles():
    lines = []
    for key in KEYS:
        app = apps.APPLICATIONS[key]
        v = app["vehicle"]
        if v["type"] in ("road", "rail"):
            m = v["mass"] / 1e3
            cda = f"{v['CdA']:.2f}" if "CdA" in v else "Davis"
            crr = f"{v['Crr']:.4f}".rstrip("0") if "Crr" in v else "--"
            rw = f"{v['wheel_radius']:.2f}"
            ge = f"{v['gear_eff']:.2f}"
            gr = f"{apps.gear_ratio(app):.1f}"
            rot = f"{v['rot_mass_factor']:.2f}"
            lines.append(f"{SHORT[key]} & {m:.1f} & {rot} & {cda} & {crr} & {rw} & {ge} & {gr} \\\\")
        else:
            lines.append(f"{SHORT[key]} & \\multicolumn{{7}}{{c}}{{normalised / mode-based cycle, no vehicle model}} \\\\")
    write("vehicles.tex", "\n".join(lines) + "\n")


def table_maps():
    """Statistics of the efficiency maps (50 x 100 grid, 50 % SOC), common feasible points only."""
    lines = []
    for key in KEYS:
        d = model.design(apps.APPLICATIONS[key]["params"])
        m = ce.compute_maps(key, SOC_MAP, 50, 100)
        eta = {c: model.efficiency(m["Pout"], sum(m[f"{k}_{c}"] for k in ce.COMPONENTS)) for c in ce.CONVERTERS}
        ok = np.isfinite(eta["2l"]) & np.isfinite(eta["bimmc"]) & (np.abs(m["Pout"]) > 1e-6)
        dz = (eta["bimmc"] - eta["2l"]) * 100
        x = (m["wm"] / d.wmBase)[:, None] * np.ones_like(dz)
        # ignore the very-light-load strip (|T| < 2 % of base torque), where eta -> 0 trivially
        ok &= np.abs(m["T"] / d.TBase)[None, :] > 0.02
        below, above = ok & (x <= 1), ok & (x > 1)
        pos = lambda mask: np.mean(dz[mask] > 0) * 100 if mask.any() else np.nan  # noqa: E731
        avg = lambda mask: np.mean(dz[mask]) if mask.any() else np.nan  # noqa: E731
        lines.append(
            f"{SHORT[key]} & {np.nanmax(np.where(ok, eta['2l'], np.nan)) * 100:.2f} & "
            f"{np.nanmax(np.where(ok, eta['bimmc'], np.nan)) * 100:.2f} & "
            f"{pos(below):.0f} & {avg(below):+.2f} & {pos(above):.0f} & {avg(above):+.2f} & "
            f"{np.nanmax(dz[ok]):+.1f} & {np.nanmin(dz[ok]):+.1f} \\\\"
        )
    write("maps_stats.tex", "\n".join(lines) + "\n")


def table_energy_scaling():
    """Point efficiency at 0.5 pu speed, 0.6 pu torque, 50 % SOC versus installed energy.

    Both battery losses scale with 1/E_b at a fixed operating point (more parallel cells,
    lower cell resistance), so the C-rate P_b/E_b decides how much the cells weigh.
    """
    lines = []
    for key in ("car", "marine"):
        for scale in (0.5, 1.0, 2.0):
            p = dict(apps.APPLICATIONS[key]["params"])
            p["Ebatt"] *= scale
            d = model.design(p)
            m = model.loss_maps(p, SOC_MAP, [0.5 * d.wmBase], [0.6 * d.TBase])
            e = {c: model.efficiency(m["Pout"], sum(m[f"{k}_{c}"] for k in ce.COMPONENTS))[0, 0] * 100
                 for c in ce.CONVERTERS}
            name = SHORT[key] if scale == 0.5 else ""
            lines.append(
                f"{name} & {p['Ebatt'] / 1e3:.0f} & {p['PBase'] / p['Ebatt']:.2f} & "
                f"{m['Pb_2l'][0, 0]:.0f} & {m['Pb_bimmc'][0, 0]:.0f} & "
                f"{e['2l']:.2f} & {e['bimmc']:.2f} & {e['bimmc'] - e['2l']:+.2f} \\\\"
            )
        if key == "car":
            lines.append("\\midrule")
    write("energy_scaling.tex", "\n".join(lines) + "\n")


def table_etacyc():
    res = results()
    lines = []
    for key in KEYS:
        r = res[(key, SOC_MAP)]
        ds = [res[(key, s)]["delta_eta_pp"] for s in (0.2, 0.5, 0.9)]
        lines.append(
            f"{SHORT[key]} & {r['eta_cycle_2l'] * 100:.2f} & {r['eta_cycle_bimmc'] * 100:.2f} & "
            f"{r['delta_eta_pp']:+.2f} & [{min(ds):+.2f}, {max(ds):+.2f}] & "
            f"{r['Tj_max_2l']:.0f} & {r['Tj_max_bimmc']:.0f} & {r['Tc_max_2l']:.0f} & "
            f"{r['Tc_max_bimmc']:.0f} & {r['Tcell_max_2l']:.1f} & {r['Tcell_max_bimmc']:.1f} \\\\"
        )
    write("etacyc_temps.tex", "\n".join(lines) + "\n")


# ----------------------------------------------------------------------------- figures
def fig_pwm():
    """One electrical period of the BI-MMC submodule: reference, carrier, gating, currents."""
    p = apps.APPLICATIONS["car"]["params"]
    d = model.design(p)
    Vcell, R0, R1, C1 = model.cell_state(p, SOC_MAP)
    wm, T = 0.8 * d.wmBase, 0.6 * d.TBase
    vmax = Vcell * d.Nscells_b * d.Nsm
    Id, Iq = ce.mtpa_point(ce.make_mtpa_solver(d), d, wm, T, vmax)
    Vd, Vq = (float(x[0, 0]) for x in model.dq_voltages(d, np.array([[Id]]), np.array([[Iq]]), [wm]))
    pp = d.motor.pole_pairs
    we = wm * pp
    fsw = p["mf_bimmc"] * we / (2 * np.pi)
    ts = 1 / (fsw * 100)
    t_cycle = 2 * np.pi / we
    tvec = np.arange(0, 2 * t_cycle, ts)
    theta = we * tvec
    io = np.cos(theta) * Id - np.sin(theta) * Iq
    vref = (np.cos(theta) * Vd - np.sin(theta) * Vq) / (Vcell * d.Nscells_b * d.Nsm)
    vti = sawtooth(2 * np.pi * fsw * tvec, 0.5)
    g1 = (vref > vti).astype(float)
    g3 = (vref < -vti).astype(float)
    ib = io * g1 + (-io) * g3
    # equivalent single-cell circuit (same scaling as calc.calc_losses_bimmc)
    r0, r1, c1 = R0 * d.Nscells_b / d.Npcells_b, R1 * d.Nscells_b / d.Npcells_b, C1 * d.Npcells_b / d.Nscells_b
    Vc = np.zeros_like(tvec)
    for i in range(len(tvec) - 1):
        Vc[i + 1] = Vc[i] + (ib[i] - Vc[i] / r1) / c1 * (tvec[i + 1] - tvec[i])
    Pb = ib**2 * r0 + Vc**2 / r1
    sel = tvec >= t_cycle
    Pavg = Pb[sel][:-1].mean()  # as simulate_battery_loss (last sample has no step)
    t = (tvec - t_cycle) / t_cycle  # second period, 0..1
    fig, ax = plt.subplots(4, 1, figsize=(W, 5.2), sharex=True, layout="constrained")
    ax[0].plot(t[sel], vref[sel], color=C2L, label=r"$v_\mathrm{ref}$")
    ax[0].plot(t[sel], vti[sel], color=INK2, lw=0.6, label="carrier")
    ax[0].plot(t[sel], -vti[sel], color=INK2, lw=0.6, ls="--", label="$-$carrier")
    ax[0].set_ylabel("[pu]")
    ax[0].legend(ncols=3, frameon=False, loc="upper right")
    ax[1].step(t[sel], (g1 - g3)[sel], color=CBI, where="post")
    ax[1].set_ylabel(r"$s(t)=g_1-g_3$")
    ax[1].set_yticks([-1, 0, 1])
    ax[2].plot(t[sel], io[sel], color=INK2, lw=0.8, label=r"phase current $i_\mathrm{o}$")
    ax[2].plot(t[sel], ib[sel], color=CBI, lw=0.8, label=r"submodule current $i_\mathrm{b}$")
    ax[2].set_ylabel("[A]")
    ax[2].legend(ncols=2, frameon=False, loc="upper right")
    ax[3].plot(t[sel], Pb[sel], color=CGREEN, lw=0.8)
    ax[3].axhline(Pavg, color=INK, lw=0.6, ls="--")
    ax[3].text(0.01, Pavg, f"mean {Pavg:.1f} W", va="bottom", fontsize=7)
    ax[3].set_ylabel(r"$R_0 i_\mathrm{b}^2+v_C^2/R_1$ [W]")
    ax[3].set_xlabel(r"time over the second electrical period $t/T_\mathrm{e}$")
    ax[0].set_title(
        f"Passenger car, {wm * 60 / (2 * np.pi):.0f} rpm, {T:.0f} N$\\cdot$m, SOC {SOC_MAP:.0%}: "
        f"$f_\\mathrm{{e}}$ = {we / 2 / np.pi:.0f} Hz, $f_\\mathrm{{c}}$ = {fsw:.0f} Hz", loc="left")
    fig.savefig(OUT / "paper_pwm.pdf")
    plt.close(fig)
    # consistency check against the production function
    Pb_prod = daf.simulate_battery_loss(ib, tvec, r0, r1, c1, t_cycle)
    assert abs(Pb_prod - Pavg) / Pavg < 1e-6, (Pb_prod, Pavg)


def fig_traces(key):
    """Speed, torque, loss power, SOC and temperatures of one cycle at 50 % SOC."""
    t = trace(key)
    d = model.design(apps.APPLICATIONS[key]["params"])
    tt = t["t"].to_numpy() / 60
    rpm = 60 / (2 * np.pi)
    fig, ax = plt.subplots(5, 1, figsize=(W, 7.4), sharex=True, layout="constrained")
    ax[0].plot(tt, t["wm"] * rpm, color=INK, lw=0.7)
    ax[0].axhline(d.wmBase * rpm, color=INK2, lw=0.6, ls="--")
    ax[0].text(tt[-1], d.wmBase * rpm, " base speed", va="bottom", ha="right", fontsize=7, color=INK2)
    ax[0].set_ylabel("Speed [rpm]")
    ax[1].plot(tt, t["T_req"], color=INK2, lw=0.6, label="requested")
    ax[1].plot(tt, t["T"], color=INK, lw=0.7, label="delivered")
    ax[1].axhline(0, color=INK2, lw=0.4)
    ax[1].set_ylabel(r"Torque [N$\cdot$m]")
    ax[1].legend(frameon=False, ncols=2, loc="upper right")
    ax[2].plot(tt, t["Ploss_2l"] / 1e3, color=C2L, lw=0.7, label="2L")
    ax[2].plot(tt, t["Ploss_bimmc"] / 1e3, color=CBI, lw=0.7, label="BI-MMC")
    ax[2].set_ylabel("Total loss [kW]")
    ax[2].legend(frameon=False, ncols=2, loc="upper right")
    ax[3].plot(tt, t["Tj_2l"], color=C2L, lw=0.8, label=r"$T_\mathrm{j}$ 2L")
    ax[3].plot(tt, t["Tj_bimmc"], color=CBI, lw=0.8, label=r"$T_\mathrm{j}$ BI-MMC")
    ax[3].set_ylabel(r"Junction temp. [$^\circ$C]")
    ax[3].legend(frameon=False, ncols=2, loc="upper left")
    ax[4].plot(tt, t["soc_2l"] * 100, color=C2L, lw=0.8, label="2L")
    ax[4].plot(tt, t["soc_bimmc"] * 100, color=CBI, lw=0.8, ls="--", label="BI-MMC")
    ax[4].set_ylabel("SOC [%]")
    ax[4].set_xlabel("Time [min]")
    ax[4].legend(frameon=False, ncols=2, loc="upper right")
    fig.savefig(OUT / f"paper_trace_{key}.pdf")
    plt.close(fig)


def fig_loss_time_breakdown():
    """Cumulative loss energy of both drives along each cycle (50 % SOC)."""
    fig, axes = plt.subplots(2, 3, figsize=(W, 4.2), layout="constrained")
    for ax, key in zip(axes.ravel(), KEYS):
        t = trace(key)
        tt = np.cumsum(t["dt"].to_numpy()) / 60
        for conv, col, lab in (("2l", C2L, "2L"), ("bimmc", CBI, "BI-MMC")):
            for comp, ls in (("Pc", "-"), ("Ps", ":"), ("Pb", "--")):
                e = np.cumsum(t[f"{comp}_{conv}"].to_numpy() * t["dt"].to_numpy()) / 3.6e6
                ax.plot(tt, e, color=col, ls=ls, lw=1.0)
        ax.set_title(SHORT[key], loc="left")
        ax.set_xlabel("Time [min]")
        ax.set_ylabel("Loss energy [kWh]")
    h = [plt.Line2D([], [], color=C2L), plt.Line2D([], [], color=CBI),
         plt.Line2D([], [], color=INK, ls="-"), plt.Line2D([], [], color=INK, ls=":"),
         plt.Line2D([], [], color=INK, ls="--")]
    fig.legend(h, ["2L", "BI-MMC", "conduction", "switching", "battery"], ncols=5,
               frameon=False, loc="outside lower center")
    fig.savefig(OUT / "paper_loss_energy.pdf")
    plt.close(fig)


def fig_soc_bars():
    """Cycle efficiency of both drives and the difference at 20/50/90 % SOC."""
    res = results()
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.4), layout="constrained", width_ratios=[1.3, 1])
    x = np.arange(len(KEYS))
    for j, (soc, al) in enumerate(((0.2, 0.45), (0.5, 0.7), (0.9, 1.0))):
        a.bar(x + (j - 1) * 0.26, [res[(k, soc)]["delta_eta_pp"] for k in KEYS], 0.26,
              color=INK, alpha=al, label=f"SOC {soc:.0%}")
    a.axhline(0, color=INK2, lw=0.6)
    a.set_xticks(x, [SHORT[k].replace(" ", "\n", 1) for k in KEYS], fontsize=6.5)
    a.set_ylabel(r"$\Delta\eta_\mathrm{cycle}$ BI-MMC $-$ 2L [pp]")
    a.legend(frameon=False, ncols=3, loc="lower left")
    for k_i, k in enumerate(KEYS):
        b.plot([0.2, 0.5, 0.9], [res[(k, s)]["delta_eta_pp"] for s in (0.2, 0.5, 0.9)], "o-", ms=3, lw=0.9,
               label=SHORT[k])
    b.axhline(0, color=INK2, lw=0.6)
    b.set_xlabel("Initial SOC")
    b.set_ylabel(r"$\Delta\eta_\mathrm{cycle}$ [pp]")
    b.legend(frameon=False, fontsize=6, ncols=1, loc="center right")
    fig.savefig(OUT / "paper_soc.pdf")
    plt.close(fig)


def _maps(key):
    return key, ce.compute_maps(key, SOC_MAP, 50, 100)


def fig_delta_maps():
    """Efficiency difference BI-MMC - 2L over the map with the cycle energy of every application."""
    with ProcessPoolExecutor(max_workers=6) as pool:
        all_maps = dict(pool.map(_maps, KEYS))
    res = results()
    fig, axes = plt.subplots(2, 3, figsize=(W, 4.6), layout="constrained")
    levels = np.linspace(-4, 4, 17)
    for ax, key in zip(axes.ravel(), KEYS):
        d = model.design(apps.APPLICATIONS[key]["params"])
        maps = all_maps[key]
        eta = {c: model.efficiency(maps["Pout"], sum(maps[f"{k}_{c}"] for k in ce.COMPONENTS))
               for c in ce.CONVERTERS}
        dz = (eta["bimmc"] - eta["2l"]) * 100
        x, y = maps["wm"] / d.wmBase, maps["T"] / d.TBase
        cf = ax.contourf(x, y, dz.T, levels=levels, cmap=DIVERGING, extend="both")
        ax.contour(x, y, dz.T, levels=[0], colors=INK, linewidths=0.8)
        t = trace(key)
        e = np.abs(t["wm"] * t["T"]) * t["dt"]
        H, xe, ye = np.histogram2d(t["wm"] / d.wmBase, t["T"] / d.TBase,
                                   bins=(np.linspace(0, x[-1], 19), np.linspace(-1, 1, 17)), weights=e)
        xc, yc = np.meshgrid((xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2, indexing="ij")
        share = H / H.sum()
        keep = share > 0.002
        ax.scatter(xc[keep], yc[keep], s=900 * share[keep], facecolor=INK, edgecolor=SURFACE, linewidth=0.5)
        ax.set_title(f"{SHORT[key]}: {res[(key, SOC_MAP)]['delta_eta_pp']:+.2f} pp", loc="left")
        ax.set_xlabel(r"$\omega_\mathrm{m}/\omega_\mathrm{b}$ [pu]")
        ax.set_ylabel(r"$T/T_\mathrm{b}$ [pu]")
    cb = fig.colorbar(cf, ax=axes, shrink=0.8, ticks=[-4, -2, 0, 2, 4])
    cb.set_label(r"$\eta_\mathrm{BI\text{-}MMC}-\eta_\mathrm{2L}$ [pp]")
    fig.savefig(OUT / "paper_delta_maps.pdf")
    plt.close(fig)


def fig_profiles():
    """Speed profiles of the six duty cycles (wheel speed or machine speed in pu)."""
    fig, axes = plt.subplots(2, 3, figsize=(W, 3.8), layout="constrained")
    for ax, key in zip(axes.ravel(), KEYS):
        prof = cycles.machine_profile(apps.APPLICATIONS[key])
        d = model.design(apps.APPLICATIONS[key]["params"])
        if key == "marine":
            t = np.cumsum(prof["dt"]) / 60
            ax.bar(t - prof["dt"] / 120, prof["wm"] / d.wmBase, width=prof["dt"] / 60, color=INK, alpha=0.8)
            ax.set_ylim(0, 1.1)
        else:
            tt = (prof["t"] if key != "offroad" else prof["t"]) / 60
            ax.plot(tt, prof["wm"] / d.wmBase, color=INK, lw=0.6)
        ax.axhline(1, color=INK2, lw=0.5, ls="--")
        ax.set_title(SHORT[key], loc="left")
        ax.set_xlabel("Time [min]")
        ax.set_ylabel(r"$\omega_\mathrm{m}/\omega_\mathrm{b}$ [pu]")
    fig.savefig(OUT / "paper_profiles.pdf")
    plt.close(fig)


if __name__ == "__main__":
    table_design()
    table_cycles()
    table_results()
    table_vehicles()
    table_etacyc()
    table_maps()
    table_energy_scaling()
    fig_pwm()
    fig_soc_bars()
    fig_loss_time_breakdown()
    for k in KEYS:
        fig_traces(k)
    fig_profiles()
    fig_delta_maps()
    print("assets written to", OUT, "and", TAB)
