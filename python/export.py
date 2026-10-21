"""Export of the data behind the dashboard plots to one Excel workbook.

Every sheet holds the data of one figure (or group of figures). Speed-torque maps are
written as one block per plotted quantity (torque in rows, speed in columns), stacked
vertically in the sheet of their figure. Points that are infeasible or not plotted (e.g.
efficiency below the plot threshold) are left empty.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import plots as dpf

SHEET_NAME_MAX = 31  # Excel limit


@dataclass(frozen=True)
class MapSheet:
    """Speed-torque maps of one sheet: name -> array of shape (speed, torque)."""

    operating_map: dpf.OperatingMap
    quantities: dict[str, np.ndarray]


def map_frame(operating_map: dpf.OperatingMap, **quantities) -> MapSheet:
    return MapSheet(
        operating_map,
        {name: np.asarray(values, dtype=float) for name, values in quantities.items()},
    )


def _write_map_sheet(sheet, data: MapSheet):
    """One block per quantity, stacked vertically: torque in rows, speed in columns.

    Layout of a block (r = first row, columns from C):
        r      D: "speed_rpm"
        r+1    D..: speed values                      | name of the quantity after the last
        r+2..  C: torque value, D..: values           | speed column
        B (middle row): "torque_Nm"
    """
    speed = np.asarray(data.operating_map.speed_rpm, dtype=float)
    torque = np.asarray(data.operating_map.torque_nm, dtype=float)
    row = 1
    for name, values in data.quantities.items():
        sheet.cell(row, 4, "speed_rpm")
        for i, w in enumerate(speed):
            sheet.cell(row + 1, 4 + i, float(w))
        sheet.cell(row + 1, 4 + len(speed), name)
        sheet.cell(row + 2 + len(torque) // 2, 2, "torque_Nm")
        for j, T in enumerate(torque):
            sheet.cell(row + 2 + j, 3, float(T))
            for i in range(len(speed)):
                v = values[i, j]
                if np.isfinite(v):  # infeasible / not plotted points stay empty
                    sheet.cell(row + 2 + j, 4 + i, float(v))
        row += len(torque) + 4  # one empty row between the blocks
    sheet.column_dimensions["B"].width = 11
    sheet.column_dimensions["C"].width = 11


def mtpa_frames(data: dpf.MtpaMapData) -> dict[str, MapSheet]:
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


def converter_frames(key, conv, operating_map) -> dict[str, MapSheet]:
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


def comparison_frames(c2l, cb, operating_map) -> dict[str, MapSheet]:
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


def write_workbook(path, sheets: dict[str, pd.DataFrame | MapSheet]) -> Path:
    """Write the sheets to an .xlsx file: tables as columns, MapSheets as torque x speed grids."""
    path = Path(path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, data in sheets.items():
            name = name[:SHEET_NAME_MAX]
            if isinstance(data, MapSheet):
                _write_map_sheet(writer.book.create_sheet(name), data)
                continue
            data.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            for col in sheet.columns:  # readable column widths
                width = max(len(str(cell.value)) for cell in col[:50] if cell.value is not None)
                sheet.column_dimensions[col[0].column_letter].width = min(width + 2, 45)
    return path
