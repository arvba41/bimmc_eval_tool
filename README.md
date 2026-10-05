# AC Battery & BI-MMC Drive Evaluator

**Explore motor-drive operating maps, estimate losses and temperatures, and compare inverter architectures—all from an interactive engineering dashboard.**

This project brings together a Python dashboard and a collection of MATLAB tools for evaluating battery-integrated motor-drive systems. The Python app makes it easy to vary motor, battery, and power-electronic parameters and see how they affect maximum-torque-per-ampere (MTPA) operation, inverter and battery losses, efficiency, and estimated device temperatures.

Its central comparison is between a conventional **two-level SiC inverter** and a **battery-integrated modular multilevel converter (BI-MMC)**. Change the design inputs, inspect the operating maps, and export plots for further analysis or discussion.

> **This is an engineering analysis and comparison tool—not a validated design, safety assessment, or substitute for device datasheets, detailed simulation, or experimental verification.**

## Why use it?

- **Compare two drive architectures** using the same motor and operating-point analysis.
- **Explore the complete torque–speed envelope** with MTPA current optimization and voltage-constrained operating points.
- **See where the losses come from:** inverter conduction, inverter switching, and battery losses.
- **Visualize thermal estimates** for power-device cases and junctions over the operating map.
- **Adapt the study to your design:** edit motor, inverter, battery, switching, and thermal parameters in the dashboard.
- **Keep a record of results:** figures are generated as PNG files and saved locally.
- **Inspect the model inputs** in the dashboard alongside the calculated parameter values and battery/MOSFET characteristic plots.

## What the dashboard calculates

### MTPA operating maps

For each torque–speed point, the app uses CasADi with the IPOPT solver to minimize the squared d- and q-axis currents subject to the motor torque equation and a voltage constraint. It then plots d/q currents and voltages across the operating map. Points beyond the configured power envelope are not solved, and current-map points above the configured base-current limit are masked.

### Loss, efficiency, and temperature maps

The resulting motor operating points are used to estimate:

- Two-level inverter conduction and switching losses.
- BI-MMC conduction and switching losses.
- Battery losses using an equivalent-circuit model.
- Case and junction temperatures from configured thermal resistances and ambient temperature.
- Loss and efficiency component maps, total-map comparisons, and temperature maps for both architectures.

The dashboard runs the analysis at the selected state of charge (SOC). Available SOC values are 10% through 100% in 10% increments.

## Configure the study

Inputs are grouped in the dashboard sidebar. Typical settings include:

| Area | Configurable inputs |
| --- | --- |
| **Motor (PMSM)** | Pole pairs, base mechanical power and speed, DC-link voltage, per-unit stator resistance, and d/q-axis inductances |
| **Two-level inverter** | Wolfspeed EDB005M12TM4 preset or a customized MOSFET, switching frequency, switching slopes, thermal resistances, ambient temperature, and device limits |
| **Battery** | NMC, LFP, LTO, or sodium-ion (NaB) chemistry; battery energy; Samsung PHEV2 24 Ah or custom cell parameters |
| **BI-MMC** | Submodules per phase, redundant-submodule fraction, MOSFET on-resistance and current rating, switching slopes, pulse number, and thermal resistances |
| **Operating condition** | SOC used for the MTPA, loss, efficiency, and temperature maps |

The app displays derived motor, inverter, battery, and BI-MMC parameters in the **Parameters** tab. The other tabs contain the **MTPA maps** and **Loss and Efficiency maps**.

## Quick start

### Requirements

- Python 3.10 or later.
- The packages listed in [`python/requirements.txt`](python/requirements.txt).
- The bundled MOSFET characteristic files in `python/data/` (included in this repository).

### Install and launch

Run the dashboard from the `python` directory. The working directory matters: the app reads the MOSFET data files from the relative path `data/`.

**macOS / Linux**

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run main.py
```

**Windows PowerShell**

```powershell
cd python
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run main.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) to open in your browser. Stop the app with **Ctrl+C** in the terminal.

## Results

The app creates `python/results_mtpa_soc/` when it runs and writes figures there. Map filenames include the selected SOC—for example, `mtpa_maps_soc_50.png` and `losses_maps_comparison_soc_50.png` for a 50% SOC analysis.

Generated figures include:

- Motor d/q current and voltage MTPA maps.
- Inverter and battery loss maps for each topology.
- Efficiency maps for each topology.
- Case and junction temperature maps.
- Total-loss, efficiency, and component-level architecture comparisons.
- Input characteristic plots for battery OCV and equivalent-circuit parameters, MOSFET switching slopes, and on-resistance versus junction temperature.

The folder is relative to the app's working directory; when launched using the commands above, it is `python/results_mtpa_soc/`.

## Project structure

```text
.
├── README.md
├── python/
│   ├── main.py          # Streamlit dashboard and analysis workflow
│   ├── calc.py          # MTPA, loss, battery, and thermal calculations
│   ├── plots.py         # Map and characteristic plotting
│   ├── requirements.txt
│   ├── data/            # Bundled Wolfspeed device-characteristic data
│   └── logo/            # Dashboard logo assets
└── MATLAB/              # MATLAB app, scripts, and supporting evaluation files
```

The MATLAB directory contains a separate set of dashboard, converter, battery, loss, and optimization materials. See [`MATLAB/README.md`](MATLAB/README.md) for its brief introduction; the Python quick-start instructions above apply to the Streamlit dashboard.

## Modeling scope and interpretation

Results depend on the selected parameters and the assumptions implemented in the calculation models. In particular:

- The motor analysis uses a permanent-magnet synchronous motor (PMSM) model with configured resistance, inductances, flux linkage, and pole-pair count.
- Battery chemistry selection supplies a built-in open-circuit-voltage-versus-SOC curve. The included Samsung cell uses example equivalent-circuit parameters; custom-cell mode lets you enter capacity and RC parameters.
- The two-level inverter can use the bundled Wolfspeed device-characteristic data or user-entered switching and device parameters. BI-MMC switching slopes are entered separately.
- Thermal maps are estimates from the configured loss and thermal-resistance values. Although device temperature limits can be entered, the maps should not be treated as certification that those limits are met.
- The dashboard supports architecture-level exploration; it does not model every control, parasitic, transient, cooling, or electrochemical effect present in a physical system.

Use the maps to compare scenarios and identify trends. Validate assumptions and results against appropriate datasheets, higher-fidelity simulation, and laboratory measurements before using them to make design or safety decisions.

## Troubleshooting

- **The app cannot find a MOSFET CSV file:** launch Streamlit from `python/` (`cd python` first), so the app's relative `data/` paths resolve correctly.
- **A dependency is missing:** activate the virtual environment and install `python/requirements.txt` as shown above.
- **The browser page does not open automatically:** use the local URL printed by Streamlit in the terminal.
- **Optimization or analysis is taking time:** MTPA results are calculated across a torque–speed grid, and BI-MMC battery-loss estimates simulate switching-related current profiles. Runtime depends on your machine and selected parameters.

## Contributing

Contributions that improve model clarity, reproducibility, usability, or validation are welcome. When changing calculations, document the assumptions and units, and include a representative validation case where possible.

## License

No license information is currently provided in this repository. Contact the project maintainers for permission and terms before redistributing or incorporating this software.
