# SOFA Score Calculator

A Python implementation of the **SOFA (Sequential Organ Failure Assessment)** score, **qSOFA** bedside screening, and **Sepsis-3** criteria assessment.

This is a clinical scoring tool — not a diagnostic device. It automates the arithmetic of established ICU scoring systems. All clinical decisions remain with the treating physician.

## What it does

**SOFA Score (0-24)** — quantifies organ dysfunction across 6 systems:

| System | Parameter | Score range |
|--------|-----------|:-----------:|
| Respiratory | PaO₂/FiO₂ ± mechanical ventilation | 0-4 |
| Coagulation | Platelet count (×10³/µL) | 0-4 |
| Liver | Total bilirubin (mg/dL) | 0-4 |
| Cardiovascular | MAP + vasopressor doses | 0-4 |
| CNS | Glasgow Coma Scale | 0-4 |
| Renal | Creatinine and/or urine output | 0-4 |

**qSOFA (0-3)** — rapid bedside screen for sepsis outside the ICU:
- Respiratory rate ≥ 22
- Altered mentation (GCS < 15)
- Systolic BP ≤ 100 mmHg
- Score ≥ 2 suggests possible sepsis

**Sepsis-3** — defines sepsis as suspected infection + acute SOFA increase ≥ 2 from baseline.

## Requirements

Python 3.8+ (stdlib only, no dependencies).

## Usage

### CLI

```bash
# Full SOFA score
python cli.py sofa \
  --pao2-fio2 180 \
  --mechanical-ventilation \
  --platelets 80 \
  --bilirubin 2.5 \
  --map 65 \
  --norepinephrine 0.15 \
  --gcs 10 \
  --creatinine 3.8

# qSOFA screening
python cli.py qsofa --respiratory-rate 26 --gcs 13 --systolic-bp 95

# Sepsis-3 assessment
python cli.py sepsis \
  --suspected-infection \
  --pao2-fio2 180 --platelets 80 --bilirubin 2.5 \
  --map 65 --norepinephrine 0.15 --gcs 10 --creatinine 3.8 \
  --respiratory-rate 26 --systolic-bp 95 \
  --baseline-pao2-fio2 400 --baseline-gcs 15

# JSON output
python cli.py sofa --json --pao2-fio2 450 --platelets 200 --gcs 15

# Batch CSV processing
python cli.py batch -i patients.csv -o results.csv
```

### Python API

```python
from sofa import calculate_sofa, calculate_qsofa, assess_sepsis3, sofa_delta

# Full SOFA
result = calculate_sofa(
    pao2_fio2=180,
    mechanical_ventilation=True,
    platelets=80,
    bilirubin=2.5,
    map_mmhg=65,
    norepinephrine=0.15,
    gcs=10,
    creatinine=3.8,
)
print(result.total)       # 17
print(result.respiratory)  # 3
print(result.to_json())

# qSOFA
q = calculate_qsofa(respiratory_rate=26, gcs=13, systolic_bp=95)
print(q.score)            # 3
print(q.suggests_sepsis)  # True

# Sepsis-3
baseline = calculate_sofa(pao2_fio2=400, platelets=250, gcs=15)
current  = calculate_sofa(pao2_fio2=180, platelets=80, gcs=10, map_mmhg=65)
sepsis   = assess_sepsis3(
    suspected_infection=True,
    baseline_sofa=baseline,
    current_sofa=current,
)
print(sepsis.meets_criteria)  # True

# Delta tracking
delta = sofa_delta(baseline, current)
print(delta["total_delta"])   # positive = worsening
```

### Batch CSV format

The batch command expects a CSV with these columns (all optional except `pao2_fio2`):

```
pao2_fio2,mechanical_ventilation,platelets,bilirubin,map_mmhg,dopamine,
dobutamine,norepinephrine,epinephrine,gcs,creatinine,urine_output_ml_day
```

Output adds `sofa_respiratory`, `sofa_coagulation`, `sofa_liver`,
`sofa_cardiovascular`, `sofa_cns`, `sofa_renal`, `sofa_total` columns.

## Running tests

```bash
python -m pytest test_sofa.py -v
```

Or without pytest:

```bash
python -m unittest test_sofa -v
```

## Clinical context

- **SOFA ≥ 2** in an ICU patient with suspected infection indicates sepsis (Sepsis-3).
- **qSOFA ≥ 2** outside the ICU should prompt further evaluation for sepsis.
- Rising SOFA over time (positive delta) correlates with increasing mortality.
- SOFA was not designed for pediatric patients; consider pSOFA for children.

## References

1. Vincent JL, et al. "Use of the SOFA score to assess the incidence of organ dysfunction/failure in intensive care units." *Crit Care Med*. 1998;26(11):1793-1800.
2. Singer M, et al. "The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)." *JAMA*. 2016;315(8):801-810.
3. Raith EP, et al. "Prognostic Accuracy of the SOFA Score, Sepsis-3, and qSOFA for Hospital Mortality." *JAMA*. 2017;317(3):290-300.

## License

MIT. See [LICENSE](LICENSE).
