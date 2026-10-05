# %%
# include necessary imports

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from os import PathLike

from seaborn import despine

textwidth = 3.45
goldenratio = (np.sqrt(5) + 1) / 2


@dataclass(frozen=True)
class PlotOptions:
    figure_number: int = 2
    save_path: str | PathLike[str] | None = None


@dataclass(frozen=True)
class OperatingMap:
    speed_rpm: np.ndarray
    torque_nm: np.ndarray
    base_power_w: float
    base_torque_nm: float


@dataclass(frozen=True)
class MtpaMapData:
    id_current: np.ndarray
    iq_current: np.ndarray
    d_voltage: np.ndarray
    q_voltage: np.ndarray
    operating_map: OperatingMap
    dc_voltage: float
    base_current: float
    soc: float


@dataclass(frozen=True)
class LossMapData:
    conduction_w: np.ndarray
    switching_w: np.ndarray
    battery_w: np.ndarray
    operating_map: OperatingMap


@dataclass(frozen=True)
class EfficiencyMapData:
    conduction: np.ndarray
    switching: np.ndarray
    battery: np.ndarray
    operating_map: OperatingMap


@dataclass(frozen=True)
class TemperatureMapData:
    junction_c: np.ndarray
    case_c: np.ndarray
    operating_map: OperatingMap


@dataclass(frozen=True)
class TotalLossMapData_comparison:
    total_loss_w_case_1: np.ndarray
    efficiency_case_1: np.ndarray
    str_case1: str
    total_loss_w_case_2: np.ndarray
    efficiency_case_2: np.ndarray
    str_case2: str
    operating_map: OperatingMap


@dataclass(frozen=True)
class IndividualLossMapData_comparison:
    conduction_w_case_1: np.ndarray
    switching_w_case_1: np.ndarray
    battery_w_case_1: np.ndarray
    str_case1: str
    conduction_w_case_2: np.ndarray
    switching_w_case_2: np.ndarray
    battery_w_case_2: np.ndarray
    str_case2: str
    operating_map: OperatingMap


# %%
# Local plotting functions
def plot_switching_slopes(
    rawdata_df, didt_on_fun, didt_off_fun, dvdt_on_fun, dvdt_off_fun, save_path=None
):
    id_vec = np.linspace(0, 400, 100)
    fig, ax = plt.subplots(
        1,
        1,
        clear=True,
        layout="constrained",
        # The sidebar controls the inputs; the output figure belongs to the
        # wide main area, so do not use the small paper-sized figure here.
        figsize=(textwidth, textwidth / goldenratio * 1.2),
    )
    ax.scatter(
        rawdata_df["didt_on_X"],
        rawdata_df["didt_on_Y"],
        label=r"$di/dt_{\mathrm{on}}$",
        marker="x",
    )
    ax.scatter(
        rawdata_df["didt_off_X"],
        rawdata_df["didt_off_Y"],
        label=r"$di/dt_{\mathrm{off}}$",
        marker="x",
    )
    ax.scatter(
        rawdata_df["dvdt_on_X"],
        rawdata_df["dvdt_on_Y"],
        label=r"$dv/dt_{\mathrm{on}}$",
        marker="x",
    )
    ax.scatter(
        rawdata_df["dvdt_off_X"],
        rawdata_df["dvdt_off_Y"],
        label=r"$dv/dt_{\mathrm{off}}$",
        marker="x",
    )
    ax.set_xlabel(r"$I_{\mathrm{d}}$ [A]")
    ax.set_ylabel(r"$di/dt$ [A/ns], $dv/dt$ [V/ns]")
    ax.set_ylim(-5, 50)
    ax.legend(ncols=2, fontsize=8, loc="upper center")
    ax.plot(id_vec, didt_on_fun(id_vec), color="gray", ls="--")
    ax.plot(id_vec, didt_off_fun(id_vec), color="gray", ls="--")
    ax.plot(id_vec, dvdt_on_fun(id_vec), color="gray", ls="--")
    ax.plot(id_vec, dvdt_off_fun(id_vec), color="gray", ls="--")
    despine(fig=fig)

    if save_path is not None:
        fig.savefig(save_path, dpi=200)

    return fig


def plot_Rdson_vs_Tj(Rdson_vs_Tj_rawdata, Rdson_Tj_fun, save_path=None):

    Tj_vec = np.linspace(-40, 175, 100)
    fig, ax = plt.subplots(
        1,
        1,
        clear=True,
        layout="constrained",
        # The sidebar controls the inputs; the output figure belongs to the
        # wide main area, so do not use the small paper-sized figure here.
        figsize=(textwidth, textwidth / goldenratio),
    )
    ax.scatter(
        Rdson_vs_Tj_rawdata["Tj"],
        Rdson_vs_Tj_rawdata["Rdson_normalized"],
        label=r"$R_{ds(on)}$ vs $T_j$",
        marker="x",
    )
    ax.set_xlabel(r"$T_j$ [°C]")
    ax.set_ylabel(r"$R_{ds(on)}$ [normalized]")
    # ax.set_ylim(0, 1.5)
    ax.legend(ncols=2, fontsize=8, loc="upper left")
    ax.plot(Tj_vec, Rdson_Tj_fun(Tj_vec) / Rdson_Tj_fun(25), color="gray", ls="--")
    despine(fig=fig)

    if save_path is not None:
        fig.savefig(save_path, dpi=200)

    return fig


def plot_cell_ocv_vs_soc(ocv_dict, battery_chem, save_path=None):

    soc_vec = ocv_dict["soc"]
    ocv_vec = ocv_dict[f"{battery_chem}"]

    fig, ax = plt.subplots(
        1,
        1,
        clear=True,
        layout="constrained",
        # The sidebar controls the inputs; the output figure belongs to the
        # wide main area, so do not use the small paper-sized figure here.
        figsize=(textwidth, textwidth / goldenratio),
    )
    ax.plot(soc_vec, ocv_vec)
    ax.set_xlabel(r"$z$ [-]")
    ax.set_ylabel(r"$v_\mathrm{oc}$ [V]")
    despine(fig=fig)

    if save_path is not None:
        fig.savefig(save_path, dpi=200)

    return fig


def plot_battery_parameters(R0_fn, R1_fn, C1_fn, save_path=None):

    soc_vec = np.arange(0, 1.01, 0.01)
    R0_vec = R0_fn(soc_vec)
    R1_vec = R1_fn(soc_vec)
    C1_vec = C1_fn(soc_vec)

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 1.2),
        clear=True,
        layout="constrained",
        sharex=True,
    )

    for ii, (data_to_plot, data_label) in enumerate(
        zip(
            [R0_vec * 1e3, R1_vec * 1e3, C1_vec],
            [r"$R_0$ [m$\Omega$]", r"$R_1$ [m$\Omega$]", r"$C_1$ [F]"],
        )
    ):
        ax[ii].plot(soc_vec, data_to_plot)
        ax[ii].set_ylabel(data_label)
        # ax[ii].grid()

    ax[-1].set_xlabel(r"$z$ [-]")
    despine(fig=fig)

    if save_path is not None:
        fig.savefig(save_path, dpi=200)

    return fig


def plot_mtpa_maps(data: MtpaMapData, options: PlotOptions = PlotOptions()):
    operating_map = data.operating_map
    Id, Iq = data.id_current, data.iq_current
    Vd, Vq = data.d_voltage, data.q_voltage
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    Vdc, Ibase, soc = data.dc_voltage, data.base_current, data.soc
    TBase, PBase = operating_map.base_torque_nm, operating_map.base_power_w

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    fig, ax = plt.subplots(
        2,
        2,
        figsize=(textwidth, textwidth / goldenratio * 2),
        sharex=True,
        sharey=True,
        layout="constrained",
        # height_ratios=[2, 2, 3],
        num=options.figure_number,
        clear=True,
    )

    ax_flat = ax.flatten()

    for ii, (data_to_plot, data_label) in enumerate(
        zip(
            [
                Id / Ibase,
                Iq / Ibase,
                Vd / Vdc,
                Vq / Vdc,
                # (Id**2 + Iq**2) ** 0.5 / Ibase,
                # (Vd**2 + Vq**2) ** 0.5 / Vdc,
            ],
            [
                r"$i_d$ [pu]",
                r"$i_q$ [pu]",
                r"$v_d$ [pu]",
                r"$v_q$ [pu]",
                # r"$i_{dq}$ [pu]",
                # r"$v_{dq}$ [pu]",
            ],
        )
    ):
        c = ax_flat[ii].contourf(
            wm_ref_vec, Tau_ref_vec, data_to_plot.T, levels=50, cmap="viridis"
        )
        cs = ax_flat[ii].contour(
            wm_ref_vec,
            Tau_ref_vec,
            data_to_plot.T,
            levels=5,
            colors="k",
            linewidths=0.5,
        )
        ax_flat[ii].plot(wm_ref_vec, Tmax, "r--")

        # cbar = fig.colorbar(c, ax=ax_flat[ii])
        ax_flat[ii].clabel(cs, inline=True, fontsize=8)
        ax_flat[ii].set_title(data_label, fontsize=8, loc="right")

    ax[0, 0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1, 0].set_ylabel(r"$\tau_e$ [Nm]")
    # ax[2, 0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[-1, 0].set_xlabel(r"$\omega_m$ [rpm]")
    ax[-1, 1].set_xlabel(r"$\omega_m$ [rpm]")

    despine(fig=fig)

    fig.suptitle(
        rf"Base values: $I={Ibase:.0f}$ A, $V={Vdc:.0f}$ V, $\tau={TBase:.0f}$ Nm, $soc={soc}$",
        fontsize=8,
    )

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_mtpa_maps_dqs(data: MtpaMapData, options: PlotOptions = PlotOptions()):
    operating_map = data.operating_map
    Id, Iq = data.id_current, data.iq_current
    Vd, Vq = data.d_voltage, data.q_voltage
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    Vdc, Ibase, soc = data.dc_voltage, data.base_current, data.soc
    TBase, PBase = operating_map.base_torque_nm, operating_map.base_power_w

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 2),
        sharex=True,
        sharey=True,
        layout="constrained",
        # height_ratios=[2, 2, 3],
        num=options.figure_number,
        clear=True,
    )

    cos_phi = np.cos(np.arctan2(Vq, Vd) - np.arctan2(Iq, Id))

    # ax_flat = ax.flatten()

    for ii, (data_to_plot, data_label) in enumerate(
        zip(
            [
                # Id / Ibase,
                # Iq / Ibase,
                # Vd / Vdc,
                # Vq / Vdc,
                (Id**2 + Iq**2) ** 0.5 / Ibase,
                (Vd**2 + Vq**2) ** 0.5 / Vdc,
                cos_phi,
            ],
            [
                # r"$i_d$ [pu]",
                # r"$i_q$ [pu]",
                # r"$v_d$ [pu]",
                # r"$v_q$ [pu]",
                r"$i_{dq}$ [pu]",
                r"$v_{dq}$ [pu]",
                r"$\cos(\phi)$ [-]",
            ],
        )
    ):
        c = ax[ii].contourf(
            wm_ref_vec, Tau_ref_vec, data_to_plot.T, levels=50, cmap="viridis"
        )
        cs = ax[ii].contour(
            wm_ref_vec,
            Tau_ref_vec,
            data_to_plot.T,
            levels=5,
            colors="k",
            linewidths=0.5,
        )
        ax[ii].plot(wm_ref_vec, Tmax, "r--")

        # cbar = fig.colorbar(c, ax=ax[ii])
        ax[ii].clabel(cs, inline=True, fontsize=8)
        ax[ii].set_title(data_label, fontsize=8, loc="right")
        ax[ii].set_ylabel(r"$\tau_e$ [Nm]")

    # ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    # ax[2].set_ylabel(r"$\tau_e$ [Nm]")
    # ax[2, 0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[-1].set_xlabel(r"$\omega_m$ [rpm]")
    # ax[-1].set_xlabel(r"$\omega_m$ [rpm]")

    fig.suptitle(
        rf"Base values: $I={Ibase:.0f}$ A, $V={Vdc:.0f}$ V, $\tau={TBase:.0f}$ Nm, $soc={soc}$",
        fontsize=8,
    )

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_losses(data: LossMapData, options: PlotOptions = PlotOptions()):
    operating_map = data.operating_map
    Pmos_loss, Psw_loss, Pbatt = (
        data.conduction_w,
        data.switching_w,
        data.battery_w,
    )
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 2.5),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    # wm_grid, _ = np.meshgrid(wm_ref_vec, Tau_ref_vec, indexing="ij")

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    cf = ax[0].contourf(wm_ref_vec, Tau_ref_vec, Pmos_loss.T, levels=50, cmap="viridis")
    cl = ax[0].contour(
        wm_ref_vec, Tau_ref_vec, Pmos_loss.T, levels=5, colors="k", linewidths=0.5
    )
    ax[0].clabel(cl, inline=True, fontsize=8)
    ax[0].plot(wm_ref_vec, Tmax, "r--")
    ax[0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[0].set_title(r"$P_\mathrm{on}^l [kW]$", fontsize=8, loc="left")

    cf = ax[1].contourf(wm_ref_vec, Tau_ref_vec, Psw_loss.T, levels=50, cmap="viridis")
    cl = ax[1].contour(
        wm_ref_vec, Tau_ref_vec, Psw_loss.T, levels=5, colors="k", linewidths=0.5
    )
    ax[1].clabel(cl, inline=True, fontsize=8)
    ax[1].plot(wm_ref_vec, Tmax, "r--")
    ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1].set_title(r"$P_\mathrm{sw}^l [kW]$", fontsize=8, loc="left")

    cf = ax[2].contourf(wm_ref_vec, Tau_ref_vec, Pbatt.T, levels=50, cmap="viridis")
    cl = ax[2].contour(
        wm_ref_vec, Tau_ref_vec, Pbatt.T, levels=5, colors="k", linewidths=0.5
    )
    ax[2].clabel(cl, inline=True, fontsize=8)
    ax[2].plot(wm_ref_vec, Tmax, "r--")
    ax[2].set_ylabel(r"$\tau_e$ [Nm]")
    ax[2].set_xlabel(r"$\omega_m$ [rpm]")
    ax[2].set_title(r"$P_\mathrm{b}^l [kW]$", fontsize=8, loc="left")

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_efficiency(data: EfficiencyMapData, options: PlotOptions = PlotOptions()):
    operating_map = data.operating_map
    eff_cond, eff_sw, eff_batt = data.conduction, data.switching, data.battery
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 2.5),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    # wm_grid, _ = np.meshgrid(wm_ref_vec, Tau_ref_vec, indexing="ij")

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    cf = ax[0].contourf(wm_ref_vec, Tau_ref_vec, eff_cond.T, levels=50, cmap="viridis")
    cl = ax[0].contour(
        wm_ref_vec, Tau_ref_vec, eff_cond.T, levels=5, colors="k", linewidths=0.5
    )
    ax[0].clabel(cl, inline=True, fontsize=8)
    ax[0].plot(wm_ref_vec, Tmax, "r--")
    ax[0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[0].set_title(r"$\eta_\mathrm{on}$ [%]", fontsize=8, loc="left")

    cf = ax[1].contourf(wm_ref_vec, Tau_ref_vec, eff_sw.T, levels=50, cmap="viridis")
    cl = ax[1].contour(
        wm_ref_vec, Tau_ref_vec, eff_sw.T, levels=5, colors="k", linewidths=0.5
    )
    ax[1].clabel(cl, inline=True, fontsize=8)
    ax[1].plot(wm_ref_vec, Tmax, "r--")
    ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1].set_title(r"$\eta_\mathrm{sw}$ [%]", fontsize=8, loc="left")

    cf = ax[2].contourf(wm_ref_vec, Tau_ref_vec, eff_batt.T, levels=50, cmap="viridis")
    cl = ax[2].contour(
        wm_ref_vec, Tau_ref_vec, eff_batt.T, levels=5, colors="k", linewidths=0.5
    )
    ax[2].clabel(cl, inline=True, fontsize=8)
    ax[2].plot(wm_ref_vec, Tmax, "r--")
    ax[2].set_ylabel(r"$\tau_e$ [Nm]")
    ax[2].set_xlabel(r"$\omega_m$ [rpm]")
    ax[2].set_title(r"$\eta_\mathrm{b}$ [%]", fontsize=8, loc="left")

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_Tc_and_Tj(data: TemperatureMapData, options: PlotOptions = PlotOptions()):
    operating_map = data.operating_map
    Tj, Tc = data.junction_c, data.case_c
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        2,
        1,
        figsize=(textwidth, textwidth / goldenratio * 1.2),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    cf = ax[0].contourf(wm_ref_vec, Tau_ref_vec, Tc.T, levels=50, cmap="viridis")
    cl = ax[0].contour(
        wm_ref_vec, Tau_ref_vec, Tc.T, levels=5, colors="k", linewidths=0.5
    )
    ax[0].clabel(cl, inline=True, fontsize=8)
    ax[0].plot(wm_ref_vec, Tmax, "r--")
    ax[0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[0].set_title(r"$T_\mathrm{c}$ [°C]", fontsize=8, loc="left")

    cf = ax[1].contourf(wm_ref_vec, Tau_ref_vec, Tj.T, levels=50, cmap="viridis")
    cl = ax[1].contour(
        wm_ref_vec, Tau_ref_vec, Tj.T, levels=5, colors="k", linewidths=0.5
    )
    ax[1].clabel(cl, inline=True, fontsize=8)
    ax[1].plot(wm_ref_vec, Tmax, "r--")
    ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1].set_xlabel(r"$\omega_m$ [rpm]")
    ax[1].set_title(r"$T_\mathrm{j}$ [°C]", fontsize=8, loc="left")

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_total_loss_comparison(
    data: TotalLossMapData_comparison, options: PlotOptions = PlotOptions()
):
    operating_map = data.operating_map
    total_loss_case_1, eff_case_1 = (
        data.total_loss_w_case_1,
        data.efficiency_case_1,
    )
    total_loss_case_2, eff_case_2 = (
        data.total_loss_w_case_2,
        data.efficiency_case_2,
    )
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 1.7),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    cf = ax[0].contourf(
        wm_ref_vec, Tau_ref_vec, total_loss_case_1.T / 1e3, levels=50, cmap="viridis"
    )
    cl = ax[0].contour(
        wm_ref_vec,
        Tau_ref_vec,
        total_loss_case_1.T / 1e3,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[0].clabel(cl, inline=True, fontsize=8)
    ax[0].plot(wm_ref_vec, Tmax, "r--")
    ax[0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[0].set_title(
        rf"$P_{{\mathrm{{tot}}}}^{{\mathrm{{l}}}}$: {data.str_case1} [kW]",
        fontsize=8,
        loc="left",
    )

    cf = ax[1].contourf(
        wm_ref_vec, Tau_ref_vec, total_loss_case_2.T / 1e3, levels=50, cmap="viridis"
    )
    cl = ax[1].contour(
        wm_ref_vec,
        Tau_ref_vec,
        total_loss_case_2.T / 1e3,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[1].clabel(cl, inline=True, fontsize=8)
    ax[1].plot(wm_ref_vec, Tmax, "r--")
    ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1].set_title(
        rf"$P_{{\mathrm{{tot}}}}^{{\mathrm{{l}}}}$: {data.str_case2} [kW]",
        fontsize=8,
        loc="left",
    )

    ax[2].contourf(
        wm_ref_vec,
        Tau_ref_vec,
        (total_loss_case_1 - total_loss_case_2).T / 1e3,
        levels=50,
        cmap="viridis",
    )
    cl = ax[2].contour(
        wm_ref_vec,
        Tau_ref_vec,
        (total_loss_case_1 - total_loss_case_2).T / 1e3,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[2].clabel(cl, inline=True, fontsize=8)
    ax[2].plot(wm_ref_vec, Tmax, "r--")
    ax[2].set_ylabel(r"$\tau_e$ [Nm]")
    ax[2].set_title(
        rf"$\Delta P_{{\mathrm{{tot}}}}^{{\mathrm{{l}}}}$: {data.str_case1} - {data.str_case2} [kW]",
        fontsize=8,
        loc="left",
    )

    ax[-1].set_xlabel(r"$\omega_m$ [rpm]")

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_total_efficiency_comparison(
    data: TotalLossMapData_comparison, options: PlotOptions = PlotOptions()
):
    operating_map = data.operating_map
    eff_case_1, eff_case_2 = data.efficiency_case_1, data.efficiency_case_2
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 1.7),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    Tmax = PBase / (wm_ref_vec * 2 * np.pi / 60)
    Tmax[Tmax > TBase] = TBase

    cf = ax[0].contourf(
        wm_ref_vec, Tau_ref_vec, eff_case_1.T * 100, levels=50, cmap="viridis"
    )
    cl = ax[0].contour(
        wm_ref_vec,
        Tau_ref_vec,
        eff_case_1.T * 100,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[0].clabel(cl, inline=True, fontsize=8)
    ax[0].plot(wm_ref_vec, Tmax, "r--")
    ax[0].set_ylabel(r"$\tau_e$ [Nm]")
    ax[0].set_title(
        rf"$\eta_{{\mathrm{{tot}}}}^{{\mathrm{{l}}}}$: {data.str_case1} [%]",
        fontsize=8,
        loc="left",
    )

    cf = ax[1].contourf(
        wm_ref_vec, Tau_ref_vec, eff_case_2.T * 100, levels=50, cmap="viridis"
    )
    cl = ax[1].contour(
        wm_ref_vec,
        Tau_ref_vec,
        eff_case_2.T * 100,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[1].clabel(cl, inline=True, fontsize=8)
    ax[1].plot(wm_ref_vec, Tmax, "r--")
    ax[1].set_ylabel(r"$\tau_e$ [Nm]")
    ax[1].set_title(
        rf"$\eta_{{\mathrm{{tot}}}}^{{\mathrm{{l}}}}$: {data.str_case2} [%]",
        fontsize=8,
        loc="left",
    )

    ax[2].contourf(
        wm_ref_vec,
        Tau_ref_vec,
        (eff_case_1 - eff_case_2).T * 100,
        levels=50,
        cmap="viridis",
    )
    cl = ax[2].contour(
        wm_ref_vec,
        Tau_ref_vec,
        (eff_case_1 - eff_case_2).T * 100,
        levels=5,
        colors="k",
        linewidths=0.5,
    )
    ax[2].clabel(cl, inline=True, fontsize=8)
    ax[2].plot(wm_ref_vec, Tmax, "r--")
    ax[2].set_ylabel(r"$\tau_e$ [Nm]")
    ax[2].set_title(
        rf"$\Delta \eta$: {data.str_case1} - {data.str_case2} [%]",
        fontsize=8,
        loc="left",
    )

    ax[2].set_xlabel(r"$\omega_m$ [rpm]")

    despine(fig=fig)

    if options.save_path is not None:
        fig.savefig(options.save_path, dpi=200)

    return fig


def plot_individual_loss_comparison(
    data: IndividualLossMapData_comparison, options: PlotOptions = PlotOptions()
):
    operating_map = data.operating_map
    cond_case_1, sw_case_1, batt_case_1 = (
        data.conduction_w_case_1,
        data.switching_w_case_1,
        data.battery_w_case_1,
    )
    cond_case_2, sw_case_2, batt_case_2 = (
        data.conduction_w_case_2,
        data.switching_w_case_2,
        data.battery_w_case_2,
    )
    wm_ref_vec, Tau_ref_vec = operating_map.speed_rpm, operating_map.torque_nm
    PBase, TBase = operating_map.base_power_w, operating_map.base_torque_nm

    fig, ax = plt.subplots(
        3,
        1,
        figsize=(textwidth, textwidth / goldenratio * 2.5),
        sharex=True,
        layout="constrained",
        num=options.figure_number,
        clear=True,
    )

    for ii, (data_case_1, data_case_2, label_case_1, label_case_2, title) in enumerate(
        zip(
            [cond_case_1, sw_case_1, batt_case_1],
            [cond_case_2, sw_case_2, batt_case_2],
            [data.str_case1] * 3,
            [data.str_case2] * 3,
            [
                r"$P_\mathrm{on}^l$ [kW]",
                r"$P_\mathrm{sw}^l$ [kW]",
                r"$P_\mathrm{b}^l$ [kW]",
            ],
        )
    ):
        cf = ax[ii].contourf(
            wm_ref_vec,
            Tau_ref_vec,
            data_case_1.T - data_case_2.T,
            levels=50,
            cmap="viridis",
        )
        cl = ax[ii].contour(
            wm_ref_vec,
            Tau_ref_vec,
            data_case_1.T - data_case_2.T,
            levels=5,
            colors="k",
            linewidths=0.5,
        )
        ax[ii].clabel(cl, inline=True, fontsize=8)
        ax[ii].set_ylabel(r"$\tau_e$ [Nm]")
        ax[ii].set_title(
            rf"{title}: {label_case_1} - {label_case_2}", fontsize=8, loc="left"
        )

    ax[-1].set_xlabel(r"$\omega_m$ [rpm]")

    despine(fig=fig)

    return fig
