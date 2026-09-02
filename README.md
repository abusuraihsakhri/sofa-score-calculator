# SOFA Score Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

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

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`SofaResult`**: Complete SOFA assessment result.
- **`QsofaResult`**: qSOFA bedside screening result.
- **`Sepsis3Result`**: Sepsis-3 assessment result.

---

## 📐 Mathematical Formulation & Logic

```text
  score = 0
  score = max(score, 1)
  score = max(score, 2)
  score = max(score, 4)
  score = max(score, 3)
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --pao2-fio2 <value> --mechanical-ventilation <value> --platelets <value> --bilirubin <value>
```

### Parameter Reference
- `--pao2-fio2`: Specifies input measurement or parameter value.
- `--mechanical-ventilation`: Specifies input measurement or parameter value.
- `--platelets`: Specifies input measurement or parameter value.
- `--bilirubin`: Specifies input measurement or parameter value.
- `--map`: Specifies input measurement or parameter value.
- `--dopamine`: Specifies input measurement or parameter value.
- `--dobutamine`: Specifies input measurement or parameter value.
- `--norepinephrine`: Specifies input measurement or parameter value.
- `--epinephrine`: Specifies input measurement or parameter value.
- `--gcs`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `pao2_fio2` | Parameter / observation metric | Required |
| `mechanical_ventilation` | Parameter / observation metric | Required |
| `platelets` | Parameter / observation metric | Required |
| `bilirubin` | Parameter / observation metric | Required |
| `map_mmhg` | Parameter / observation metric | Required |
| `dopamine` | Parameter / observation metric | Required |
| `dobutamine` | Parameter / observation metric | Required |
| `norepinephrine` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t sofa-score-calculator .
docker run -p 8000:8000 sofa-score-calculator
```
