# `cycle_eval.py` – documentation

Time-domain loss evaluation of the two-level inverter (2L) and the BI-MMC drive over a duty cycle.

The script no longer builds efficiency/loss maps and interpolates them. At **every time step** of the cycle it

1. takes the requested speed and torque from the cycle,
2. finds the MTPA currents for the voltage the battery can supply *at the present SOC*,
3. evaluates the loss models of `calc.py` (`calc_losses_2l`, `calc_losses_bimmc`) for that point,
4. updates the SOC of each pack from the power drawn from its cells.

The user chooses the **application** and the **initial SOC**. The output is the instantaneous conduction (`Pc`), switching (`Ps`) and battery (`Pb`) loss of both converters, plus the SOC trajectory.

---

## 1. Usage

```bash
# command line: all applications at three initial SOCs (default)
python cycle_eval.py

# one application, one initial SOC
python cycle_eval.py --apps car --soc 0.9

# from Python
import cycle_eval as ce
res, trace = ce.evaluate_cycle("bus", soc0=0.8)
```

| Argument | Meaning | Default |
|---|---|---|
| `--apps` | keys of `applications.APPLICATIONS` (`car bus truck offroad marine train`) | all |
| `--soc` | one or more **initial** SOC values, 0–1 | `0.2 0.5 0.9` |
| `--jobs` | number of parallel processes (one per application/SOC pair) | CPU count |

### Output (in `python/results_cycles/`)

| File | Content |
|---|---|
| `losses_<app>_soc<NN>.csv` | per-time-step trace (columns below), one file per application and initial SOC |
| `cycle_results.xlsx` / `.json` | one summary row per application and initial SOC (energies, efficiencies, final SOC) |

Columns of the trace (`<c>` is `2l` or `bimmc`):

| Column | Unit | Meaning |
|---|---|---|
| `t`, `dt` | s | time and step length of the cycle |
| `wm` | rad/s | machine speed |
| `T_req` | N·m | torque requested by the cycle |
| `T` | N·m | torque actually delivered (after the power / voltage / current limits) |
| `P` | W | mechanical power `wm·T` (negative = regeneration) |
| `soc_<c>` | – | SOC of that converter's pack at the **start** of the step |
| `Pc_<c>`, `Ps_<c>`, `Pb_<c>` | W | conduction, switching, battery loss |
| `Ploss_<c>` | W | `Pc + Ps + Pb` |
| `Tj_<c>` | °C | junction temperature from the steady-state thermal model |
| `infeasible` | – | `True` if no MTPA solution exists at that point (losses set to 0) |

---

## 2. Modelling assumptions

* **Each converter has its own SOC.** Both packs start at `soc0` but discharge differently because their losses differ.
* **SOC update.** The power drawn from the cells' open-circuit source is `P + Pc + Ps + Pb` (negative while regenerating). The cell current is that power divided by `N_cells · Vcell(SOC)`. SOC then changes by `−I_cell·dt / (3600·Qcell)` and is clipped to 0–1. `N_cells` is the total cell count of the pack.
* **SOC changes everything downstream.** `cell_state` gives the cell OCV and `R0`, `R1`, `C1` at the current SOC. The OCV sets the DC-link voltage of the 2L (`Vcell·Nscells_2l`) and the submodule voltage of the BI-MMC (`Vcell·Nscells_b`). It also sets the voltage limit of the MTPA problem, so the torque–speed envelope shrinks as the pack discharges.
* **Same delivered torque for both drives.** If the requested torque is outside either converter's envelope, both deliver the smaller of the two feasible torques, so the comparison uses identical mechanical work.
* **No machine losses.** As in `calc.py`, motor copper/iron losses are not included, so the mechanical power `wm·T` is taken as the inverter output.
* **Standstill.** `wm = 0` and `T = 0` means the converter is off (all losses 0). `wm = 0` with torque is evaluated, but the BI-MMC battery model needs an electrical cycle, so its speed is floored (see `MIN_FSW_BIMMC`).
* **Large steps.** The ISO 8178 marine cycle consists of four steady modes with steps of several hundred seconds. The SOC is integrated with explicit Euler over those steps, which is acceptable at those loads but not a fine time resolution.

---

## 3. File walkthrough

### 3.1 Module docstring (lines 1–15)
States the purpose, the command-line usage and the Python entry point `evaluate_cycle`.

### 3.2 Imports and environment (lines 17–31)

| Line | Statement | Purpose |
|---|---|---|
| 17–19 | `argparse`, `json`, `os` | command-line parsing, writing the JSON summary, CPU count and environment variables |
| 20 | `ProcessPoolExecutor` | runs the application/SOC cases in parallel processes |
| 21 | `Path` | platform-independent paths |
| 23 | `os.environ.setdefault("TQDM_DISABLE", "1")` | `calc_losses_bimmc` draws a `tqdm` progress bar for every call. Evaluated once per time step this would flood the terminal, so it is disabled before `calc` is imported. `setdefault` lets the user override it. |
| 25–26 | `numpy`, `pandas` | arrays; trace and summary tables |
| 28 | `applications as apps` | application presets (drive parameters, vehicle, cycle) |
| 29 | `calc as daf` | the loss models and the MTPA problem builder |
| 30 | `cycles` | converts a cycle into machine speed/torque time series |
| 31 | `model` | drive design, cell model, MOSFET data |

### 3.3 Constants (lines 33–38)

| Line | Constant | Meaning |
|---|---|---|
| 33 | `RESULTS_DIR` | `results_cycles/` next to the script |
| 34 | `CONVERTERS` | the two drives, used as dictionary keys and column suffixes |
| 35 | `COMPONENTS` | loss components: `Pc` conduction, `Ps` switching, `Pb` battery |
| 36–37 | `MIN_FSW_BIMMC` (50 Hz) | `calc_losses_bimmc` simulates the battery RC network with explicit Euler and a step of `1/(100·fsw)`. When `fsw` is a few Hz the step exceeds the RC time constant (about 0.8 ms) and the simulation diverges. Speeds that would give a lower `fsw` are therefore raised to the speed that gives 50 Hz. |
| 38 | `N_BISECT` | number of bisection steps used to find the feasible torque (resolution ≈ 0.1 % of the requested torque) |

### 3.4 Loss maps (lines 41–58)
Kept **only** because `doc/figures/make_cycle_figures.py` still draws background loss maps with them. The cycle evaluation itself does not use them.

* `map_path(app_key, soc, n_speed, n_torque)` – file name of a cached map (`maps_<app>_soc<NN>_<ns>x<nt>.npz`).
* `compute_maps(app_key, soc, n_speed, n_torque, recompute)` – loads the cached map if it exists (unless `recompute`). Otherwise it builds the speed/torque grid with `model.default_grid`, runs `model.loss_maps`, saves the result as compressed `.npz` and returns it.

### 3.5 `make_mtpa_solver(d)` (line 65)
Returns the CasADi/IPOPT problem from `daf.create_mtpa_optimization_problem(d.motor)`, i.e. the tuple `(opti, x, (Tau_ref, wm_ref, v_lim))`. It minimises `Id²+Iq²` subject to the torque equation and the voltage-circle constraint. It is created **once per converter** and reused for every step, so IPOPT can warm-start from the previous solution.

### 3.6 `mtpa_point(solver, d, wm, T, vmax)` (lines 70–88)

| Step | What it does |
|---|---|
| unpack | gets the optimiser, the decision variable `x = [Id, Iq]` and the three parameters |
| `set_value` ×3 | sets the voltage limit `vmax` [V], the torque `T` [N·m] and the speed `wm` [rad/s] |
| `opti.solve()` | solves; if IPOPT fails (`RuntimeError`) the initial guess is reset to zero and `None` is returned |
| `Id, Iq` | reads the solution as floats |
| `set_initial` | stores the solution as warm start for the next call |
| current check | if `Id²+Iq² > Ibase²` (the peak current limit) the point is rejected (`None`) |
| return | `(Id, Iq)` in A, or `None` if infeasible |

### 3.7 `feasible_torque(solver, d, wm, T_req, vmax)` (lines 91–110)
Finds the torque the converter can actually deliver at this speed and voltage limit.

1. Try the requested torque (`mtpa_point`). If it works, return it.
2. Otherwise bisect between `lo = 0` (assumed feasible) and `hi = T_req` for `N_BISECT` iterations. A feasible midpoint raises `lo` and is remembered as `best`; an infeasible one lowers `hi`.
3. If no midpoint was ever feasible, try `T = 0`. This can still return `None` if the voltage is too low even for flux weakening at this speed and SOC.
4. Return `(torque, (Id, Iq))`.

The sign of `T_req` is preserved because `lo` and `hi` carry the sign.

### 3.8 `losses_2l(p, d, mosfet, cell, wm, Id, Iq, rdson_iter=5)` (lines 117–141)
Instantaneous 2L losses at one operating point, using `daf.calc_losses_2l`.

| Step | What it does |
|---|---|
| unpack | `slopes, rdson_fun = mosfet` (switching-slope functions and normalised `Rdson(Tj)`); `Vcell, R0, R1, C1 = cell` |
| `V_dc` | DC-link voltage = cell voltage × series cells; this is the SOC-dependent link voltage |
| 1×1 arrays | `calc_losses_2l` is vectorised for maps. The currents are wrapped as 1×1 arrays so one function serves both uses |
| `_dq_voltages` | d/q voltages from the machine equations (`R·I` plus the speed-voltage terms) |
| `thermal`, `battery` | parameter containers for `calc_losses_2l`; the battery gets `R0, R1, C1` of the present SOC |
| loop `rdson_iter` | the conduction loss depends on `Rdson(Tj)` and `Tj` depends on the loss. The fixed-point iteration `Tj → Rdson → Pcond → Tj` is repeated 5 times, starting with the 25 °C datasheet value |
| `daf.calc_losses_2l` | returns conduction `Pc`, switching `Ps`, battery `Pb`, `Tj` and `Tc` (case temperature, not used here) |
| return | four floats: `Pc, Ps, Pb` [W], `Tj` [°C] |

### 3.9 `losses_bimmc(p, d, cell, wm, T, Id, Iq)` (lines 144–174)
Instantaneous BI-MMC losses with `daf.calc_losses_bimmc`.

| Step | What it does |
|---|---|
| `wm_eff` | speed floor so that the switching frequency is at least `MIN_FSW_BIMMC` (see 3.3). Standstill and creep speeds are therefore evaluated as if at about 20 Hz switching |
| `Vs_b` | submodule voltage = cell voltage × series cells per submodule |
| `_dq_voltages` | d/q voltages at `wm_eff` |
| `calc_losses_bimmc(...)` | called with 1×1 arrays and one-element speed/torque vectors. It uses `Nsm`, the redundancy, `Vs_b`, `Rdson`, the number of parallel MOSFETs, `fsw = mf·we/2π`, thermal parameters, switching slopes and the battery parameters at the present SOC |
| battery loss | inside `calc_losses_bimmc` the cell RC network is simulated over two electrical cycles with the actual submodule gating (carrier vs. reference) and the average of the second cycle is used |
| return | four floats: `Pc, Ps, Pb` [W], `Tj` [°C] |

### 3.10 `evaluate_cycle(app_key, soc0, rdson_iter=5)` (lines 177–281)
The main routine. Returns `(summary dict, trace DataFrame)`.

**Setup (lines 177–196)**

| Statement | Meaning |
|---|---|
| `app`, `p`, `d` | application preset, drive parameters (`NOMINAL` format) and derived design (`model.design`) |
| `prof = cycles.machine_profile(app)` | machine speed `wm`, torque `T`, time step `dt`, time `t` and vehicle speed `v` of the cycle |
| `wm_all = clip(wm, 0, d.wmMax)` | speed is limited to the maximum speed of the drive |
| `T_req_all`, `dt_all` | requested torque and step lengths |
| `mosfet = model.mosfet_data(p)` | MOSFET slope functions and `Rdson(Tj)`, computed once |
| `solver` | one MTPA problem per converter |
| `r` | redundant-submodule fraction of the BI-MMC |
| `n_cells` | total number of cells of each pack: `Nscells_2l·Npcells_2l` for the 2L, `3·Nsm·Nscells_b·Npcells_b` for the BI-MMC |
| `soc` | SOC of each pack, both initialised with `soc0` |
| `rows` | list collecting one dict per step |

**Time loop (line 197 onward)** – one iteration per cycle sample:

1. **Cell state** – `cell_state(p, soc[c])` gives `(Vcell, R0, R1, C1)` at the present SOC of each pack. `row` starts with the inputs and the SOC at the beginning of the step.
2. **Idle** (line 200) – zero torque at zero speed turns the converter off: `T = 0`, all losses 0, `Tj = ambient`.
3. **Otherwise** –
   * `vmax` – phase-voltage limits at the present SOC. 2L: `Vcell·Nscells_2l/√3` (SVPWM). BI-MMC: `Vcell·Nscells_b·Nsm·(1−r)`, the string voltage of a phase leg minus the redundant submodules.
   * `T_lim`, `T_cmd` – the requested torque is clipped to the rated power `PBase` (`|wm·T| ≤ PBase`; the `(1−1e-9)` factor avoids rounding above the limit).
   * `sol` – `feasible_torque` for each converter at its own voltage limit.
   * `T` – the smaller magnitude of the two feasible torques, with the sign of the command, so both drives deliver the same torque.
   * `currents` loop – a converter that could deliver more than `T` is solved again at `T` (otherwise the stored solution is reused). `ok` becomes `False` if any current is `None`.
   * losses – if `ok`, `losses_2l` and `losses_bimmc` are called with the MTPA currents. If not, losses are set to 0 with `Tj = NaN` and the step is flagged `infeasible`.
4. **Record and SOC update** – `P = wm·T`. For each converter the losses go into `row`; `Ploss_<c>` is their sum; `I_cell = (P + Pc + Ps + Pb)/(n_cells·Vcell)` is the average cell current (sign: positive = discharge); SOC is updated with `−I_cell·dt/(3600·Qcell)` and clipped to 0–1. The new SOC is used in the next step.

**Post-processing (lines 240–281)**

| Statement | Meaning |
|---|---|
| `trace = DataFrame(rows)`, `insert(0, "t", ...)` | the per-step table, with the time as first column |
| `dt, wm, T, P` | arrays taken from the trace |
| `P_req = wm·T_req_all` | requested mechanical power, used to quantify clipped energy |
| `E(x)` | integrates a power [W] over `dt` and converts W·s to kWh (÷ 3.6·10⁶) |
| `res` – identification | application key, label, cycle name, `soc_start`, final SOC of each pack (`soc_end_2l`, `soc_end_bimmc`), duration, distance (`None` for cycles without a vehicle speed) |
| `res` – mechanical energy | motoring and regeneration energy actually delivered; the part of the request that was clipped; `n_infeasible` = number of steps without a feasible operating point |
| `share_below_base_speed` | fraction of the mechanical energy delivered at or below base speed, i.e. without field weakening |
| `gear_ratio` | gear ratio of the application (only for applications with a wheel radius) |
| loss loop | for each converter the energy of every component, `E_<c>_<conv>_kWh`, and their sum `E_loss_<conv>_kWh` |
| `eta_cycle_<conv>` | `1 − E_loss / (E_motoring + E_regen)`: losses charged to the throughput |
| `E_batt_net_<conv>_kWh` | net energy taken from the cells: motoring − regeneration + losses |
| `delta_eta_pp` | efficiency difference BI-MMC − 2L in percentage points |
| `delta_loss_pct` | relative loss difference BI-MMC vs. 2L in % |
| `kWh_per_100km_<conv>` | net consumption per 100 km, only if the cycle has a distance |

### 3.11 `_job(args)` (lines 283–287)
Worker for the process pool: unpacks `(app_key, soc0)`, runs `evaluate_cycle`, writes the trace to `losses_<app>_soc<NN>.csv` and returns the summary dict. Defined at module level so it can be pickled.

### 3.12 `main()` (lines 290 onward)

| Statement | Meaning |
|---|---|
| `ArgumentParser` | defines `--apps`, `--soc`, `--jobs` (section 1); the description is the first line of the module docstring |
| `RESULTS_DIR.mkdir(exist_ok=True)` | creates the output folder |
| `jobs` | every (application, initial SOC) combination |
| `ProcessPoolExecutor.map(_job, jobs)` | evaluates the cases in parallel; results come back in job order |
| `DataFrame(rows)` | summary table of all cases |
| `to_excel`, `write_text(json.dumps(...))` | writes `cycle_results.xlsx` and `cycle_results.json` |
| `cols` + `pd.option_context` | prints a compact summary (initial and final SOC, losses, efficiencies, number of infeasible steps) |
| `if __name__ == "__main__"` | runs `main()` only when executed as a script, not when imported |

---

## 4. Truck application (Södertälje–Norrköping)

The `truck` application no longer uses the WHVC. Its vehicle and cycle come from `so_no/`:

* **Vehicle** – `applications._truck_vehicle()` reads `so_no/vehicle_params.mat`: mass 40 t, `CdA = C_d·A`, rolling resistance `c_r0 + c_r1·v`, air density, gravity and wheel radius 0.5 m. Rotating inertia is neglected (factor 1.0), as in `so_no/truck_sensitivity.py`. Gear efficiency 0.96 is kept from the earlier preset. The gear ratio is sized so that the 80 km/h cruise speed gives 1 pu machine speed (`cruise_speed_kmh`, `cruise_pu` in the vehicle dict; `applications.gear_ratio`). Other applications still map their top speed to 95 % of the maximum speed.
* **Cycle** – `cycles.road_cycle` reads the road slope vs. distance from `so_no/SoNO_scenario.mat` (118.9 km) and integrates `m·dv/dt = F_ctrl − F_resistance(v, slope)`. `F_ctrl` is a proportional cruise controller (`k_p = 1e4`, set speed 80 km/h, start 20 m/s, wheel-torque limit 7000 N·m). This is the same model as `truck_sensitivity.py`. It gives about 5455 s at 64–84 km/h.
* **Torque** – `apps.road_load_force` now takes the slope: gravity `m·g·sin(slope)`, rolling `(c_r0 + c_r1·v)·m·g·cos(slope)`, drag, plus `m·a`. The wheel force is converted to machine speed and torque as for the other road vehicles. Unlike `truck_sensitivity.py`, which ignores acceleration in the energy figure, `m·a` is included here.
* The route needs up to about 475 kW on the climbs, above the 400 kW rating. `evaluate_cycle` clips this and reports it as `E_clipped_motoring_kWh`.

---

## 5. Practical notes

* **Run time.** About 3 s for the passenger car (1800 steps) with two IPOPT solves per step.
* **`n_infeasible` > 0.** Happens at a low initial SOC when the pack voltage falls too low for the requested speed. The affected steps carry zero loss and the trace flags them.
* **Empty pack.** If SOC reaches 0 the simulation continues with the OCV at 0 % SOC. Use a higher initial SOC or a larger battery if that happens.
* **Reproducing the earlier results.** The old map-based evaluation is gone from the cycle path. The instantaneous evaluation also differs from it in using the SOC-dependent voltage limit at each step and the electrical-speed floor for the BI-MMC battery loss.
* **Figure script.** `doc/figures/make_cycle_figures.py` still calls `compute_maps` and reads `profile_<app>.npz`. The new code does not write that profile file, so the script needs a small update to read `losses_<app>_soc<NN>.csv` instead.
