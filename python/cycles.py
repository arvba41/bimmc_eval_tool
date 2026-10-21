"""Duty cycles -> machine speed [rad/s] and torque [N.m] time series.

Four kinds of cycle (see applications.APPLICATIONS):
- "speed":      vehicle speed vs. time (WLTC, WHVC, Braunschweig) + road-load model
- "normalised": normalised speed/torque vs. time (NRTC)
- "modes":      weighted steady-state modes (ISO 8178 E3, propeller law)
- "road":       cruise-controlled run over a measured road slope profile
- "rail":       synthetic station-to-station run + Davis resistance

Torque beyond the machine envelope is not handled here; cycle_eval clips it (the
remainder goes to the mechanical brake or is not delivered).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from scipy.io import loadmat

import applications as apps
import model

CYCLE_DIR = Path(__file__).parent / "data" / "cycles"
ROAD_DIR = Path(__file__).parent / "so_no"


def _wheel_to_machine(app, v, a, slope=0.0):
    """Machine speed and torque for wheel speed v [m/s], acceleration a [m/s^2], slope [rad]."""
    veh = app["vehicle"]
    G = apps.gear_ratio(app)
    F = apps.road_load_force(veh, v, a, slope)
    T_wheel = F * veh["wheel_radius"]
    eta = veh["gear_eff"]
    # gear losses: motoring needs more machine torque, braking returns less
    T = np.where(T_wheel >= 0, T_wheel / (G * eta), T_wheel * eta / G)
    wm = v / veh["wheel_radius"] * G
    return wm, T


def speed_cycle(app):
    df = pd.read_csv(CYCLE_DIR / app["cycle"]["file"])
    t = df["time_s"].to_numpy(dtype=float)
    v = df["speed_kmh"].to_numpy(dtype=float) / 3.6
    a = np.gradient(v, t)
    wm, T = _wheel_to_machine(app, v, a)
    return {"t": t, "dt": np.gradient(t), "v": v, "wm": wm, "T": T}


def road_cycle(app, step=1.0):
    """Truck on a real road: proportional cruise controller holds v_set on a slope profile.

    The road (road_distance [m], road_slope [rad]) is a .mat file in so_no/. The speed
    follows from the longitudinal dynamics m dv/dt = F_ctrl - F_resistance(v, slope),
    integrated over time until the end of the road is reached.
    """
    veh = app["vehicle"]
    cyc = app["cycle"]
    road = loadmat(ROAD_DIR / cyc["file"], squeeze_me=True)
    dist, slope_rad = road["road_distance"], road["road_slope"]
    slope = interp1d(dist, slope_rad, fill_value="extrapolate")
    f_max = cyc["max_wheel_torque"] / veh["wheel_radius"]
    v_set = cyc["v_set_kmh"] / 3.6

    def dynamics(t, y):
        x, v = y
        f_ctrl = np.clip(cyc["k_p"] * (v_set - v), -f_max, f_max)
        resistance = apps.road_load_force(veh, v, 0.0, float(slope(x)))
        return [v, (f_ctrl - resistance) / (veh["mass"] * veh["rot_mass_factor"])]

    def end_of_road(t, y):
        return y[0] - dist[-1]

    end_of_road.terminal = True
    end_of_road.direction = 1
    t_eval = np.arange(0, 20000, step)
    sol = solve_ivp(
        dynamics, (t_eval[0], t_eval[-1]), [0.0, cyc["v_init"]], t_eval=t_eval, events=end_of_road
    )
    t, x, v = sol.t, sol.y[0], sol.y[1]
    a = np.gradient(v, t)
    wm, T = _wheel_to_machine(app, v, a, slope(x))
    return {"t": t, "dt": np.full_like(t, step), "v": v, "wm": wm, "T": T, "slope": slope(x)}


def normalised_cycle(app):
    """NRTC: speed 0-100 % between idle and rated speed, torque in % of max. torque."""
    df = pd.read_csv(CYCLE_DIR / app["cycle"]["file"])
    veh = app["vehicle"]
    d = model.design(app["params"])
    t = df["time_s"].to_numpy(dtype=float)
    n_pct = df["speed_pct"].to_numpy(dtype=float)
    T_pct = df["torque_pct"].to_numpy(dtype=float)
    rated = veh["rated_speed_pu"] * d.wmBase
    idle = veh["idle_speed_pu"] * rated
    wm = idle + n_pct / 100 * (rated - idle)
    T_max = np.minimum(d.TBase, app["params"]["PBase"] / np.maximum(wm, 1e-9))
    # motoring points ("m", NaN torque) are taken as zero torque: the replaced engine
    # is dragged by the load, which an electric drive need not recover
    T = np.nan_to_num(T_pct, nan=0.0) / 100 * T_max
    return {"t": t, "dt": np.gradient(t), "v": None, "wm": wm, "T": T}


def mode_cycle(app, duration_s=3600.0):
    """ISO 8178 E3 modes as steady points weighted by their share of time."""
    veh = app["vehicle"]
    d = model.design(app["params"])
    m = apps.E3_MODES
    wm = np.array(m["speed_pu"]) * veh["rated_speed_pu"] * d.wmBase
    P = np.array(m["power_pu"]) * veh["rated_power_pu"] * app["params"]["PBase"]
    dt = np.array(m["weight"]) * duration_s
    return {"t": np.cumsum(dt) - dt, "dt": dt, "v": None, "wm": wm, "T": P / wm}


def rail_cycle(app, step=1.0):
    """Synthetic regional run: max. acceleration (power-limited), cruise, brake, dwell."""
    veh = app["vehicle"]
    cyc = app["cycle"]
    p = app["params"]
    m = veh["mass"] * veh["rot_mass_factor"]
    # tractive limits at the wheel: 90 % of the machine's power and base torque
    P_wheel = 0.9 * p["PBase"] * veh["gear_eff"]
    F_wheel = (
        0.9 * model.design(p).TBase * apps.gear_ratio(app) * veh["gear_eff"]
        / veh["wheel_radius"]
    )
    v_line = cyc["v_line_kmh"] / 3.6

    v_hist = []
    for dist in np.array(cyc["stations_km"]) * 1e3:
        v, x = 0.0, 0.0
        while True:
            braking_dist = v**2 / (2 * cyc["decel"])
            if x + v * step + braking_dist >= dist and v > 0:
                v = max(v - cyc["decel"] * step, 0.0)
            elif v < v_line:
                R = apps.road_load_force(veh, np.array(v), 0.0).item()
                a = min(cyc["accel"], (min(F_wheel, P_wheel / max(v, 0.1)) - R) / m)
                v = min(v + a * step, v_line)
            # else: cruise at line speed
            x += v * step
            v_hist.append(v)
            if v == 0.0:
                break
        v_hist += [0.0] * int(cyc["dwell_s"] / step)

    v = np.array(v_hist)
    t = np.arange(len(v)) * step
    a = np.gradient(v, t)
    wm, T = _wheel_to_machine(app, v, a)
    return {"t": t, "dt": np.full_like(t, step), "v": v, "wm": wm, "T": T}


def machine_profile(app):
    """Cycle of an application as a dict with t, dt [s], v [m/s] or None, wm [rad/s], T [N.m].

    Road cycles also carry the road slope [rad] as "slope".
    """
    kind = app["cycle"]["kind"]
    return {
        "speed": speed_cycle,
        "road": road_cycle,
        "normalised": normalised_cycle,
        "modes": mode_cycle,
        "rail": rail_cycle,
    }[kind](app)
