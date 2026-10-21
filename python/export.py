"""Export of the data behind the dashboard plots to one Excel workbook.

Every sheet holds the data of one figure (or group of figures). Speed-torque maps are
written in long format: one row per (speed, torque) grid point and one column per plotted
quantity, so each column can be reshaped into the map shown in the figure. NaN (points that
are infeasible or not plotted, e.g. efficiency below the plot threshold) are left empty.
"""

from pathlib import Path

import numpy as np
import pandas as pd

import plots as dpf

SHEET_NAME_MAX = 31  # Excel limit


def map_frame(operating_map: dpf.OperatingMap, **quantities) -> pd.DataFrame:
    """Long-format table of speed x torque maps; each array has shape (speed, torque)."""
    speed, torque = np.meshgrid(
        operating_map.speed_rpm, operating_map.torque_nm, indexing="ij"
    )
    columns = {"speed_rpm": speed.ravel(), "torque_Nm": torque.ravel()}
    for name, values in quantities.items():
        columns[name] = np.asarray(values, dtype=float).ravel()
    return pd.DataFrame(columns)


def mtpa_frames(data: dpf.MtpaMapData) -> dict[str, pd.DataFrame]:
    """Data of plot_mtpa_maps and plot_mtpa_maps_dqs (same normalisation as the plots)."""
    Id, Iq, Vd, Vq = data.id_current, data.iq_current, data.d_voltage, data.q_voltage
    Vdc, Ibase = data.dc_voltage, data.base_current
    return {
        "MTPA_dq": map_frame(
            data.operating_map,
            id_pu=Id / Ibase,
            iq_pu=Iq / Ibase,
            vd_pu=Vd / Vdc,
            vq_pu=Vq / Vdc,
        ),
        "MTPA_magnitude": map_frame(
            data.operating_map,
            idq_pu=(Id**2 + Iq**2) ** 0.5 / Ibase,
            vdq_pu=(Vd**2 + Vq**2) ** 0.5 / Vdc,
            cos_phi=np.cos(np.arctan2(Vq, Vd) - np.arctan2(Iq, Id)),
        ),
    }


def converter_frames(key, conv, operating_map) -> dict[str, pd.DataFrame]:
    """Loss, temperature and efficiency maps of one converter ('2l' or 'bimmc')."""
    tag = {"2l": "2L", "bimmc": "BIMMC"}[key]
    eff_c, eff_s, eff_b, eff_tot = conv["eff"]
    return {
        f"{tag}_losses": map_frame(
            operating_map,
            conduction_kW=conv["Pc"] / 1e3,
            switching_kW=conv["Ps"] / 1e3,
            battery_kW=conv["Pb"] / 1e3,
            total_kW=conv["Ploss"] / 1e3,
        ),
        f"{tag}_temperatures": map_frame(
            operating_map,
            Tcase_C=conv["Tc"],
            Tjunction_C=conv["Tj"],
            Tcell_C=conv["Tcell"],
        ),
        f"{tag}_efficiency": map_frame(
            operating_map,
            conduction_pct=eff_c * 100,
            switching_pct=eff_s * 100,
            battery_pct=eff_b * 100,
            total_pct=eff_tot * 100,
        ),
    }


def comparison_frames(c2l, cb, operating_map) -> dict[str, pd.DataFrame]:
    """Data of the 2L vs BI-MMC comparison plots (positive difference = BI-MMC better)."""
    parts = ("Pc", "Ps", "Pb")
    names = ("conduction", "switching", "battery")
    loss, eff = {}, {}
    for part, name in zip(parts, names):
        loss[f"{name}_2L_kW"] = c2l[part] / 1e3
        loss[f"{name}_BIMMC_kW"] = cb[part] / 1e3
        loss[f"{name}_diff_2L-BIMMC_kW"] = (c2l[part] - cb[part]) / 1e3
    for i, name in enumerate(names):
        eff[f"{name}_2L_pct"] = c2l["eff"][i] * 100
        eff[f"{name}_BIMMC_pct"] = cb["eff"][i] * 100
        eff[f"{name}_diff_BIMMC-2L_pp"] = (cb["eff"][i] - c2l["eff"][i]) * 100
    return {
        "Comparison_total": map_frame(
            operating_map,
            loss_2L_kW=c2l["Ploss"] / 1e3,
            loss_BIMMC_kW=cb["Ploss"] / 1e3,
            loss_diff_2L_minus_BIMMC_kW=(c2l["Ploss"] - cb["Ploss"]) / 1e3,
            efficiency_2L_pct=c2l["eff"][3] * 100,
            efficiency_BIMMC_pct=cb["eff"][3] * 100,
            efficiency_diff_BIMMC_minus_2L_pp=(cb["eff"][3] - c2l["eff"][3]) * 100,
        ),
        "Comparison_individual_loss": map_frame(operating_map, **loss),
        "Comparison_individual_eff": map_frame(operating_map, **eff),
    }


def write_workbook(path, sheets: dict[str, pd.DataFrame]) -> Path:
    """Write the sheets to an .xlsx file (the first sheet is usually the parameter list)."""
    path = Path(path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:SHEET_NAME_MAX], index=False)
            sheet = writer.sheets[name[:SHEET_NAME_MAX]]
            for col in sheet.columns:  # readable column widths
                width = max(len(str(cell.value)) for cell in col[:50] if cell.value is not None)
                sheet.column_dimensions[col[0].column_letter].width = min(width + 2, 45)
    return path
