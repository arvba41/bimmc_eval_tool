# Standard drive and duty cycles

This folder holds four public test cycles as plain CSV files: comma-separated, a header row, 1 Hz, and no index column.
Each file comes from a regulatory or well-known public source. No values were synthesised, smoothed, or resampled.
Distance is the trapezoidal integral of speed over the sample times as given.

Retrieved on 2026-10-16. The raw downloads were kept outside the repository.

| File | Samples | Time span | Max | Distance | Reference |
|---|---|---|---|---|---|
| `wltc_class3b.csv` | 1801 | 0 to 1800 s | 131.3 km/h | 23.266 km | about 23.27 km, 131.3 km/h |
| `whvc.csv` | 1800 | 1 to 1800 s | 87.80 km/h | 20.072 km | about 20.1 km, about 87.8 km/h |
| `braunschweig.csv` | 1741 | 0 to 1740 s | 58.26 km/h | 10.874 km | about 10.9 km, about 58.2 km/h, 1740 s |
| `nrtc.csv` | 1238 | 1 to 1238 s | speed 105 %, torque 100 % | n/a | 1238 s |

---

## `wltc_class3b.csv`: WLTC Class 3b

- **Columns:** `time_s,speed_kmh`, with speed at 0.1 km/h resolution, as in the regulation.
- **Regulation:** UN GTR No. 15 (WLTP), Annex 1, Class 3b cycle. The phases are Low, Medium 3b, High 3b and Extra-High 3.
- **Source:** the JRC `wltp` project, commit `18650f37`.
  - https://raw.githubusercontent.com/JRCSTU/wltp/master/bin/data/class3-1-Low.csv
  - https://raw.githubusercontent.com/JRCSTU/wltp/master/bin/data/class3-2b-Medium.csv
  - https://raw.githubusercontent.com/JRCSTU/wltp/master/bin/data/class3-3b-High.csv
  - https://raw.githubusercontent.com/JRCSTU/wltp/master/bin/data/class3-4-ExtraHigh.csv
- **Transformations:** the four phase files were concatenated. Their time stamps were already continuous from 0 to 1800 s.
- **Cross-check:** compared against NREL FASTSim `python/fastsim/resources/cycles/wltc_3b.csv` on branch `fastsim-2`, commit `63808be8`, after converting m/s to km/h. The time bases are identical and the largest difference is 1.6e-8 km/h.
- **Validation:** 1801 samples covering 1800 s, maximum 131.3 km/h, distance 23.266 km (regulation value 23.266 km), mean speed 46.5 km/h.

## `whvc.csv`: World Harmonized Vehicle Cycle

- **Columns:** `time_s,speed_kmh`, with speed at 0.01 km/h resolution, as in the regulation.
- **Regulation:** UN GTR No. 4 (WHDC), Annex 1, part II "WHVC vehicle schedule" in the hybrid (HILS/HPC) provisions. The document is ECE/TRANS/180/Add.4/Amend.4 (2021), pages 103 to 120.
- **Source:** UN Official Document System, https://documents.un.org/api/symbol/access?s=ECE/TRANS/180/Add.4/Amend.4&l=en&t=pdf, which resolves to https://documents.un.org/doc/undoc/gen/g21/253/70/pdf/g2125370.pdf.
- **Transformations:**
  - The text was extracted from the PDF with `pdftotext -layout`.
  - The time and speed pairs were parsed from the two-column table.
  - The road-gradient column was dropped. It is a function of the hybrid system's rated power and is used for HILS only.
- **Time convention:** the table runs from t = 1 s to t = 1800 s, so the file has 1800 samples and no t = 0 row. Some secondary sources, such as DieselNet, list 0 to 1800 s. Prepend `0,0` if a 0-based axis is needed.
- **Cross-check:** parsed the same way from ECE/TRANS/180/Add.4/Amend.3 (2015, Annex 1(b)), https://documents.un.org/doc/undoc/gen/g15/134/55/pdf/g1513455.pdf. All 1800 values are identical.
- **Validation:** 1800 samples covering 1799 s of trapezoidal span, maximum 87.80 km/h, distance 20.072 km (reference about 20.1 km), mean speed 40.2 km/h.

## `braunschweig.csv`: Braunschweig city bus cycle

- **Columns:** `time_s,speed_kmh`, with speed written to 4 decimals. See the note on resolution below.
- **Origin:** a chassis-dynamometer bus cycle from TU Braunschweig. It is not part of any regulation, but it is widely used, for example in the DieselNet and TransportPolicy summaries.
- **Source:** NREL (now NLR) DriveCAT, the "Braunschweig City Driving Cycle" entry.
  - Download: https://www.nlr.gov/docs/libraries/transportation/csv/braunschweig-cycle.csv
  - Tool page: https://www.nlr.gov/transportation/drive-cycle-tool
- **Transformations:** speed was converted from mph to km/h by multiplying by 1.609344.
- **Resolution:** DriveCAT stores speed in mph rounded to 3 significant figures. Above 10 mph that is a 0.1 mph step, about 0.16 km/h. The original TU Braunschweig km/h values therefore cannot be recovered exactly. The rounding error is well under 0.1 km/h per sample and its effect on distance is negligible.
- **Validation:** 1741 samples covering 1740 s, maximum 58.26 km/h, distance 10.874 km (DriveCAT gives 6.76 mi, which is 10.88 km), mean speed 22.5 km/h. DieselNet gives 1740 s, 58.2 km/h, about 11 km and 22.9 km/h.

## `nrtc.csv`: Non-Road Transient Cycle (NRE engines)

- **Columns:** `time_s,speed_pct,torque_pct`, all integers as in the regulation.
  - Speed is the normalised speed in %.
  - Torque is the normalised torque in %, relative to the maximum torque at the commanded speed.
- **Regulation:** Commission Delegated Regulation (EU) 2017/654, Annex XVII, Appendix 3, "NRTC engine dynamometer schedule". This supplements Regulation (EU) 2016/1628 and was published in OJ L 102, 13.4.2017.
- **Source:** EU Publications Office (Cellar), the XHTML manifestation of CELEX 32017R0654, http://publications.europa.eu/resource/cellar/76b69e9f-200e-11e7-84e2-01aa75ed71a1, fetched with `Accept: application/xhtml+xml` and `Accept-Language: eng`. This is the original OJ text. Later amendments were not merged in, and none is known to change the NRTC table.
- **Transformations:** the HTML table was parsed. The LSI-NRTC table that follows it was excluded.
- **Time convention:** the table runs from t = 1 s to t = 1238 s, giving 1238 samples, which is kept as published.
- **Cross-check:** 40 CFR Part 1039, Appendix VI, "Nonroad Compression-ignition Composite Transient Cycle", from the eCFR API at https://www.ecfr.gov/api/versioner/v1/full/2026-10-14/title-40.xml?part=1039. All 1238 rows are identical.
- **Motoring points:** neither the EU table nor the US table contains any "m" (motoring) entries or negative torque values. Every torque value is a number from 0 to 100. So no encoding was needed: the motoring-flagged count is 0 and there are no NaN values in the file. Torque is 0 at 17 points where speed is above 0. When the cycle is denormalised, 0 % torque gives a reference torque of zero. If the manufacturer declares a minimum torque under Annex VI, point 7.7.2.3(a), that minimum is used instead. These points are kept as 0 without any flag.
- **Note:** the "m" convention exists in the WHTC engine schedule of GTR No. 4 Annex 1 and in the US FTP heavy-duty transient cycle, not in the NRTC.
- **Validation:** 1238 samples, speed from 0 to 105 %, torque from 0 to 100 %, 0 motoring-flagged points, mean speed 67.7 %, mean torque 39.3 %.
