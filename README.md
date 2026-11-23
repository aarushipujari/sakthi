# Alloy Addition Calculator
### Automated Corrective Alloy Addition Engine from Spectrometer Results
**Industrial Decision Support System for Coreless Induction Furnace Foundries**  
*Sakthi Hackathon 2.0 • Process Automation & Metallurgical Optimization*

---

## 1. Industrial Context & Problem Understanding

During coreless induction furnace melting in automotive foundries (e.g. **Sakthi Auto Component Ltd**), molten metal chemical composition is sampled via optical emission spectrometers (OES). Initial melt chemistry rarely hits target specifications on the first reading.

Determining corrective ferroalloy additions manually introduces critical challenges:
* **Time Pressure & Heat Loss**: Molten iron cools rapidly (~5–10 °C/min), risking cold taps and slag crusting if calculations are delayed.
* **Non-Linear Dilution & Recovery Losses**: Added alloys are partially lost to oxidation and slagging (recovery rate $\eta < 1.0$), and the added mass dilutes the bath ($M_{final} = M_0 + \sum x_i$).
* **Slag Generation & Mass Partitioning**: Non-recovered alloying elements oxidize and partition directly into the dross/slag layer (~1–2% of unrecovered mass), requiring operational estimation for fluxing and slag skimming.
* **Cross-Contamination & Joint Optimization**: Alloys carry multiple elements (e.g. SiMn carries both 65% Mn and 17% Si; HC FeCr carries 65% Cr and 7% C). Manual single-element calculations often overshoot carbon or silicon ceilings.
* **Lack of Auditability**: Hand calculations lack formal traceability, digital verification, and immutable audit logs.

**Alloy Addition Calculator** solves this by formulating alloy addition as a **Constrained Linear Programming (LP) Optimization** solved in under 15 milliseconds with **SciPy HiGHS**, paired with an offline-ready SCADA dashboard, append-only SQLite audit log, and safe AST evaluation.

---

## 2. Mathematical Formulation & Physical Conservation

### Objective Function
Minimize the total cost of alloy additions:
$$\min \sum_{i=1}^{n} c_i x_i + M \sum_{j} (s_{j}^{min} + s_{j}^{max})$$
Where:
* $x_i \ge 0$: Mass of ferroalloy $i$ added (kg).
* $c_i$: Unit cost of ferroalloy $i$ (₹/kg or $/kg).
* $s_{j}^{min}, s_{j}^{max} \ge 0$: Soft constraint slack variables with large penalty $M = 10,000$, ensuring the solver never crashes with a bare "infeasible" and always returns a best-effort plan with diagnostic violations.

### Elemental Mass Balance with Recovery & Dilution
For each element $j$ in the target grade specification:
$$c_{final, j} = \frac{M_0 c_{0, j} + \sum_{i=1}^{n} x_i a_{i, j} \eta_{i, j}}{M_0 + \sum_{i=1}^{n} x_i} \times 100\%$$

Transformed into standard linear constraints:
$$\sum_{i=1}^{n} x_i \left( a_{i, j} \eta_{i, j} - \frac{c_{target, j}}{100} \right) + s_j = M_0 \left( \frac{c_{target, j} - c_{0, j}}{100} \right)$$

* **Mass Conservation & Slag/Oxidation Loss**: Unrecovered alloying mass is formally tracked via:
  $$\Delta M_{slag} = \sum_{i=1}^{n} \sum_{j} x_i \cdot a_{i, j} \cdot (1 - \eta_{i, j})$$
  This estimate is reported in the calculation trace, metric summary strip, and export tickets so the melter knows the expected oxidation loss and slag volume before skimming.
* **Dilution Protection**: For elements already above minimum ($c_{0, j} \ge c_{min, j}$), a lower floor is strictly maintained so additions of carrier alloys do not dilute the bath below grade limits.
* **FeSiMg Gating**: FeSiMg nodulizer (6% Mg, 45% Si) is strictly gated to grades with active magnesium requirements ($\text{Mg}_{min} > 0$), preventing accidental nodulizing in grey iron or steels.
* **Safe Carbon Equivalent (CE) AST Evaluation**: Grade CE formulas are parsed using Python's `ast` visitor (`SafeCEValidator`), restricting execution exclusively to elemental symbols (`C, Si, P, Mn, Cr, Mo, Ni, Cu, V`), numbers, and basic arithmetic operators (`+ - * / ()`), eliminating arbitrary code execution risks.
* **Unified FX Rate**: Currency conversion is governed by a single configurable constant (`DEFAULT_FX_RATE = 84.0` INR/USD).
* **Optimization Modes**:
  * **Target Setpoint (`target`)**: Targets the exact corridor midpoint for maximum safety margin.
  * **Lean Spec (`lean`)**: Targets the lower specification boundary for minimum raw material cost.

---

## 3. Key Capabilities & Technical Features

### A. Automated Spectrometer (OES) Integration
* **Multi-Format Ingestion**: Drag-and-drop parser for CSV, TSV, and JSON spectrometer exports (Spectro MAXx, Thermo ARL, Bruker Q8).
* **Auto-Grade Detection**: Automatically matches composition to the closest grade recipe.
* **Preloaded Industrial Samples**: Located in `samples/` (`sample_ductile_iron_500_7.csv`, `sample_grey_iron_fg260.csv`, `sample_steel_4140.json`, `sample_stainless_304.csv`, `sample_hadfield_wear_steel.csv`).

### B. Industrial Grade Library & Recipe Editor
* Pre-configured for standard automotive casting grades:
  1. **SG Iron 500/7 (ASTM 65-45-12)**: Crankshafts & Steering Knuckles.
  2. **SG Iron 400/18 (Ferritic High Impact)**: Suspension Control Arms & Caliper Brackets.
  3. **Grey Cast Iron FG 260 (ASTM Class 35)**: Ventilated Brake Rotors & Drums.
  4. **Low-Alloy Steel 4140 (42CrMo4)**: Transmission Pinions & Turbine Shafts.
  5. **Austenitic Stainless CF8 (AISI 304)**: Chemical Pump Impellers & Valves.
  6. **Hadfield Manganese Steel (ASTM A128 Gr B)**: Rock Crusher Jaws & Wear Plates.
* **Configurable Recipes (`data/grades.json`)**: Full CRUD API (`GET/POST/PUT/DELETE /api/grades`) with validation ($\text{min} \le \text{target} \le \text{max}$) and CE formula validation. Includes clone/duplicate functionality.

### C. Commercial Ferroalloy Catalog & Editable Recoveries
* Preloaded with 10 commercial alloys (Recarburizer, FeSi 75, HC FeMn, LC FeMn, SiMn 65/17, HC FeCr, LC FeCr, FeMo 60, Pure Nickel, FeSiMg 6%).
* **Editable Recoveries & Pricing (`data/alloys.json`)**: Live editing of recovery factors ($\eta$), compositions, bag sizes, and costs via `PUT /api/alloys/{id}` or UI modal.
* **Packaging Dispatch Breakdown**: Translates exact kilograms into whole packaging units and trim scale adjustments (e.g. `2 Sacks (50 kg) + 13.2 kg trim`).

### D. User Verification & Override Workflow
* Workflow states: `CALCULATED` $\to$ `UNDER_REVIEW` $\to$ `APPROVED` / `OVERRIDDEN` / `REJECTED`.
* **Live Interactive Override Simulation**: Operators can manually adjust recommended alloy weights. The backend (`POST /api/simulate-additions`) recalculates resulting chemistry in real time and highlights newly induced out-of-spec corridor violations in red.
* **Mandatory Override Justification**: Overriding the calculated plan enforces entering the operator name and justification reason before saving.

### E. Append-Only Audit Trail & Reproducibility (`data/heats.db`)
* Every calculated and approved heat is stored in SQLite with full snapshots of input chemistry, final chemistry, recovery factors, pricing, recommendations, operator name, and override notes.
* **`heat_events` Audit Log**: Append-only log recording every status change (`timestamp, actor, old_status, new_status, reason, snapshot_hash`).
* **Recipe & Solver Hashing**: Stores `grade_version_hash` (SHA-256 of grade specification) and `optimizer_version` to guarantee exact replayability.
* **Official Vector PDF Export**: Generates high-resolution vector PDF melt tickets with ReportLab (`/api/heats/{id}/export?format=pdf`).
* **CSV Data Export**: One-click tabular CSV download (`/api/heats/{id}/export?format=csv`).

### F. Dual Variables & Metallurgical Explainability
* Exposes **shadow prices (dual marginals)** for binding chemistry constraints in both ₹/kg and $/kg.
* Explains the exact metallurgical driving force behind each recommendation (e.g. *“SiMn chosen over separate FeMn/FeSi to satisfy both Mn and Si deficits simultaneously at lower cost”*).

### G. Zero-CDN Offline Self-Contained Frontend
* Completely eliminates external CDN scripts.
* 100% functional in isolated industrial plant networks and foundries with air-gapped workstations.
* High-contrast light mode with clean steel blue accent (`#2563eb`), organized into 5 focused tabs:
  1. **Live Calculation**: Single-column operational flow (Parameters $\to$ Metrics Strip $\to$ Status Banner $\to$ Core Table $\to$ Charge Plan $\to$ Sign-off).
  2. **Economics**: Heuristic cost & savings benchmark with fair spec checking and zero NaN fallbacks.
  3. **Heat History**: Filterable heats table with event history modal and PDF/CSV export.
  4. **Master Recipe Settings**: Full interactive editing and duplication of grades and alloy recovery catalogs.
  5. **Spectrometer Ingestion**: Drag-and-drop OES file parser with auto-grade mapping.

---

## 4. Project Directory Structure

```
sakthi/
├── backend/
│   ├── catalog.py           # Standard grade & alloy seed data
│   ├── config.py            # Global constants (DEFAULT_FX_RATE, OPTIMIZER_VERSION)
│   ├── explainability.py    # Dual variable explainability & what-if heuristics
│   ├── export_service.py    # ReportLab PDF & CSV dispatch ticket generator
│   ├── main.py              # FastAPI REST API controller
│   ├── optimizer.py         # SciPy HiGHS LP engine with AST CE evaluator
│   ├── spectrometer.py      # Multi-format OES spectrometer file parser
│   └── storage.py           # Persistence layer (JSON configs, SQLite audit log)
├── data/
│   ├── alloys.json          # Editable ferroalloys catalog & recovery factors
│   ├── grades.json          # Configurable grade recipes & corridor specs
│   └── heats.db             # SQLite digital audit trail database
├── samples/
│   ├── sample_ductile_iron_500_7.csv
│   ├── sample_grey_iron_fg260.csv
│   ├── sample_steel_4140.json
│   ├── sample_stainless_304.csv
│   └── sample_hadfield_wear_steel.csv
├── static/
│   ├── app.js               # Reactive SCADA cockpit client logic & vector icons
│   ├── index.html           # High-contrast light theme dashboard
│   └── styles.css           # Self-contained offline CSS & print stylesheet
├── tests/
│   ├── conftest.py          # Session fixture isolating storage to temp dir (SAKTHI_DATA_DIR)
│   ├── test_all_grades.py   # Baseline verification runner for all standard grades
│   ├── test_api.py          # REST endpoint, CRUD, import & export tests
│   └── test_optimizer.py    # Mass-balance, dilution, gating, fuzz & AST CE tests
├── requirements.txt         # Production library dependencies
├── run.bat                  # One-click launcher script
└── README.md                # Technical documentation & architecture
```

---

## 5. Quickstart & Verification

### Prerequisites
* Python 3.10 or higher.
* Recommended libraries: `fastapi`, `uvicorn`, `scipy`, `numpy`, `pydantic`, `pytest`, `httpx`, `reportlab`, `python-multipart`.

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch the System
Double click **`run.bat`** or run:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Navigate to **`http://127.0.0.1:8000`** in your browser.

### Run Comprehensive Test Suite
Execute the full pytest verification suite (isolated database, independent mass balance, fuzzing, API validation, audit trails):
```bash
pytest tests/ -v
```
All 18 tests execute and pass cleanly:
```
tests/test_all_grades.py::test_all_grades_verification PASSED
tests/test_api.py::test_get_grades_and_alloys PASSED
tests/test_api.py::test_grade_crud_and_validation PASSED
tests/test_api.py::test_alloy_update_and_recovery_validation PASSED
tests/test_api.py::test_spectrometer_payload_import PASSED
tests/test_api.py::test_simulate_manual_additions PASSED
tests/test_api.py::test_heat_audit_trail_and_verification_workflow PASSED
tests/test_api.py::test_input_chemistry_validation_and_implausible_warnings PASSED
tests/test_api.py::test_config_endpoint PASSED
tests/test_optimizer.py::test_all_standard_grades_feasibility PASSED
tests/test_optimizer.py::test_independent_mass_balance_accuracy PASSED
tests/test_optimizer.py::test_fesimg_gated_on_magnesium PASSED
tests/test_optimizer.py::test_dilution_protection PASSED
tests/test_optimizer.py::test_soft_constraints_on_over_spec_input PASSED
tests/test_optimizer.py::test_lean_mode_vs_target_mode PASSED
tests/test_optimizer.py::test_fuzz_random_inputs PASSED
tests/test_optimizer.py::test_safe_ce_evaluator_security_and_accuracy PASSED
tests/test_optimizer.py::test_calculation_trace_slag_loss_and_recovery_notices PASSED
============================= 18 passed in 9.90s ==============================
```
