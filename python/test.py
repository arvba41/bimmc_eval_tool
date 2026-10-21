# %%
import cycle_eval as ce
import applications as apps
import cycles
import model
import numpy as np
import matplotlib.pyplot as plt

# %%
app_key = "car"  # "car", "bus", "truck", "offroad"
res, trace = ce.evaluate_cycle(app_key, soc0=0.8)

# %% print the results of the cycle: general, per converter (2L | BI-MMC) and temperatures
import pandas as pd

per_conv = {}
for k, v in res.items():
    for c in ce.CONVERTERS:
        if k.endswith(f"_{c}") or f"_{c}_" in k:
            per_conv.setdefault(k.replace(f"_{c}", ""), {})[c] = v
general = {k: v for k, v in res.items() if not any(f"_{c}" in k for c in ce.CONVERTERS)}
print(f"--- {app_key}: cycle results ---")
print(pd.Series(general).to_string())
print("\n--- per converter ---")
print(
    pd.DataFrame(per_conv)
    .T[list(ce.CONVERTERS)]
    .to_string(float_format="{:.4g}".format)
)

# loss energy breakdown [kWh] of the two converters
fig0, ax0 = plt.subplots(figsize=(6, 4), num="loss_energy", clear=True)
labels = {"Pc": "conduction", "Ps": "switching", "Pb": "battery"}
x = np.arange(len(labels))
for i, c in enumerate(ce.CONVERTERS):
    ax0.bar(
        x + (i - 0.5) * 0.35, [res[f"E_{k}_{c}_kWh"] for k in labels], 0.35, label=c
    )
ax0.set_xticks(x, list(labels.values()))
ax0.set_ylabel("Loss energy [kWh]")
ax0.set_title(
    f"{app_key}: {res['cycle']}, eta 2L {res['eta_cycle_2l']:.4f} / BI-MMC {res['eta_cycle_bimmc']:.4f}"
)
ax0.legend()
fig0.tight_layout()

# %%
t = trace["t"]
app = apps.APPLICATIONS[app_key]
prof = cycles.machine_profile(app)
has_speed = app["vehicle"].get("wheel_radius") is not None
if has_speed:
    trace["v_kmh"] = (
        trace["wm"] / apps.gear_ratio(app) * app["vehicle"]["wheel_radius"] * 3.6
    )
    speed_panel = ("Speed [km/h]", [("v_kmh", "simulated")])
    # drive cycle speed (only defined for cycles that are specified in vehicle speed)
    v_cycle = prof["v"]
    if v_cycle is not None:
        trace["v_cycle_kmh"] = v_cycle * 3.6
        speed_panel[1].insert(0, ("v_cycle_kmh", "drive cycle"))
else:  # no vehicle (e.g. offroad): show the machine speed instead
    speed_panel = ("Speed [rad/s]", [("wm", "wm")])
panels = [
    speed_panel,
    ("Torque [Nm]", [("T_req", "requested"), ("T", "delivered")]),
    ("Power [W]", [("P", "P")]),
    ("SOC", [("soc_2l", "2L"), ("soc_bimmc", "BI-MMC")]),
    ("Loss [W]", [("Ploss_2l", "2L"), ("Ploss_bimmc", "BI-MMC")]),
    ("Tj [°C]", [("Tj_2l", "2L"), ("Tj_bimmc", "BI-MMC")]),
    ("Tc [°C]", [("Tc_2l", "2L"), ("Tc_bimmc", "BI-MMC")]),
    ("Tcell [°C]", [("Tcell_2l", "2L"), ("Tcell_bimmc", "BI-MMC")]),
]

fig, axs = plt.subplots(
    len(panels), 1, sharex=True, figsize=(10, 12), num="trace", clear=True
)
for ax, (ylabel, series) in zip(axs, panels):
    for col, label in series:
        ax.plot(t, trace[col], label=label)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    if len(series) > 1:
        ax.legend(loc="upper right")
if (
    "slope" in prof
):  # road slope as filled area on a secondary axis of the speed subplot
    ax_s = axs[0].twinx()
    ax_s.fill_between(
        t, np.tan(prof["slope"]) * 100, alpha=0.2, color="tab:gray", label="slope"
    )
    ax_s.set_ylabel("Road slope [%]")
    axs[0].set_zorder(ax_s.get_zorder() + 1)  # keep the speed lines in front
    axs[0].patch.set_visible(False)
axs[-1].set_xlabel("t [s]")
fig.tight_layout()
# plt.show()

# %% torque vs speed in pu (mechanical machine speed)
p = app["params"]
d = model.design(p)
wm_pu = trace["wm"] / d.wmBase
T_pu = trace["T"] / d.TBase

# max torque: base torque up to base speed, constant power (PBase / wm) above it
w_grid = np.linspace(0, d.wmMax, 500)
T_lim_pu = np.minimum(1.0, p["PBase"] / np.maximum(w_grid, 1e-9) / d.TBase)

fig2, ax = plt.subplots(figsize=(7, 5), num="torque_speed", clear=True)
ax.plot(
    trace["wm"] / d.wmBase,
    trace["T_req"] / d.TBase,
    ".",
    ms=3,
    alpha=0.3,
    label="requested",
)
ax.plot(wm_pu, T_pu, ".", ms=3, label="delivered")
ax.plot(w_grid / d.wmBase, T_lim_pu, "k--", label="limit (Pmax)")
ax.plot(w_grid / d.wmBase, -T_lim_pu, "k--")
ax.set_xlabel("Speed [pu]")
ax.set_ylabel("Torque [pu]")
ax.grid(True)
ax.legend()
fig2.tight_layout()
plt.show()

# %%
