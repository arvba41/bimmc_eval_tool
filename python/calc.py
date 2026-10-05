# %%
# imports

from dataclasses import dataclass, field
from typing import Callable

import casadi as ca
import numpy as np
from numba import njit
from scipy.signal import sawtooth
from tqdm import tqdm

Slope = float | Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class MotorParameters:
    stator_resistance: float
    d_axis_inductance: float
    q_axis_inductance: float
    magnet_flux: float
    pole_pairs: int


@dataclass(frozen=True)
class SwitchingSlopes:
    didt_on: Slope = 10.0
    didt_off: Slope = 18.0
    dvdt_on: Slope = 25.0
    dvdt_off: Slope = 30.0


@dataclass(frozen=True)
class BatteryParameters:
    r0: float
    r1: float
    c1: float
    series_cells: int
    parallel_cells: int


@dataclass(frozen=True)
class ThermalParameters:
    ambient_temperature: float
    junction_to_case: float
    case_to_ambient: float


@dataclass(frozen=True)
class TwoLevelLossConfig:
    dc_voltage: float
    on_resistance: float
    parallel_devices: int
    switching_frequency: float
    battery: BatteryParameters
    thermal: ThermalParameters
    switching: SwitchingSlopes = field(default_factory=SwitchingSlopes)


@dataclass(frozen=True)
class BimmcLossConfig:
    submodules_per_phase: int
    submodules_redundant_pu: float
    submodule_voltage: float
    on_resistance: float
    parallel_devices: int
    switching_frequency: np.ndarray | float
    thermal: ThermalParameters
    battery: BatteryParameters
    pole_pairs: int
    switching: SwitchingSlopes = field(
        default_factory=lambda: SwitchingSlopes(
            didt_on=1.0, didt_off=1.0, dvdt_on=0.5, dvdt_off=0.5
        )
    )


def _slope_value(slope: Slope, current: np.ndarray) -> np.ndarray | float:
    return slope(current) if callable(slope) else slope


# %%
# Create an optimization object for MTPA


def create_mtpa_optimization_problem(motor: MotorParameters):
    opti = ca.Opti()  # Create an optimization problem

    x = opti.variable(2, 1)  # Create a 2-dimensional optimization variable

    Tau_ref = opti.parameter()  # Create a parameter for the reference torque
    wm_ref = opti.parameter()  # Create a parameter for the reference speed
    vmax = opti.parameter()  # Create a parameter for the maximum voltage

    opti.minimize(x[0] ** 2 + x[1] ** 2)  # Set the objective function
    opti.subject_to(
        1.5
        * motor.pole_pairs
        * (
            motor.magnet_flux * x[1]
            + (motor.d_axis_inductance - motor.q_axis_inductance) * x[0] * x[1]
        )
        == Tau_ref
    )  # Set the constraint

    vd = (
        x[0] * motor.stator_resistance
        - wm_ref * motor.pole_pairs * motor.q_axis_inductance * x[1]
    )  # d-axis voltage equation
    vq = x[1] * motor.stator_resistance + wm_ref * motor.pole_pairs * (
        motor.magnet_flux + motor.d_axis_inductance * x[0]
    )  # q-axis voltage equation
    opti.subject_to(vd**2 + vq**2 < vmax**2)  # Set the voltage constraint

    opti.solver(
        "ipopt",
        {
            "ipopt": {
                "print_level": 0,
                "sb": "no",
                # "warm_start_init_point": "yes",
                # "linear_solver": "ma57",
            },
            "print_time": False,
        },
    )  # Set the solver to IPOPT

    # opti.solver("osqp", {"print_time": False}, {"osqp": {"verbose": False}})
    return opti, x, (Tau_ref, wm_ref, vmax)


# %%
# get the losses of a two-level converter


def calc_losses_2l(Id, Iq, Vd, Vq, config: TwoLevelLossConfig):
    vdc = config.dc_voltage
    Rdson = config.on_resistance
    Npmos = config.parallel_devices
    fsw = config.switching_frequency
    battery = config.battery
    thermal = config.thermal

    # # clculate the copper losses
    # # NOTE: converter model is not included because the THS is expected to be very low (~1 %).
    # Pcu_loss = 3 / 2 * Rs * (Id**2 + Iq**2)

    # two-level inverter conduction losses
    # CALC: Pon_per_mos     = 0.5 * (\hat I_dq / \sqrt(2) / Npmos )**2 * Rdson
    # CALC: Pon_per_switch  = 0.5 * (\hat I_dq / \sqrt(2) / Npmos )**2 * Rdson * Npmos
    #                       = 1 / 4 * (\hat I_dq)**2 * Rdson / Npmos
    # per phase: P_on_phase = 1 / 4 * (\hat I_dq )**2 * Rdson / Npmos * 2
    #                       = 1 / 2 * (\hat I_dq )**2 * Rdson / Npmos
    # total: P_on_total     = 3 / 2 * (\hat I_dq )**2 * Rdson / Npmos
    Pmos_loss = 3 / 2 * Rdson * (Id**2 + Iq**2) / Npmos

    # two-level inverter switching losses
    # get the switching slopes from the user-defined functions or use the default values
    switching = config.switching
    # vdc = kwargs.get("vdc", VMax)

    Idq = np.sqrt(Id**2 + Iq**2) * 2 / np.pi  # [A] (abs avg. value of the current)
    device_current = Idq / Npmos
    tri = device_current / _slope_value(switching.didt_on, device_current) * 1e-9
    tfi = device_current / _slope_value(switching.didt_off, device_current) * 1e-9
    trv = vdc / _slope_value(switching.dvdt_on, device_current) * 1e-9
    tfv = vdc / _slope_value(switching.dvdt_off, device_current) * 1e-9
    # CALC: Esw_per_mos = 1 / 2 * Vdc * Idq * 2 / \pi / Npmos * (tri + tfv + tfi + trv)
    # Esw_per_sw        = 1 / 2 * Vdc * Idq * 2 / \pi / Npmos * (tri + tfv + tfi + trv) * Npmos
    #                   = 1 / 2 * Vdc * Idq * 2 / \pi * (tri + tfv + tfi + trv)
    Esw_per_sw = 1 / 2 * vdc * Idq * (tri + tfv + tfi + trv)
    Psw_loss = 3 * 2 * Esw_per_sw * Npmos * fsw  # [W]

    # calculate the case and junction temperatures
    Tc = (
        thermal.ambient_temperature
        + (Pmos_loss + Psw_loss) / (3 * 2 * Npmos) * thermal.case_to_ambient
    )  # [°C] case temperature
    Tj = (
        Tc + (Pmos_loss + Psw_loss) / (3 * 2 * Npmos) * thermal.junction_to_case
    )  # [°C] junction temperature

    # battery losses
    # Idc = 3/2 * \sqrt(Id^2 + Iq^2) * cos(arctan(Vq/Vd) - arctan(Iq/Id)) * \sqrt(Vd^2 + Vq^2) / (2 * vdc)
    P_inv_in = (
        3
        / 2
        * np.sqrt(Id**2 + Iq**2)
        * np.cos(np.arctan2(Vq, Vd) - np.arctan2(Iq, Id))
        * np.sqrt(Vd**2 + Vq**2)
    )  # [W] input power to the inverter
    Idc = (P_inv_in + ((Pmos_loss + Psw_loss) * np.sign(P_inv_in))) / (2 * vdc)
    Pbatt = (
        Idc**2
        * (battery.r0 + battery.r1)
        * battery.series_cells
        / battery.parallel_cells
    )  # [W] battery losses

    return Pmos_loss, Psw_loss, Pbatt, Tj, Tc


# %%
# # get the losses of the BI-MMC drive
def calc_losses_bimmc(Id, Iq, Vd, Vq, wm_ref, Te_ref, config: BimmcLossConfig):
    Nsm = config.submodules_per_phase
    r = config.submodules_redundant_pu
    vs = config.submodule_voltage
    Rdson = config.on_resistance
    Npmos = config.parallel_devices
    fsw = config.switching_frequency
    thermal = config.thermal
    r0 = config.battery.r0
    r1 = config.battery.r1
    c1 = config.battery.c1
    nscells = config.battery.series_cells
    npcells = config.battery.parallel_cells
    pp = config.pole_pairs

    # # clculate the copper losses
    # # NOTE: converter model is not included because the THS is expected to be very low (~1 %).
    # Pcu_loss = 3 / 2 * Rs * (Id**2 + Iq**2)

    # inverter conduction losses
    # CALC: Pon_per_switch  = 0.5 * (\hat I_dq / \sqrt(2) / Npmos )**2 * Rdson
    #                       = 0.5 / 2 * (\hat I_dq / Npmos )**2 * Rdson
    # Pon_per_SM    = 0.5 / 2 * (\hat I_dq / Npmos )**2 * Rdson * Nsw * Npmos (where Nsw - number of switches per SM, Nsw = 4)
    #               = (\hat I_dq)**2 * Rdson / Npmos
    # per phase: P_on_phase = (\hat I_dq)**2 * Rdson / Npmos * Nsm (where Nsm - number of SMs per phase
    #                       = (\hat I_dq)**2 * Rdson / Npmos * Nsm
    # total: P_on_total     = 3 * (\hat I_dq)**2 * Rdson / Npmos * Nsm
    Pmos_loss = 3 * (Id**2 + Iq**2) / Npmos * Rdson * Nsm

    # inverter switching losses
    # get the switching slopes from the user-defined functions or use the default values
    switching = config.switching

    Idq = np.sqrt(Id**2 + Iq**2) * 2 / np.pi  # [A] (abs avg. value of the current)
    device_current = Idq / Npmos
    tri = device_current / _slope_value(switching.didt_on, device_current) * 1e-9
    tfi = device_current / _slope_value(switching.didt_off, device_current) * 1e-9
    trv = vs / _slope_value(switching.dvdt_on, device_current) * 1e-9
    tfv = vs / _slope_value(switching.dvdt_off, device_current) * 1e-9
    # Calculation of switching losses
    # CALC: Esw_per_mos = 1 / 2 * Vs * \sqrt(Id^2 + Iq^2) / Npmos * (tri + tfv + tfi + trv)
    # Esw_per_sw        = 1 / 2 * Vs * \sqrt(Id^2 + Iq^2) / Npmos * (tri + tfv + tfi + trv) * Npmos
    # Esw_per_sm        = 1 / 2 * Vs * \sqrt(Id^2 + Iq^2) * (tri + tfv + tfi + trv) * Nsw (where Nsw - number of switches per SM, Nsw = 4)
    # Esw_per_phase     = 1 / 2 * Vs * \sqrt(Id^2 + Iq^2) * (tri + tfv + tfi + trv) * Nsw * Nsm (where Nsm - number of SMs per phase)
    Esw_per_sw = 1 / 2 * vs * Idq * (tri + tfv + tfi + trv) * 4 * Nsm
    Psw_loss = 3 * 2 * Esw_per_sw * fsw  # [W]

    # calculate the case and junction temperatures
    Tc = (
        thermal.ambient_temperature
        + (Pmos_loss + Psw_loss) / (3 * 2 * Nsm * 4 * Npmos) * thermal.case_to_ambient
    )  # [°C] case temperature
    Tj = (
        Tc
        + (Pmos_loss + Psw_loss) / (3 * 2 * Nsm * 4 * Npmos) * thermal.junction_to_case
    )  # [°C] junction temperature

    # battery losses
    Pbatt = np.zeros_like(Idq)
    for ii, we in tqdm(
        enumerate(wm_ref * pp),
        total=len(wm_ref * pp),
        desc="Calculating battery losses",
    ):

        if we > 0:

            ts = 1 / (fsw[ii][0] * 100)  # [s] time step for the switching frequency
            tvec = np.arange(
                0, 2 * np.pi / we, ts
            )  # create a time vector for one electrical cycle
            theta = we * tvec

            for jj, _ in enumerate(Te_ref):

                io = np.cos(theta) * Id[ii, jj] - np.sin(theta) * Iq[ii, jj]

                vref = (np.cos(theta) * Vd[ii, jj] - np.sin(theta) * Vq[ii, jj]) / (
                    vs * Nsm * (1 - r)
                )  # [pu] reference voltage for the submodules
                vti = sawtooth(
                    2 * np.pi * fsw[ii][jj] * tvec, 0.5
                )  # [pu] triangular carrier signal
                g1 = (vref > vti).astype(float)  # [pu] gating signal for the submodules
                g3 = (vref < -vti).astype(
                    float
                )  # [pu] gating signal for the submodules
                io = io * g1 + (-io) * g3  # [A] current through the submodules

                Pbatt[ii, jj] = simulate_battery_loss(
                    io,
                    tvec,
                    r0 * nscells / npcells,
                    r1 * nscells / npcells,
                    c1 * npcells / nscells,
                )

        else:
            Pbatt[ii] = np.nan

    Pbatt *= 3 * Nsm  # [W] total battery losses

    return Pmos_loss, Psw_loss, Pbatt, Tj, Tc


@njit
def batterymdel(ib, R0, R1, C1, Vc):
    """
    Battery model using an equivalent circuit with a series resistor (R0) and a parallel RC network (R1, C1).

    Parameters:
    ib : array_like
        Battery current (A). Positive for discharging, negative for charging.
    R0 : float
        Series resistance (Ohm).
    R1 : float
        Parallel resistance (Ohm).
    C1 : float
        Parallel capacitance (F).

    Returns:
    dVc_dt : float
        Derivative of the capacitor voltage (V/s).
    dEb_dt : float
        Instantaneous battery power loss (W).
    """
    dVc_dt = 1 / C1 * (ib - Vc / R1)  # Differential equation for capacitor voltage
    dEb_dt = ib**2 * R0 + Vc**2 / R1  # Power loss in the battery

    return dVc_dt, dEb_dt


@njit
def simulate_battery_loss(ib_profile, tvec, R0, R1, C1):
    """
    Simulate the battery current profile over time and compute the cumulative energy loss.
    """
    Vc = 0
    Eb = 0
    for i in range(ib_profile.size):
        dVc_dt, dEb_dt = batterymdel(ib_profile[i], R0, R1, C1, Vc)
        if i < tvec.size - 1:
            Vc += dVc_dt * (tvec[i + 1] - tvec[i])
            Eb += dEb_dt * (tvec[i + 1] - tvec[i])

    return Eb / (tvec[-1] - tvec[0])
