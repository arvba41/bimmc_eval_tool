"""Drive-cycle loss evaluation of the 2L inverter and the BI-MMC for all applications.

The loss models of calc.py are evaluated at every time step of the duty cycle
(cycles.machine_profile), no loss/efficiency maps are involved. The user chooses the
application and the initial battery SOC; the output is the instantaneous conduction,
switching and battery loss of both drives together with the SOC trajectory, which
evolves along the cycle with the power drawn from the cells.

Usage:
    python cycle_eval.py [--apps car bus truck offroad marine train]
                         [--soc 0.2 0.5 0.9] [--jobs 6]

Python:
    res, trace = evaluate_cycle("car", soc0=0.9)   # summary dict, per-step DataFrame
"""

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault(
    "TQDM_DISABLE", "1"
)  # silence the per-point battery-loss progress bar

import numpy as np
import pandas as pd

import applications as apps
import calc as daf
import cycles
import model

RESULTS_DIR = Path(__file__).parent / "results_cycles"
CONVERTERS = ("2l", "bimmc")
COMPONENTS = ("Pc", "Ps", "Pb")  # conduction, switching, battery
MIN_FSW_BIMMC = (
    50.0  # [Hz] BI-MMC battery loss needs an electrical cycle; the explicit-Euler RC
)
# simulation (step 1/(100 fsw)) is only stable above ~8 Hz, which sets a floor on the speed
N_BISECT = (
    10  # torque bisection steps when the requested torque is outside the envelope
)


# ----------------------------------------------------------------------------
# loss maps (only used by doc/figures/make_cycle_figures.py for the background maps)


def map_path(app_key, soc, n_speed, n_torque):
    return (
        RESULTS_DIR
        / f"maps_{app_key}_soc{int(round(soc * 100)):02d}_{n_speed}x{n_torque}.npz"
    )


def compute_maps(app_key, soc, n_speed=50, n_torque=100, recompute=False):
    path = map_path(app_key, soc, n_speed, n_torque)
    if path.exists() and not recompute:
        return dict(np.load(path))
    p = apps.APPLICATIONS[app_key]["params"]
    wm_vec, T_vec = model.default_grid(p, n_speed, n_torque)
    maps = model.loss_maps(p, soc, wm_vec, T_vec)
    RESULTS_DIR.mkdir(exist_ok=True)
    np.savez_compressed(path, **maps)
    return maps


# ----------------------------------------------------------------------------
# operating point: MTPA currents and feasible torque


def make_mtpa_solver(d):
    """Reusable MTPA problem (CasADi/IPOPT); the previous solution warm-starts the next."""
    return daf.create_mtpa_optimization_problem(d.motor)


def mtpa_point(solver, d, wm, T, vmax):
    """MTPA currents (Id, Iq) [A] at speed wm [rad/s], torque T [N.m] and voltage limit vmax [V].

    Returns None if the point is infeasible (voltage) or exceeds the current limit.
    """
    opti, x, (Tau_ref, wm_ref, v_lim) = solver
    opti.set_value(v_lim, vmax)
    opti.set_value(Tau_ref, T)
    opti.set_value(wm_ref, wm)
    try:
        sol = opti.solve()
    except RuntimeError:
        opti.set_initial(x, 0)
        return None
    Id, Iq = float(sol.value(x[0])), float(sol.value(x[1]))
    opti.set_initial(x, sol.value(x))
    if Id**2 + Iq**2 > d.Ibase**2:
        return None
    return Id, Iq


def feasible_torque(solver, d, wm, T_req, vmax):
    """Largest torque with the sign of T_req that is <= |T_req| and feasible at (wm, vmax).

    Tries T_req first and bisects towards zero otherwise. Returns (T, (Id, Iq)); the
    currents are None if not even zero torque is feasible (voltage too low at this speed).
    """
    sol = mtpa_point(solver, d, wm, T_req, vmax)
    if sol is not None:
        return T_req, sol
    lo, hi, best = 0.0, T_req, None
    for _ in range(N_BISECT):
        mid = (lo + hi) / 2
        s = mtpa_point(solver, d, wm, mid, vmax)
        if s is not None:
            lo, best = mid, s
        else:
            hi = mid
    if best is None:
        return 0.0, mtpa_point(solver, d, wm, 0.0, vmax)
    return lo, best


# ----------------------------------------------------------------------------
# instantaneous losses (calc.py) at one operating point


def losses_2l(p, d, mosfet, cell, wm, Id, Iq, rdson_iter=5):
    """Pc, Ps, Pb [W], Tj and Tc [degC] of the 2L inverter and its battery at one point."""
    slopes, rdson_fun = mosfet
    Vcell, R0, R1, C1 = cell
    V_dc = Vcell * d.Nscells_2l
    Id, Iq = np.array([[Id]]), np.array([[Iq]])
    Vd, Vq = model.dq_voltages(d, Id, Iq, [wm])
    thermal = daf.ThermalParameters(p["Tambient"], p["Rth_jc_2l"], p["Rth_ca_2l"])
    battery = daf.BatteryParameters(R0, R1, C1, d.Nscells_2l, d.Npcells_2l)
    Rdson = p["Rdson_2l"]
    for _ in range(rdson_iter):  # fixed point Tj -> Rdson(Tj) -> Pcond -> Tj
        Pc, Ps, Pb, Tj, Tc = daf.calc_losses_2l(
            Id,
            Iq,
            Vd,
            Vq,
            daf.TwoLevelLossConfig(
                dc_voltage=V_dc,
                on_resistance=Rdson,
                parallel_devices=d.Npmos_2l,
                switching_frequency=p["fsw"],
                battery=battery,
                thermal=thermal,
                switching=slopes,
            ),
        )
        Rdson = p["Rdson_2l"] * rdson_fun(Tj)
    return (
        float(Pc[0, 0]),
        float(Ps[0, 0]),
        float(Pb[0, 0]),
        float(Tj[0, 0]),
        float(Tc[0, 0]),
    )


def losses_bimmc(p, d, cell, wm, T, Id, Iq):
    """Pc, Ps, Pb [W], Tj and Tc [degC] of the BI-MMC and its battery at one point."""
    Vcell, R0, R1, C1 = cell
    wm_eff = max(wm, MIN_FSW_BIMMC * 2 * np.pi / (p["mf_bimmc"] * d.motor.pole_pairs))
    Vs_b = Vcell * d.Nscells_b
    Id, Iq = np.array([[Id]]), np.array([[Iq]])
    Vd, Vq = model.dq_voltages(d, Id, Iq, [wm_eff])
    Pc, Ps, Pb, Tj, Tc = daf.calc_losses_bimmc(
        Id,
        Iq,
        Vd,
        Vq,
        np.array([wm_eff]),
        np.array([T]),
        daf.BimmcLossConfig(
            submodules_per_phase=d.Nsm,
            submodules_redundant_pu=p["Nsm_redundant_pu"],
            submodule_voltage=Vs_b,
            on_resistance=p["Rdson_bimmc"],
            parallel_devices=d.Npmos_b,
            switching_frequency=p["mf_bimmc"]
            * wm_eff
            * d.motor.pole_pairs
            / (2 * np.pi)
            * np.ones((1, 1)),
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
            rdson_vs_tj=model.bimmc_rdson_fun(p),
        ),
    )
    return (
        float(Pc[0, 0]),
        float(Ps[0, 0]),
        float(Pb[0, 0]),
        float(Tj[0, 0]),
        float(Tc[0, 0]),
    )


# ----------------------------------------------------------------------------
# cycle evaluation


def evaluate_cycle(app_key, soc0, rdson_iter=5):
    """Time-domain loss evaluation of one application, starting at state of charge soc0.

    Returns (summary dict, per-step DataFrame with the instantaneous losses and SOC).
    """
    app = apps.APPLICATIONS[app_key]
    p = app["params"]
    d = model.design(p)
    prof = cycles.machine_profile(app)
    wm_all = np.clip(prof["wm"], 0, d.wmMax)
    T_req_all, dt_all = prof["T"], prof["dt"]

    mosfet = model.mosfet_data(p)
    solver = {c: make_mtpa_solver(d) for c in CONVERTERS}
    r = p["Nsm_redundant_pu"]
    # total number of cells of each pack: the SOC follows from the charge drawn per cell
    n_cells = {
        "2l": d.Nscells_2l * d.Npcells_2l,
        "bimmc": 3 * d.Nsm * d.Nscells_b * d.Npcells_b,
    }

    soc = {c: float(soc0) for c in CONVERTERS}
    rows = []
    for wm, T_req, dt in zip(wm_all, T_req_all, dt_all):
        cell = {c: model.cell_state(p, soc[c]) for c in CONVERTERS}
        row = {
            "wm": wm,
            "T_req": T_req,
            "dt": dt,
            **{f"soc_{c}": soc[c] for c in CONVERTERS},
        }
        if abs(T_req) < 1e-9 and wm < 1e-9:  # standstill without torque: converter off
            T, ok = 0.0, True
            out = {c: (0.0, 0.0, 0.0, p["Tambient"], p["Tambient"]) for c in CONVERTERS}
        else:
            # the voltage limit follows the cell voltage, i.e. the present SOC
            vmax = {
                "2l": cell["2l"][0] * d.Nscells_2l / np.sqrt(3),
                "bimmc": cell["bimmc"][0] * d.Nscells_b * d.Nsm * (1 - r),
            }
            T_lim = p["PBase"] / max(wm, 1e-9) * (1 - 1e-9)  # rated power limit
            T_cmd = float(np.clip(T_req, -T_lim, T_lim))
            sol = {
                c: feasible_torque(solver[c], d, wm, T_cmd, vmax[c]) for c in CONVERTERS
            }
            # both drives deliver the same torque: the smaller of the two envelopes
            T = min(abs(sol["2l"][0]), abs(sol["bimmc"][0])) * np.sign(T_cmd)
            ok = True
            currents = {}
            for c in CONVERTERS:
                T_c, i_c = sol[c]
                if abs(T_c) != abs(T):
                    i_c = mtpa_point(solver[c], d, wm, T, vmax[c])
                currents[c] = i_c
                ok &= i_c is not None
            if ok:
                out = {
                    "2l": losses_2l(
                        p, d, mosfet, cell["2l"], wm, *currents["2l"], rdson_iter
                    ),
                    "bimmc": losses_bimmc(
                        p, d, cell["bimmc"], wm, T, *currents["bimmc"]
                    ),
                }
            else:  # no feasible current at this SOC and speed: losses not available
                out = {c: (0.0, 0.0, 0.0, np.nan, np.nan) for c in CONVERTERS}
        P = wm * T
        row.update({"T": T, "P": P, "infeasible": not ok})
        for c in CONVERTERS:
            Pc, Ps, Pb, Tj, Tc = out[c]
            row.update(
                {f"Pc_{c}": Pc, f"Ps_{c}": Ps, f"Pb_{c}": Pb, f"Tj_{c}": Tj, f"Tc_{c}": Tc}
            )
            row[f"Ploss_{c}"] = Pc + Ps + Pb
            # steady-state cell temperature (no thermal capacitance), bottom-cooled and
            # side-insulated cells, see model.CELL_THERMAL_DEFAULT
            row[f"Tcell_{c}"] = (
                model.cell_temperature(p, Pb, n_cells[c]) if ok else np.nan
            )
            # power drawn from the cells' open-circuit source (negative = charging)
            I_cell = (P + Pc + Ps + Pb) / (n_cells[c] * cell[c][0])
            soc[c] = float(
                np.clip(soc[c] - I_cell * dt / (3600 * p["Qcell"]), 0.0, 1.0)
            )
        rows.append(row)

    trace = pd.DataFrame(rows)
    trace.insert(0, "t", prof["t"])

    dt, wm, T, P = (
        trace["dt"].to_numpy(),
        trace["wm"].to_numpy(),
        trace["T"].to_numpy(),
        trace["P"].to_numpy(),
    )
    P_req = wm * T_req_all
    E = lambda x: float(np.sum(x * dt) / 3.6e6)  # [W] * [s] -> [kWh]  # noqa: E731
    res = {
        "app": app_key,
        "label": app["label"],
        "cycle": app["cycle"]["name"],
        "soc_start": float(soc0),
        "soc_end_2l": soc["2l"],
        "soc_end_bimmc": soc["bimmc"],
        "duration_s": float(np.sum(dt)),
        "distance_km": (
            float(np.sum(prof["v"] * dt) / 1e3) if prof["v"] is not None else None
        ),
        "E_motoring_kWh": E(np.maximum(P, 0)),
        "E_regen_kWh": E(np.maximum(-P, 0)),
        "E_clipped_motoring_kWh": E(np.maximum(P_req, 0) - np.maximum(P, 0)),
        "E_clipped_regen_kWh": E(np.maximum(-P_req, 0) - np.maximum(-P, 0)),
        "n_infeasible": int(trace["infeasible"].sum()),
        # share of |mechanical energy| delivered below base speed (no field weakening)
        "share_below_base_speed": float(
            np.sum(np.abs(P) * dt * (wm <= d.wmBase))
            / max(np.sum(np.abs(P) * dt), 1e-9)
        ),
        "gear_ratio": (
            apps.gear_ratio(app) if app["vehicle"].get("wheel_radius") else None
        ),
    }
    for conv in CONVERTERS:
        total = 0.0
        for c in COMPONENTS:
            res[f"E_{c}_{conv}_kWh"] = E(trace[f"{c}_{conv}"].to_numpy())
            total += res[f"E_{c}_{conv}_kWh"]
        res[f"E_loss_{conv}_kWh"] = total
        for T in ("Tj", "Tc", "Tcell"):  # peak temperatures over the cycle [degC]
            res[f"{T}_max_{conv}"] = float(np.nanmax(trace[f"{T}_{conv}"]))
        # losses charged to the traction energy (motoring + regeneration throughput)
        res[f"eta_cycle_{conv}"] = 1 - total / (
            res["E_motoring_kWh"] + res["E_regen_kWh"]
        )
        res[f"E_batt_net_{conv}_kWh"] = (
            res["E_motoring_kWh"] - res["E_regen_kWh"] + total
        )
    res["delta_eta_pp"] = (res["eta_cycle_bimmc"] - res["eta_cycle_2l"]) * 100
    res["delta_loss_pct"] = (res["E_loss_bimmc_kWh"] / res["E_loss_2l_kWh"] - 1) * 100
    if res["distance_km"]:
        for conv in CONVERTERS:
            res[f"kWh_per_100km_{conv}"] = (
                res[f"E_batt_net_{conv}_kWh"] / res["distance_km"] * 100
            )
    return res, trace


def _job(args):
    app_key, soc0 = args
    res, trace = evaluate_cycle(app_key, soc0)
    trace.to_csv(
        RESULTS_DIR / f"losses_{app_key}_soc{int(round(soc0 * 100)):02d}.csv",
        index=False,
    )
    return res


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apps", nargs="+", default=list(apps.APPLICATIONS))
    parser.add_argument(
        "--soc",
        nargs="+",
        type=float,
        default=[0.2, 0.5, 0.9],
        help="initial state of charge(s) [0-1]",
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count())
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    jobs = [(a, s) for a in args.apps for s in args.soc]
    print(f"Evaluating {len(jobs)} cycles ...")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(_job, jobs))
    df = pd.DataFrame(rows)
    df.to_excel(RESULTS_DIR / "cycle_results.xlsx", index=False)
    (RESULTS_DIR / "cycle_results.json").write_text(json.dumps(rows, indent=2))
    cols = [
        "label",
        "soc_start",
        "soc_end_2l",
        "soc_end_bimmc",
        "E_motoring_kWh",
        "E_loss_2l_kWh",
        "E_loss_bimmc_kWh",
        "eta_cycle_2l",
        "eta_cycle_bimmc",
        "delta_eta_pp",
        "n_infeasible",
    ]
    with pd.option_context("display.width", 220, "display.precision", 4):
        print(df[cols])
    print(f"Results written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
