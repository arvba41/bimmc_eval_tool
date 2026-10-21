"""Application presets: drive design (model.NOMINAL format) plus vehicle and cycle data.

All applications use the same cell (24 Ah NMC), the same 2L device family
(Wolfspeed 1200 V module, so the DC link is kept <= 800 V) and the same BI-MMC
submodule design, so that differences come from the duty cycle and drive rating.
Vehicle data are typical literature values (assumptions, see the `source` fields).

Gear ratio: chosen so that the top speed of the vehicle maps to 95 % of the
machine's maximum speed (computed in `gear_ratio`).
"""

from copy import deepcopy

from pathlib import Path

import numpy as np
from scipy.io import loadmat

import model

G = 9.81  # [m/s^2]
RHO_AIR = 1.2  # [kg/m^3]


def _truck_vehicle():
    """40 t tractor-semitrailer from so_no/vehicle_params.mat (Södertälje-Norrköping study)."""
    v = loadmat(Path(__file__).parent / "so_no" / "vehicle_params.mat", squeeze_me=True)
    return {
        "type": "road",
        "mass": float(v["m"]),  # [kg]
        "rot_mass_factor": 1.0,  # the study ignores rotating inertia
        "CdA": float(v["C_d"] * v["A"]),  # [m^2]
        "Crr": float(v["c_r0"]),
        "Crr_v": float(v["c_r1"]),  # [s/m] speed-dependent part: Crr = c_r0 + c_r1 * v
        "rho": float(v["rho"]),  # [kg/m^3]
        "g": float(v["g"]),  # [m/s^2]
        "wheel_radius": float(v["r_w"]),
        "gear_eff": 0.96,
        "v_top_kmh": 90.0,
        "cruise_speed_kmh": 80.0,  # cruise speed maps to 1 pu machine speed
        "cruise_pu": 1.0,
        "source": "40 t tractor-semitrailer, so_no/vehicle_params.mat",
    }


def _app(overrides, vehicle=None, cycle=None, label=""):
    p = deepcopy(model.NOMINAL)
    p.update(overrides)
    return {"label": label, "params": p, "vehicle": vehicle, "cycle": cycle}


APPLICATIONS = {
    "car": _app(
        {"PBase": 150e3, "wmBase": 5000.0, "Vdc": 400.0, "Ebatt": 75e3},
        vehicle={
            "type": "road",
            "mass": 1900.0,  # [kg] incl. driver and some payload
            "rot_mass_factor": 1.05,
            "CdA": 0.62,  # [m^2]
            "Crr": 0.0085,
            "wheel_radius": 0.33,  # [m]
            "gear_eff": 0.97,
            "v_top_kmh": 180.0,
            "source": "typical D-segment BEV",
        },
        cycle={"kind": "speed", "file": "wltc_class3b.csv", "name": "WLTC Class 3b"},
        label="Passenger car",
    ),
    "bus": _app(
        {"PBase": 250e3, "wmBase": 2500.0, "Vdc": 700.0, "Ebatt": 350e3},
        vehicle={
            "type": "road",
            "mass": 15000.0,  # [kg] 12 m bus, half load
            "rot_mass_factor": 1.08,
            "CdA": 5.0,
            "Crr": 0.007,
            "wheel_radius": 0.48,
            "gear_eff": 0.96,
            "v_top_kmh": 85.0,
            "source": "typical 12 m city bus",
        },
        cycle={"kind": "speed", "file": "braunschweig.csv", "name": "Braunschweig"},
        label="City bus",
    ),
    "truck": _app(
        {},  # dashboard defaults: 400 kW, 400 kWh, 700 V
        vehicle=_truck_vehicle(),
        cycle={
            "kind": "road",
            "file": "SoNO_scenario.mat",  # road_distance [m], road_slope [rad]
            "name": "Södertälje-Norrköping",
            "v_set_kmh": 80.0,  # speed set point of the cruise controller
            "v_init": 20.0,  # [m/s]
            "k_p": 1e4,  # [N/(m/s)] proportional gain
            "max_wheel_torque": 7000.0,  # [N.m] traction/brake limit at the wheels
        },
        label="Heavy-duty truck",
    ),
    "offroad": _app(
        {"PBase": 150e3, "wmBase": 2000.0, "Vdc": 700.0, "Ebatt": 200e3},
        vehicle={
            "type": "normalised",
            # NRTC normalised speed: 0 % = idle, 100 % = rated speed
            "idle_speed_pu": 0.35,  # idle / rated speed of the replaced engine
            "rated_speed_pu": 1.0,  # rated speed in pu of the machine base speed
            "source": "e-machine replacing a 150 kW diesel (e.g. excavator, loader)",
        },
        cycle={"kind": "normalised", "file": "nrtc.csv", "name": "NRTC"},
        label="Off-road machine",
    ),
    "marine": _app(
        {"PBase": 400e3, "wmBase": 1800.0, "Vdc": 800.0, "Ebatt": 1000e3},
        vehicle={
            "type": "propeller",
            "rated_speed_pu": 1.0,  # propeller rated speed in pu of base speed
            "rated_power_pu": 0.9,  # continuous rating in pu of PBase
            "source": "electric ferry / workboat propulsion drive",
        },
        cycle={"kind": "modes", "name": "ISO 8178 E3"},
        label="Marine vessel",
    ),
    "train": _app(
        {"PBase": 600e3, "wmBase": 2000.0, "Vdc": 800.0, "Ebatt": 300e3},
        vehicle={
            "type": "rail",
            "mass": 60000.0,  # [kg] vehicle mass per traction drive
            "rot_mass_factor": 1.08,
            # Davis resistance R = A + B v + C v^2, v in km/h, R in N
            "davis": (1000.0, 10.0, 0.10),
            "wheel_radius": 0.43,
            "gear_eff": 0.97,
            "v_top_kmh": 140.0,
            "source": "regional battery multiple unit, one drive per 60 t",
        },
        cycle={
            "kind": "rail",
            "name": "Synthetic regional run",
            "stations_km": [4.0, 7.0, 10.0],  # inter-station distances
            "v_line_kmh": 120.0,
            "accel": 0.8,  # [m/s^2] max. tractive acceleration
            "decel": 0.8,  # [m/s^2] service braking
            "dwell_s": 40.0,
        },
        label="Regional train",
    ),
}

# ISO 8178-4 E3 (propeller law, heavy-duty marine): speed, power and weight per mode
E3_MODES = {
    "speed_pu": [1.00, 0.91, 0.80, 0.63],
    "power_pu": [1.00, 0.75, 0.50, 0.25],
    "weight": [0.20, 0.50, 0.15, 0.15],
}


def gear_ratio(app):
    """Machine speed / wheel speed.

    If the vehicle defines "cruise_speed_kmh" and "cruise_pu", that speed maps to
    cruise_pu times the base speed; otherwise v_top maps to 95 % of the maximum speed.
    """
    veh = app["vehicle"]
    d = model.design(app["params"])
    if "cruise_pu" in veh:
        return veh["cruise_pu"] * d.wmBase * veh["wheel_radius"] / (veh["cruise_speed_kmh"] / 3.6)
    return 0.95 * d.wmMax * veh["wheel_radius"] / (veh["v_top_kmh"] / 3.6)


def road_load_force(veh, v, a, slope=0.0):
    """Tractive force [N] at the wheel for speed v [m/s], acceleration a [m/s^2], slope [rad]."""
    m = veh["mass"] * veh["rot_mass_factor"]
    g = veh.get("g", G)
    if veh["type"] == "rail":
        A, B, C = veh["davis"]
        v_kmh = v * 3.6
        resistance = A + B * v_kmh + C * v_kmh**2
    else:
        resistance = 0.5 * veh.get("rho", RHO_AIR) * veh["CdA"] * v**2 + (
            veh["Crr"] + veh.get("Crr_v", 0.0) * v
        ) * veh["mass"] * g * np.cos(slope)
    resistance = resistance + veh["mass"] * g * np.sin(slope)
    # resistance only acts when moving
    resistance = np.where(v > 0.01, resistance, 0.0)
    return m * a + resistance
