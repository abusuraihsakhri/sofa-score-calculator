# SOFA Score Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)

</div>

---

## What It Does

SOFA (Sequential Organ Failure Assessment) Score Calculator.

Implements the full SOFA score (0-24) across 6 organ systems, qSOFA bedside
screening, SOFA delta tracking, and Sepsis-3 criteria assessment.

References:
    Vincent JL, et al. "The SOFA score to describe organ dysfunction/failure."
    Intensive Care Med. 1996; 22:707-710.

    Singer M, et al. "The Third International Consensus Definitions for Sepsis
    and Septic Shock (Sepsis-3)." JAMA. 2016; 315(8):801-810.

Stdlib only. No external dependencies.

---

## Key Capabilities

- **Full SOFA Score (0-24):** Across 6 organ systems — Respiratory, Coagulation, Liver, Cardiovascular, CNS, Renal
- **qSOFA Bedside Screening:** Quick 3-criteria assessment for sepsis risk
- **SOFA Delta Tracking:** Change detection from baseline measurements
- **Sepsis-3 Criteria Assessment:** Suspected infection + acute SOFA increase >= 2
- **CSV Batch Processing:** Process multiple patients from a CSV file

---

## Installation

No installation required — uses Python stdlib only. Requires Python 3.10+.

```bash
git clone https://github.com/abusuraihsakhri/sofa-score-calculator.git
cd sofa-score-calculator
```

---

## Usage

### 1. Full SOFA Score (single patient)

```bash
python cli.py sofa --pao2-fio2 180 --mechanical-ventilation --platelets 80 --bilirubin 2.5 --map 60 --norepinephrine 0.15 --gcs 10 --creatinine 3.0
```

JSON output:
```bash
python cli.py sofa --json --pao2-fio2 180 --mechanical-ventilation --platelets 80 --gcs 15
```

### 2. qSOFA Bedside Screening

```bash
python cli.py qsofa --respiratory-rate 26 --gcs 13 --systolic-bp 95
```

### 3. Sepsis-3 Criteria Assessment

```bash
python cli.py sepsis --pao2-fio2 180 --mechanical-ventilation --platelets 80 --map 60 --norepinephrine 0.15 --gcs 10 --creatinine 3.0 --suspected-infection --respiratory-rate 26 --systolic-bp 95
```

### 4. Batch CSV Processing

```bash
python cli.py batch -i sample.csv -o results.csv
```

Input CSV must include column headers matching the parameter names:
`pao2_fio2`, `platelets`, `bilirubin`, `gcs`, etc. (see `sample.csv` for format).

Empty cells are treated as normal/default values.

### Parameters

| Parameter | Description | Default |
|:----------|:------------|:--------|
| `--pao2-fio2` | PaO2/FiO2 ratio (mmHg) | Required |
| `--mechanical-ventilation` | Patient on mechanical ventilation | False |
| `--platelets` | Platelet count (×10³/µL) | 999 (normal) |
| `--bilirubin` | Total bilirubin (mg/dL) | 0.0 |
| `--map` | Mean arterial pressure (mmHg) | None |
| `--dopamine` | Dopamine dose (µg/kg/min) | None |
| `--dobutamine` | Dobutamine dose (µg/kg/min) | None |
| `--norepinephrine` | Norepinephrine dose (µg/kg/min) | None |
| `--epinephrine` | Epinephrine dose (µg/kg/min) | None |
| `--gcs` | Glasgow Coma Scale (3-15) | 15 |
| `--creatinine` | Serum creatinine (mg/dL) | None |
| `--urine-output` | Urine output (mL/day) | None |

---

## Testing

Run the full test suite:

```bash
python -m pytest test_sofa.py -v
```

Or with unittest:

```bash
python -m unittest test_sofa -v
```

---

## Scoring Reference

### SOFA Sub-scores (each 0-4)

| System | Parameter | 0 | 1 | 2 | 3 | 4 |
|:-------|:----------|:-:|:-:|:-:|:-:|:-:|
| Respiratory | PaO2/FiO2 | ≥400 | <400 | <300 | <200* | <100* |
| Coagulation | Platelets | ≥150 | <150 | <100 | <50 | <20 |
| Liver | Bilirubin | <1.2 | <2.0 | <6.0 | <12.0 | ≥12.0 |
| Cardiovascular | MAP/Vasopressors | ≥70 | <70 | Dob/DA≤5 | DA≤15/NE≤0.1 | DA>15/NE>0.1 |
| CNS | GCS | 15 | 13-14 | 10-12 | 6-9 | <6 |
| Renal | Creatinine/UO | <1.2 | <2.0 | <3.5 | <5.0 | ≥5.0 |

*With mechanical ventilation

### qSOFA Criteria (each 0-1)

- Respiratory rate ≥ 22
- Altered mentation (GCS < 15)
- Systolic BP ≤ 100

Score ≥ 2 suggests sepsis risk.

---

## Project Structure

```
sofa-score-calculator/
├── sofa.py          # Core scoring library
├── cli.py           # Command-line interface
├── test_sofa.py     # Test suite
├── sample.csv       # Example batch input
├── LICENSE          # MIT License
├── README.md        # This file
└── .github/
    └── workflows/
        ci.yml       # CI pipeline
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
