"""Headless loss model of the two-level (2L) inverter and the BI-MMC drive.

Shared by sens.py, cycle_eval.py and the synopsis figures (doc/figures). It uses the
same equations as the dashboard (main.py), plus two corrections that main.py does
not have yet:

- each converter gets its own voltage limit in the MTPA problem (the BI-MMC string
  voltage is Vs * Nsm * (1 - r), so with redundancy its envelope shrinks and the
  submodule reference never exceeds 1);
- the 2L conduction loss uses Rdson(Tj) from the datasheet, found by a fixed-point
  iteration Tj -> Rdson -> Pcond -> Tj.

Both are switched on by default and can be turned off (voltage_limit="2l",
rdson_tj=False) to reproduce the dashboard results.

Parameters are passed as a dict in the format of NOMINAL (user inputs).
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

import calc as daf

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
    "Tjmax_2l": 175.0,  # [°C]
    "Tcmax_2l": 100.0,  # [°C]
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
    "Nsm": 12,  # preferred number of submodules per phase (see "bimmc_sizing")
    "Nsm_redundant_pu": 0.0,
    # "match": submodules x cells per submodule chosen (near Nsm) so that the BI-MMC
    #          peak phase voltage matches the 2L inverter's (fair comparison);
    # "ceil":  exactly Nsm submodules, cells per submodule rounded up (dashboard)
    "bimmc_sizing": "match",
    "Rdson_bimmc": 0.3e-3,  # [Ohm]
    "Imax_mosfet": 400.0,  # [A]
    "didt_on_bimmc": 1.0,
    "didt_off_bimmc": 1.0,
    "dvdt_on_bimmc": 0.5,
    "dvdt_off_bimmc": 0.5,
    "mf_bimmc": 2,
    "Rth_jc_bimmc": 0.5,
    "Rth_ca_bimmc": 0.2,
    "Tjmax_bimmc": 175.0,  # [°C]
}


# default coefficients of the customised MOSFET: 3rd order fit of the Wolfspeed data [c3 .. c0]
RDSON_POLY_DEFAULT = (9.43462740e-12, 2.99523011e-05, 5.77104581e-04, 9.67661695e-01)


def _table_function(x, y):
    """Linear interpolation, held constant outside the data range."""
    return interp1d(
        x, y, kind="linear", bounds_error=False, fill_value=(y.iloc[0], y.iloc[-1])
    )


def rdson_poly_fun(coef, tj_range=None):
    """Rdson(Tj) / Rdson(25 °C) from 3rd order polynomial coefficients [c3, c2, c1, c0].

    The polynomial is normalised so that the datasheet Rdson holds at 25 °C. Tj is held
    at the limits of tj_range (fitted data range) when given.
    """
    coef = np.asarray(coef, dtype=float)
    ref = np.polyval(coef, 25.0)

    def fun(tj):
        tj = np.asarray(tj, dtype=float)
        if tj_range is not None:
            tj = np.clip(tj, *tj_range)
        return np.polyval(coef, tj) / ref

    return fun


def fit_rdson_poly(rdson_raw, degree=3):
    """Polynomial coefficients (highest power first) of the normalised Rdson vs Tj raw data."""
    return np.polyfit(rdson_raw["Tj"], rdson_raw["Rdson_normalized"], degree)


def mosfet_raw(p):
    """Raw switching-slope table and Rdson(Tj) table (None for a customised MOSFET)."""
    if p["mosfet"] == "Wolfspeed":
        return (
            pd.read_csv(DATA_DIR / "Wolfspeed_MOSFET_dvdt_didt_data.csv"),
            pd.read_csv(DATA_DIR / "Wolfspeed_MOSFET_Rdson_vs_Tj_data.csv"),
        )
    ImosRated = p["ImosRated_RMS"] * np.sqrt(2)
    raw = pd.DataFrame(
        {
            f"{k}_{ax}": ([0, ImosRated] if ax == "X" else [p[f"{k}_2l"]] * 2)
            for k in ("didt_on", "didt_off", "dvdt_on", "dvdt_off")
            for ax in ("X", "Y")
        }
    )
    return raw, None


def mosfet_data(p):
    """Switching slopes and normalised Rdson(Tj) function of the 2L MOSFET."""
    raw, rdson_raw = mosfet_raw(p)
    if rdson_raw is not None:
        rdson_tj = rdson_poly_fun(
            fit_rdson_poly(rdson_raw), (rdson_raw["Tj"].min(), rdson_raw["Tj"].max())
        )
    else:
        rdson_tj = rdson_poly_fun(p.get("Rdson_poly", RDSON_POLY_DEFAULT))
    slopes = daf.SwitchingSlopes(
        *[
            _table_function(raw[f"{k}_X"], raw[f"{k}_Y"])
            for k in ("didt_on", "didt_off", "dvdt_on", "dvdt_off")
        ]
    )
    return slopes, rdson_tj


@dataclass(frozen=True)
class Design:
    """Derived machine, battery and converter quantities (independent of SOC)."""

    VBase: float  # [V] base phase voltage (peak)
    VMax: float  # [V] maximum phase voltage (peak) at nominal cell voltage
    wmBase: float  # [rad/s]
    TBase: float  # [N.m]
    Ibase: float  # [A] peak current limit
    wmMax: float  # [rad/s]
    motor: daf.MotorParameters
    Vnom: float  # [V] nominal cell voltage (50 % SOC)
    Nscells_2l: int
    Npcells_2l: int
    Npmos_2l: int
    Nsm: int  # submodules per phase
    Nscells_b: int  # series cells per submodule
    Npcells_b: float  # may be fractional with "match" sizing (equal cell count)
    Npmos_b: int


def bimmc_sizing(p, Nscells_2l, VBase, Vnom, window=3):
    """Submodules per phase and series cells per submodule of the BI-MMC."""
    Nsm = int(p["Nsm"])
    if p.get("bimmc_sizing", "match") == "ceil":
        return Nsm, int(np.ceil(2 * VBase / np.sqrt(3) / (Vnom * Nsm)))
    # cells per phase that give the 2L peak phase voltage (Vdc / sqrt(3) with SVPWM)
    target = Nscells_2l / np.sqrt(3)
    candidates = [
        (abs(n * c - target), abs(n - Nsm), n, c)
        for n in range(max(Nsm - window, 1), Nsm + window + 1)
        for c in {max(int(np.floor(target / n)), 1), int(np.ceil(target / n))}
    ]
    _, _, n, c = min(candidates)
    return n, c


def design(p) -> Design:
    VBase = p["Vdc"] / 2
    VMax = VBase * 2 / np.sqrt(3)
    wb = p["wmBase"] * 2 * np.pi / 60
    pp = int(p["pp"])
    psi_f = VBase / (wb * pp)
    ZBase = (VBase / np.sqrt(2) * np.sqrt(3)) ** 2 / p["PBase"]
    Ibase = np.ceil(2 * p["PBase"] / (3 * VBase) / 50) * 50
    Rs = p["rs_pu"] * ZBase
    Ld = p["ld_pu"] * ZBase / (wb * pp)
    Lq = p["lq_pu"] * ZBase / (wb * pp)
    if Ld * Ibase >= psi_f:
        raise ValueError("Ld*Ibase >= magnet flux: no finite maximum speed")
    wmMax = VMax / (psi_f - Ld * Ibase) / pp

    Vnom = OCV[p["chemistry"]][OCV["soc"].index(0.5)]
    Nscells_2l = int(np.ceil(2 * VBase / Vnom))
    Npcells_2l = int(np.ceil(p["Ebatt"] / (p["Qcell"] * Vnom * Nscells_2l)))
    Nsm, Nscells_b = bimmc_sizing(p, Nscells_2l, VBase, Vnom)
    if p.get("bimmc_sizing", "match") == "ceil":
        Npcells_b = int(np.ceil(p["Ebatt"] / (3 * Nsm * Vnom * Nscells_b * p["Qcell"])))
    else:
        # same total number of cells (installed energy) as the 2L pack; the
        # equivalent parallel count is then generally not an integer
        Npcells_b = Nscells_2l * Npcells_2l / (3 * Nsm * Nscells_b)
    return Design(
        VBase=VBase,
        VMax=VMax,
        wmBase=wb,
        TBase=p["PBase"] / wb,
        Ibase=Ibase,
        wmMax=wmMax,
        motor=daf.MotorParameters(Rs, Ld, Lq, psi_f, pp),
        Vnom=Vnom,
        Nscells_2l=Nscells_2l,
        Npcells_2l=Npcells_2l,
        Npmos_2l=int(np.ceil(Ibase / (p["ImosRated_RMS"] * np.sqrt(2)))),
        Nsm=Nsm,
        Nscells_b=Nscells_b,
        Npcells_b=Npcells_b,
        # Imax_mosfet is an RMS rating; Ibase is a peak current
        Npmos_b=max(int(np.ceil(Ibase / (p["Imax_mosfet"] * np.sqrt(2)))), 4),
    )


def cell_state(p, soc):
    """Cell OCV and equivalent-circuit parameters (R0, R1, C1) at the given SOC."""
    ocv = OCV[p["chemistry"]]
    Vcell = np.interp(soc, OCV["soc"][::-1], ocv[::-1])
    poly_r = 1.3 * soc**2 - 1.3 * soc + 1.3
    poly_c = -1.3 * soc**2 + 1.3 * soc + 1.3
    C1_nom = p.get("C1_nom") or 1 / (2 * np.pi * 250 * p["R1_nom"])
    return Vcell, p["R0_nom"] * poly_r, p["R1_nom"] * poly_r, C1_nom * poly_c


def solve_mtpa(d: Design, vmax, wm_vec, T_vec, PBase):
    """MTPA currents on the (speed x torque) grid; NaN where infeasible or over current.

    wm_vec in [rad/s], T_vec in [N.m], vmax is the peak phase voltage limit [V].
    """
    opti, x, (Tau_ref, wm_ref, v_lim) = daf.create_mtpa_optimization_problem(d.motor)
    opti.set_value(v_lim, vmax)
    Id = np.full((len(wm_vec), len(T_vec)), np.nan)
    Iq = np.full_like(Id, np.nan)
    for ii, wm in enumerate(wm_vec):
        for jj, Tau in enumerate(T_vec):
            if abs(Tau * wm) > PBase:
                continue
            opti.set_value(Tau_ref, Tau)
            opti.set_value(wm_ref, wm)
            try:
                sol = opti.solve()
            except RuntimeError:
                opti.set_initial(x, 0)
                continue
            Id[ii, jj], Iq[ii, jj] = sol.value(x[0]), sol.value(x[1])
            opti.set_initial(x, sol.value(x))
    over = Id**2 + Iq**2 > d.Ibase**2
    Id[over] = np.nan
    Iq[over] = np.nan
    return Id, Iq


def dq_voltages(d: Design, Id, Iq, wm_vec):
    wr = np.asarray(wm_vec)[:, None] * d.motor.pole_pairs
    m = d.motor
    Vd = Id * m.stator_resistance - wr * m.q_axis_inductance * Iq
    Vq = Iq * m.stator_resistance + wr * (m.magnet_flux + m.d_axis_inductance * Id)
    return Vd, Vq


def loss_maps(p, soc, wm_vec, T_vec, voltage_limit="own", rdson_tj=True, rdson_iter=5):
    """Loss maps of both converters on a (speed x torque) grid.

    wm_vec [rad/s] (>= 0) and T_vec [N.m] (both signs) are 1-D vectors.
    voltage_limit: "own" gives each converter its own phase-voltage limit,
                   "2l" uses the 2L limit for both (dashboard behaviour).
    Returns a dict of 2-D arrays [W] / [°C] plus the grid and voltage limits.
    NaN marks points outside a converter's envelope (voltage, current or power).
    """
    d = design(p)
    wm_vec = np.asarray(wm_vec, dtype=float)
    T_vec = np.asarray(T_vec, dtype=float)
    Vcell, R0, R1, C1 = cell_state(p, soc)
    Nsm = d.Nsm
    r = p["Nsm_redundant_pu"]

    V_dc = Vcell * d.Nscells_2l  # full 2L DC-link (pack) voltage
    vmax_2l = V_dc / np.sqrt(3)  # peak phase voltage with SVPWM
    Vs_b = Vcell * d.Nscells_b  # submodule voltage
    vmax_b = Vs_b * Nsm * (1 - r) if voltage_limit == "own" else vmax_2l

    Id_2l, Iq_2l = solve_mtpa(d, vmax_2l, wm_vec, T_vec, p["PBase"])
    if np.isclose(vmax_b, vmax_2l):
        Id_b, Iq_b = Id_2l, Iq_2l
    else:
        Id_b, Iq_b = solve_mtpa(d, vmax_b, wm_vec, T_vec, p["PBase"])

    Pout = wm_vec[:, None] * T_vec[None, :]

    # --- two-level inverter
    slopes_2l, rdson_fun = mosfet_data(p)
    Vd, Vq = dq_voltages(d, Id_2l, Iq_2l, wm_vec)
    thermal_2l = daf.ThermalParameters(p["Tambient"], p["Rth_jc_2l"], p["Rth_ca_2l"])
    battery_2l = daf.BatteryParameters(R0, R1, C1, d.Nscells_2l, d.Npcells_2l)
    Rdson = p["Rdson_2l"]
    for _ in range(rdson_iter if rdson_tj else 1):
        Pc_2l, Ps_2l, Pb_2l, Tj_2l, Tc_2l = daf.calc_losses_2l(
            Id_2l,
            Iq_2l,
            Vd,
            Vq,
            daf.TwoLevelLossConfig(
                dc_voltage=V_dc,
                on_resistance=Rdson,
                parallel_devices=d.Npmos_2l,
                switching_frequency=p["fsw"],
                battery=battery_2l,
                thermal=thermal_2l,
                switching=slopes_2l,
            ),
        )
        if rdson_tj:
            # datasheet Rdson is given at 25 °C; Tj is NaN outside the envelope
            Rdson = p["Rdson_2l"] * rdson_fun(np.nan_to_num(Tj_2l, nan=25.0))

    # --- BI-MMC
    Vd_b, Vq_b = dq_voltages(d, Id_b, Iq_b, wm_vec)
    fsw_b = p["mf_bimmc"] * wm_vec[:, None] * d.motor.pole_pairs / (2 * np.pi)
    fsw_b = np.broadcast_to(fsw_b, Id_b.shape)
    Pc_b, Ps_b, Pb_b, Tj_b, Tc_b = daf.calc_losses_bimmc(
        Id_b,
        Iq_b,
        Vd_b,
        Vq_b,
        wm_vec,
        T_vec,
        daf.BimmcLossConfig(
            submodules_per_phase=Nsm,
            submodules_redundant_pu=r,
            submodule_voltage=Vs_b,
            on_resistance=p["Rdson_bimmc"],
            parallel_devices=d.Npmos_b,
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
            battery=daf.BatteryParameters(R0, R1, C1, d.Nscells_b, d.Npcells_b),
            pole_pairs=d.motor.pole_pairs,
        ),
    )

    # steady-state thermal limits (reported separately, the loss maps are not masked:
    # a transient cycle can pass through these points without reaching steady state)
    with np.errstate(invalid="ignore"):
        thermal_ok_2l = (Tj_2l <= p["Tjmax_2l"]) & (Tc_2l <= p["Tcmax_2l"])
        thermal_ok_b = Tj_b <= p["Tjmax_bimmc"]

    return {
        "wm": wm_vec,
        "T": T_vec,
        "Pout": Pout,
        "vmax_2l": vmax_2l,
        "vmax_bimmc": vmax_b,
        "Id_2l": Id_2l,
        "Iq_2l": Iq_2l,
        "Id_bimmc": Id_b,
        "Iq_bimmc": Iq_b,
        "Pc_2l": Pc_2l,
        "Ps_2l": Ps_2l,
        "Pb_2l": Pb_2l,
        "Tj_2l": Tj_2l,
        "Tc_2l": Tc_2l,
        "thermal_ok_2l": thermal_ok_2l,
        "Pc_bimmc": Pc_b,
        "Ps_bimmc": Ps_b,
        "Pb_bimmc": Pb_b,
        "Tj_bimmc": Tj_b,
        "Tc_bimmc": Tc_b,
        "thermal_ok_bimmc": thermal_ok_b,
    }


def efficiency(Pout, Ploss):
    """Efficiency with the drive's sign convention (regeneration stays <= 100 %)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return Pout / (Pout + np.sign(Pout) * Ploss)


def default_grid(p, n_speed=50, n_torque=100):
    """Speed [rad/s] and torque [N.m] vectors covering the full map (as in main.py)."""
    d = design(p)
    return np.linspace(0, d.wmMax, n_speed), np.linspace(-d.TBase, d.TBase, n_torque)
