"""Generate the figures and key numbers for the PCIM synopsis.

Runs the same model as python/main.py (default dashboard inputs) without
Streamlit and writes vector figures plus a JSON file with the reported numbers.

Usage (from the repository root):
    python/venv/bin/python doc/figures/make_figures.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import calc as daf  # noqa: E402

OUT = Path(__file__).resolve().parent
DATA = ROOT / "python" / "data"

# ----------------------------------------------------------------------------
# default dashboard inputs (python/main.py)
pp, PBase, wmBase, Vdc = 4, 400e3, 3000.0, 700.0
rs_pu, ld_pu, lq_pu = 0.01, 0.55, 0.85
fsw_2l, Rdson_2l, ImosRated = 10e3, 4.6e-3, 320 * np.sqrt(2)
Rth_jc_2l, Rth_ca_2l, Tamb = 0.08, 0.05, 25.0
chem, Ebatt, Qcell = "NMC", 400e3, 24.0
R0_nom, R1_nom = 1.2e-3, 0.7e-3
C1_nom = 1 / (2 * np.pi * 250 * R1_nom)
Nsm, r_red, Rdson_b, Imax_b = 12, 0.0, 0.3e-3, 400.0
slopes_b = daf.SwitchingSlopes(1.0, 1.0, 0.5, 0.5)
mf_b, Rth_jc_b, Rth_ca_b = 2, 0.5, 0.2

OCV = {
    "soc": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
    "NMC": [4.13, 4.03, 3.92, 3.83, 3.75, 3.70, 3.66, 3.63, 3.59, 3.53, 3.34],
}
poly_r = lambda s: 1.3 * s**2 - 1.3 * s + 1.3  # noqa: E731
poly_c = lambda s: -1.3 * s**2 + 1.3 * s + 1.3  # noqa: E731

# derived machine quantities
VBase = Vdc / 2
VMax = VBase * 2 / np.sqrt(3)
wb = wmBase * 2 * np.pi / 60
TBase = PBase / wb
psi_f = VBase / (wb * pp)
ZBase = (VBase / np.sqrt(2) * np.sqrt(3)) ** 2 / PBase
Ibase = np.ceil(2 * PBase / (3 * VBase) / 50) * 50
Rs, Ld, Lq = rs_pu * ZBase, ld_pu * ZBase / (wb * pp), lq_pu * ZBase / (wb * pp)
wmMax = VMax / (psi_f - Ld * Ibase) / pp * 60 / (2 * np.pi)

Vnom = OCV[chem][OCV["soc"].index(0.5)]
Ns_2l = int(np.ceil(2 * VBase / Vnom))
Np_2l = int(np.ceil(Ebatt / (Qcell * Vnom * Ns_2l)))
Npmos_2l = np.ceil(Ibase / ImosRated)
Ns_b = int(np.ceil(2 * VBase / np.sqrt(3) / (Vnom * Nsm)))
Np_b = int(np.ceil(Ebatt / (3 * Nsm * Vnom * Ns_b * Qcell)))
Npmos_b = max(int(np.ceil(Ibase / (Imax_b * np.sqrt(2)))), 4)

raw = pd.read_csv(DATA / "Wolfspeed_MOSFET_dvdt_didt_data.csv")


def _slope(name):
    return interp1d(
        raw[f"{name}_X"], raw[f"{name}_Y"], bounds_error=False,
        fill_value=(raw[f"{name}_Y"].iloc[0], raw[f"{name}_Y"].iloc[-1]),
    )


slopes_2l = daf.SwitchingSlopes(*[_slope(k) for k in ("didt_on", "didt_off", "dvdt_on", "dvdt_off")])

wm_vec = np.linspace(0, wmMax, 50)
T_vec = np.linspace(-TBase, TBase, 100)
Pout = wm_vec[:, None] * T_vec[None, :] * 2 * np.pi / 60


def run(soc):
    Vcell = OCV[chem][OCV["soc"].index(soc)]
    motor = daf.MotorParameters(Rs, Ld, Lq, psi_f, pp)
    opti, x, (Tr, wr_p, vmax) = daf.create_mtpa_optimization_problem(motor)
    V_dc = Vcell * Ns_2l / 2
    opti.set_value(vmax, V_dc * 2 / np.sqrt(3))
    Id = np.full((len(wm_vec), len(T_vec)), np.nan)
    Iq = Id.copy()
    for i, wm in enumerate(wm_vec):
        for j, T in enumerate(T_vec):
            if abs(T * wm * 2 * np.pi / 60) > PBase:
                continue
            opti.set_value(Tr, T)
            opti.set_value(wr_p, wm * 2 * np.pi / 60)
            try:
                sol = opti.solve()
            except RuntimeError:
                opti.set_initial(x, 0)
                continue
            Id[i, j], Iq[i, j] = sol.value(x[0]), sol.value(x[1])
            opti.set_initial(x, sol.value(x))
    oc = Id**2 + Iq**2 > Ibase**2
    Id[oc] = np.nan
    Iq[oc] = np.nan
    we = wm_vec[:, None] * pp * 2 * np.pi / 60
    Vd = Id * Rs - we * Lq * Iq
    Vq = Iq * Rs + we * (psi_f + Ld * Id)
    R0, R1, C1 = R0_nom * poly_r(soc), R1_nom * poly_r(soc), C1_nom * poly_c(soc)

    l2 = daf.calc_losses_2l(Id, Iq, Vd, Vq, daf.TwoLevelLossConfig(
        2 * V_dc, Rdson_2l, Npmos_2l, fsw_2l,
        daf.BatteryParameters(R0, R1, C1, Ns_2l, Np_2l),
        daf.ThermalParameters(Tamb, Rth_jc_2l, Rth_ca_2l), slopes_2l))
    fsw_b = mf_b * np.meshgrid(wm_vec / 60 * pp, T_vec, indexing="ij")[0]
    lb = daf.calc_losses_bimmc(Id, Iq, Vd, Vq, wm_vec * 2 * np.pi / 60, T_vec, daf.BimmcLossConfig(
        Nsm, r_red, Vcell * Ns_b, Rdson_b, Npmos_b, fsw_b,
        daf.ThermalParameters(Tamb, Rth_jc_b, Rth_ca_b),
        daf.BatteryParameters(R0, R1, C1, Ns_b, Np_b), pp, slopes_b))

    res = {}
    for name, (Pc, Ps, Pb, Tj, Tc) in (("2l", l2), ("bimmc", lb)):
        Ptot = Pc + Ps + Pb
        with np.errstate(invalid="ignore", divide="ignore"):
            eta = Pout / (Pout + np.sign(Pout) * Ptot)
        res[name] = dict(Pc=Pc, Ps=Ps, Pb=Pb, Ptot=Ptot, eta=eta, Tj=Tj)
    return res


def nearest(wm_rpm, T):
    return int(np.argmin(abs(wm_vec - wm_rpm))), int(np.argmin(abs(T_vec - T)))


# operating points (speed [rpm], torque [Nm]) used in the synopsis
POINTS = {
    "A (low speed, low torque)": (0.25 * wmBase, 0.2 * TBase),
    "B (base speed, rated torque)": (wmBase, 0.8 * TBase),
    "C (high speed, part load)": (2 * wmBase, 0.3 * TBase),
}

SOCS = [0.1, 0.5, 0.9]
results = {soc: run(soc) for soc in SOCS}
r50 = results[0.5]

# ----------------------------------------------------------------------------
# numbers for the text
mot = Pout > 0
summary = {
    "derived": dict(TBase=TBase, Ibase=Ibase, wmMax=wmMax, Ns_2l=Ns_2l, Np_2l=Np_2l,
                    Npmos_2l=Npmos_2l, Ns_b=Ns_b, Np_b=Np_b, Npmos_b=Npmos_b,
                    Rs_mohm=Rs * 1e3, Ld_uH=Ld * 1e6, Lq_uH=Lq * 1e6, psi_mWb=psi_f * 1e3),
    "soc": {},
}
for soc in SOCS:
    r = results[soc]
    e2, eb = r["2l"]["eta"], r["bimmc"]["eta"]
    valid = mot & np.isfinite(e2) & np.isfinite(eb)
    d = {
        "eta_max_2l": np.nanmax(e2[mot]), "eta_max_bimmc": np.nanmax(eb[mot]),
        "eta_mean_2l": np.mean(e2[valid]), "eta_mean_bimmc": np.mean(eb[valid]),
        "frac_bimmc_better": np.mean(eb[valid] > e2[valid]),
        "deta_max_pp": np.max(eb[valid] - e2[valid]) * 100,
        "deta_min_pp": np.min(eb[valid] - e2[valid]) * 100,
        "deta_p95_pp": np.percentile(eb[valid] - e2[valid], 95) * 100,
        "deta_p05_pp": np.percentile(eb[valid] - e2[valid], 5) * 100,
        "Tj_max_2l": np.nanmax(r["2l"]["Tj"]), "Tj_max_bimmc": np.nanmax(r["bimmc"]["Tj"]),
        "points": {},
    }
    for k, (w, T) in POINTS.items():
        i, j = nearest(w, T)
        d["points"][k] = {
            "wm": wm_vec[i], "T": T_vec[j], "Pout_kW": Pout[i, j] / 1e3,
            **{f"{c}_{n}": float(r[n][c][i, j]) for n in ("2l", "bimmc") for c in ("Pc", "Ps", "Pb", "Ptot", "eta")},
        }
    summary["soc"][soc] = d
(OUT / "synopsis_numbers.json").write_text(json.dumps(summary, indent=2, default=float))

# ----------------------------------------------------------------------------
# figures
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})
W = 17.6 / 2.54  # text width [in]
Tmax = np.minimum(PBase / np.maximum(wm_vec * 2 * np.pi / 60, 1e-9), TBase)


def _map(ax, Z, levels, cmap, title, fmt="%.1f", nlines=6):
    Zm = np.where(mot, Z, np.nan).T
    cf = ax.contourf(wm_vec / 1e3, T_vec, Zm, levels=levels, cmap=cmap, extend="both")
    cl = ax.contour(wm_vec / 1e3, T_vec, Zm, levels=nlines, colors="k", linewidths=0.4)
    ax.clabel(cl, inline=True, fontsize=6, fmt=fmt)
    ax.plot(wm_vec / 1e3, Tmax, "k--", lw=0.8)
    ax.set_ylim(0, TBase * 1.03)
    ax.set_xlabel(r"$\omega_\mathrm{m}$ [krpm]")
    ax.set_title(title, loc="left")
    return cf


fig, ax = plt.subplots(1, 3, figsize=(W, 1.9), sharey=True, layout="constrained")
lv = np.linspace(90, 100, 41)
cf = _map(ax[0], r50["2l"]["eta"] * 100, lv, "viridis", r"(a) $\eta$, 2L inverter [%]", nlines=[96, 97, 98, 99])
_map(ax[1], r50["bimmc"]["eta"] * 100, lv, "viridis", r"(b) $\eta$, BI-MMC [%]", nlines=[96, 97, 98, 99])
fig.colorbar(cf, ax=ax[:2], shrink=0.9, pad=0.01, ticks=[90, 92, 94, 96, 98, 100])
deta = (r50["bimmc"]["eta"] - r50["2l"]["eta"]) * 100
lim = 3.0
cf2 = _map(ax[2], deta, np.linspace(-lim, lim, 41), "RdBu",
           r"(c) $\Delta\eta$ = BI-MMC $-$ 2L [pp]", fmt="%.1f", nlines=[-2, -1, -0.5, 0, 0.5, 1, 2])
fig.colorbar(cf2, ax=ax[2], shrink=0.9, pad=0.01, ticks=[-3, -2, -1, 0, 1, 2, 3])
ax[0].set_ylabel(r"$\tau_\mathrm{e}$ [Nm]")
for a, (k, (w, T)) in zip("ABC", POINTS.items()):
    for axx in ax:
        axx.plot(w / 1e3, T, "o", ms=3, mfc="w", mec="k", mew=0.6)
        axx.annotate(a, (w / 1e3, T), xytext=(3, 2), textcoords="offset points", fontsize=7)
fig.savefig(OUT / "efficiency_maps_soc50.pdf")

# loss breakdown at the operating points (SOC 50 %) and SOC dependence
fig, ax = plt.subplots(1, 2, figsize=(W, 1.7), layout="constrained", width_ratios=[1.25, 1])
labels, x0 = [], 0
cols = {"Pc": "#4C72B0", "Ps": "#DD8452", "Pb": "#55A868"}
names = {"Pc": "conduction", "Ps": "switching", "Pb": "battery"}
for p, (k, (w, T)) in enumerate(POINTS.items()):
    i, j = nearest(w, T)
    for q, n in enumerate(("2l", "bimmc")):
        bottom = 0
        for c in ("Pc", "Ps", "Pb"):
            v = r50[n][c][i, j] / 1e3
            ax[0].bar(x0, v, bottom=bottom, color=cols[c], width=0.7,
                      label=names[c] if (p == 0 and q == 0) else None)
            bottom += v
        labels.append(f"{k[0]}\n{'2L' if n == '2l' else 'BI-MMC'}")
        x0 += 1
    x0 += 0.5
xt = [0, 1, 2.5, 3.5, 5, 6]
ax[0].set_xticks(xt, labels)
ax[0].set_ylabel("Loss [kW]")
ax[0].legend(frameon=False, loc="upper left")
ax[0].set_title("(a) Loss breakdown, SOC = 50 %", loc="left")

for k, (w, T) in POINTS.items():
    i, j = nearest(w, T)
    d = [(results[s]["bimmc"]["eta"][i, j] - results[s]["2l"]["eta"][i, j]) * 100 for s in SOCS]
    ax[1].plot(np.array(SOCS) * 100, d, "o-", ms=3, label=f"point {k[0]}")
ax[1].axhline(0, color="k", lw=0.5)
ax[1].set_xlabel("SOC [%]")
ax[1].set_ylabel(r"$\Delta\eta$ (BI-MMC $-$ 2L) [pp]")
ax[1].set_ylim(-1.6, 1.3)
ax[1].legend(frameon=False, loc="lower right", ncols=3)
ax[1].set_title(r"(b) Efficiency difference vs. SOC", loc="left")
fig.savefig(OUT / "loss_breakdown_soc.pdf")

print(json.dumps(summary, indent=1, default=lambda v: round(float(v), 4)))
