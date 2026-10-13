# SOFA Score Calculator

An implementation of the **original SOFA (Sequential Organ Failure Assessment)** score and qSOFA, with a Python command-line interface, CSV batch processing, and an in-browser calculator using Pyodide.

## Features

- **SOFA (0–24)**: six component scores for respiration, coagulation, liver, cardiovascular system, CNS, and kidneys.
- **qSOFA (0–3)**: respiratory rate, altered mentation, and systolic blood pressure.
- **Change from baseline**: per-system and total SOFA difference, plus operational Sepsis-3 threshold assessment for suspected infection.
- **Python CLI and CSV**: process one assessment or an entire local CSV file.
- **Browser interface**: use the original Python `sofa.py` logic directly in the browser via a version-pinned Pyodide runtime; no server-side Python or API key.

## Clinical interpretation and limitations

This project implements the **original SOFA score**, not SOFA-2. A SOFA increase of at least 2 in the setting of suspected infection is an operational Sepsis-3 criterion, not a substitute for clinical diagnosis. **Neither a low qSOFA nor a low SOFA rules out sepsis.** Current Surviving Sepsis Campaign guidance recommends NEWS/NEWS2, MEWS, or SIRS over qSOFA as the sole sepsis screening tool.

**Important:** The legacy Python API and normal-mode CLI retain historical defaults for omitted measurements (for compatibility). An omitted value must **not** be interpreted clinically as a measured normal value. Enter all available measurements and use `--strict` for clinical CSV datasets. The web interface requires inputs for every scoring domain and does not silently assume normal laboratory measurements. Confirm ventilatory support criteria, measurement timing, baseline organ dysfunction, and sedation effects on GCS before interpreting results.

This software is for education and research support, not standalone patient management.

## Using the browser application

Open the site when GitHub Pages is enabled for this repository, select **SOFA** or **qSOFA**, enter the clinical measurements in the stated units, and calculate. Baseline SOFA and suspected infection are optional inputs for viewing the operational Sepsis-3 threshold.

The site processes entered measurements **locally in the browser**; it does not store or upload patient values. On initial load it downloads the Python runtime from jsDelivr and loads the local `sofa.py` file from the site. These asset requests have normal network metadata (such as IP address); no patient inputs are sent with them. Avoid entering identifiable patient data.

Requires a modern browser with WebAssembly and JavaScript support and internet access to load the Pyodide runtime. Browser functionality is separate from the CLI and is not intended for offline use.

## Python CLI

Requires **Python 3.10+**. Runtime dependencies: none.

```bash
git clone https://github.com/abusuraihsakhri/sofa-score-calculator.git
cd sofa-score-calculator

# Single assessment (provide actual measurements rather than relying on defaults)
python cli.py sofa --pao2-fio2 180 --mechanical-ventilation \
  --platelets 80 --bilirubin 2.5 --map 60 \
  --norepinephrine 0.15 --gcs 10 --creatinine 3.0

# Machine-readable output
python cli.py sofa --pao2-fio2 280 --platelets 160 --bilirubin 0.8 \
  --map 85 --gcs 15 --creatinine 0.9 --json

# qSOFA risk stratification
python cli.py qsofa --respiratory-rate 26 --gcs 13 --systolic-bp 95

# Operational Sepsis-3 criteria using supplied baseline measurements
python cli.py sepsis --suspected-infection --pao2-fio2 180 \
  --platelets 80 --gcs 10 --creatinine 3.0

# Batch CSV (strict mode rejects missing key measurements)
python cli.py batch -i sample.csv -o results.csv --strict
```

The CSV header uses names such as `pao2_fio2`, `mechanical_ventilation`, `platelets`, `bilirubin`, `map_mmhg`, `dopamine`, `dobutamine`, `norepinephrine`, `epinephrine`, `gcs`, `creatinine`, and `urine_output_ml_day`. See [sample.csv](sample.csv).

Use `--strict` with batch mode to require explicit respiratory, coagulation, hepatic and GCS entries, plus a MAP or vasoactive dose and a renal measurement. In non-strict batch mode, missing values still use legacy defaults. Existing output files may be replaced; source and destination cannot be the same file.

The CLI uses platelet units **×10³/µL**, bilirubin and creatinine **mg/dL**, vasoactive drug doses **µg/kg/min**, urine output **mL per 24 h**, and PaO₂/FiO₂ in **mmHg**. The six organ subscores each range from 0 to 4; their sum ranges from 0 to 24.

## Development and testing

```bash
python -m unittest test_sofa -v
# Optional dev tools:
python -m pip install pytest ruff
python -m pytest -q
ruff check . --select E,F,W
node --test web-input.test.mjs
```

The repository includes a Python matrix CI workflow, browser input tests, and a Pages deployment workflow. Static site files are `index.html`, `style.css`, `app.mjs`, `input.mjs`, and `sofa.py`. There is no Flask/FastAPI server; Python executes through WebAssembly (Pyodide) in the browser.

## References

1. Vincent JL, Moreno R, Takala J, et al. The SOFA score to describe organ dysfunction/failure. *Intensive Care Medicine*. 1996;22:707–710.
2. Singer M, Deutschman CS, Seymour CW, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). *JAMA*. 2016;315:801–810.
3. Society of Critical Care Medicine. [Surviving Sepsis Campaign: Adult Guidelines](https://www.sccm.org/survivingsepsiscampaign/guidelines-and-resources/surviving-sepsis-campaign-adult-guidelines).

## License

[MIT](LICENSE).
