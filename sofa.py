#!/usr/bin/env python3
"""
SOFA (Sequential Organ Failure Assessment) Score Calculator.

Implements the full SOFA score (0-24) across 6 organ systems, qSOFA bedside
screening, SOFA delta tracking, and Sepsis-3 criteria assessment.

References:
    Vincent JL, et al. "The SOFA score to describe organ dysfunction/failure."
    Intensive Care Med. 1996; 22:707-710.

    Singer M, et al. "The Third International Consensus Definitions for Sepsis
    and Septic Shock (Sepsis-3)." JAMA. 2016; 315(8):801-810.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_non_negative(value: float | int, name: str) -> None:
    """Raise ValueError if a physiological value is negative."""
    if value < 0:
        raise ValueError(f"{name} cannot be negative, got {value}")


def _validate_gcs(gcs: int) -> None:
    """Raise ValueError if GCS is outside the valid range of 3-15."""
    if gcs < 3 or gcs > 15:
        raise ValueError(f"GCS must be between 3 and 15, got {gcs}")


# ---------------------------------------------------------------------------
# Individual organ-system scoring functions
# ---------------------------------------------------------------------------

def score_respiration(pao2_fio2: float, mechanical_ventilation: bool = False) -> int:
    """Respiratory sub-score (0-4) from PaO2/FiO2 ratio.

    Args:
        pao2_fio2: PaO2/FiO2 ratio (mmHg). Must be non-negative.
        mechanical_ventilation: Whether the patient is on mechanical ventilation.

    Returns:
        Integer score 0-4.

    Raises:
        ValueError: If pao2_fio2 is negative.
    """
    _validate_non_negative(pao2_fio2, "pao2_fio2")
    if pao2_fio2 >= 400:
        return 0
    if pao2_fio2 < 100 and mechanical_ventilation:
        return 4
    if pao2_fio2 < 200 and mechanical_ventilation:
        return 3
    if pao2_fio2 < 300:
        return 2
    # pao2_fio2 < 400
    return 1


def score_coagulation(platelets: float) -> int:
    """Coagulation sub-score (0-4) from platelet count (×10³/µL).

    Args:
        platelets: Platelet count in ×10³/µL. Must be non-negative.

    Returns:
        Integer score 0-4.

    Raises:
        ValueError: If platelets is negative.
    """
    _validate_non_negative(platelets, "platelets")
    if platelets >= 150:
        return 0
    if platelets < 20:
        return 4
    if platelets < 50:
        return 3
    if platelets < 100:
        return 2
    # platelets < 150
    return 1


def score_liver(bilirubin: float) -> int:
    """Liver sub-score (0-4) from total bilirubin (mg/dL).

    Args:
        bilirubin: Total bilirubin in mg/dL. Must be non-negative.

    Returns:
        Integer score 0-4.

    Raises:
        ValueError: If bilirubin is negative.
    """
    _validate_non_negative(bilirubin, "bilirubin")
    if bilirubin < 1.2:
        return 0
    if bilirubin >= 12.0:
        return 4
    if bilirubin >= 6.0:
        return 3
    if bilirubin >= 2.0:
        return 2
    # 1.2 <= bilirubin < 2.0
    return 1


def score_cardiovascular(
    map_mmhg: Optional[float] = None,
    dopamine: Optional[float] = None,
    dobutamine: Optional[float] = None,
    norepinephrine: Optional[float] = None,
    epinephrine: Optional[float] = None,
) -> int:
    """Cardiovascular sub-score (0-4) from MAP and vasopressor doses.

    Vasopressor doses are in µg/kg/min.  Any dose of dobutamine counts as
    score 2 regardless of MAP.

    The highest applicable score wins (e.g. dopamine >15 overrides MAP <70).

    Args:
        map_mmhg: Mean arterial pressure in mmHg (None if not measured).
        dopamine: Dopamine dose in µg/kg/min (None if not used).
        dobutamine: Dobutamine dose in µg/kg/min (None if not used).
        norepinephrine: Norepinephrine dose in µg/kg/min (None if not used).
        epinephrine: Epinephrine dose in µg/kg/min (None if not used).

    Returns:
        Integer score 0-4.
    """
    score = 0

    # Validate non-negative values
    for name, val in [
        ("map_mmhg", map_mmhg),
        ("dopamine", dopamine),
        ("dobutamine", dobutamine),
        ("norepinephrine", norepinephrine),
        ("epinephrine", epinephrine),
    ]:
        if val is not None:
            _validate_non_negative(val, name)

    # MAP-based baseline
    if map_mmhg is not None and map_mmhg < 70:
        score = max(score, 1)

    # Dobutamine at any dose → at least 2
    if dobutamine is not None and dobutamine > 0:
        score = max(score, 2)

    # Dopamine dosing tiers
    if dopamine is not None:
        if dopamine > 15:
            score = max(score, 4)
        elif dopamine > 5:
            score = max(score, 3)
        elif dopamine > 0:
            score = max(score, 2)

    # Norepinephrine dosing tiers
    if norepinephrine is not None:
        if norepinephrine > 0.1:
            score = max(score, 4)
        elif norepinephrine > 0:
            score = max(score, 3)

    # Epinephrine follows same tiers as norepinephrine
    if epinephrine is not None:
        if epinephrine > 0.1:
            score = max(score, 4)
        elif epinephrine > 0:
            score = max(score, 3)

    return score


def score_cns(gcs: int) -> int:
    """Central nervous system sub-score (0-4) from Glasgow Coma Scale (3-15).

    Args:
        gcs: Glasgow Coma Scale score (3-15).

    Returns:
        Integer score 0-4.

    Raises:
        ValueError: If gcs is outside the valid range of 3-15.
    """
    _validate_gcs(gcs)
    if gcs == 15:
        return 0
    if gcs >= 13:
        return 1
    if gcs >= 10:
        return 2
    if gcs >= 6:
        return 3
    return 4


def score_renal(
    creatinine: Optional[float] = None,
    urine_output_ml_day: Optional[float] = None,
) -> int:
    """Renal sub-score (0-4) from creatinine (mg/dL) and/or urine output.

    The higher of the two scoring paths is used when both are provided.

    Args:
        creatinine: Serum creatinine in mg/dL (None if not measured).
        urine_output_ml_day: Urine output in mL/day (None if not measured).

    Returns:
        Integer score 0-4.
    """
    score = 0

    if creatinine is not None:
        _validate_non_negative(creatinine, "creatinine")
        if creatinine >= 5.0:
            score = max(score, 4)
        elif creatinine >= 3.5:
            score = max(score, 3)
        elif creatinine >= 2.0:
            score = max(score, 2)
        elif creatinine >= 1.2:
            score = max(score, 1)

    if urine_output_ml_day is not None:
        _validate_non_negative(urine_output_ml_day, "urine_output_ml_day")
        if urine_output_ml_day < 200:
            score = max(score, 4)
        elif urine_output_ml_day < 500:
            score = max(score, 3)

    return score


# ---------------------------------------------------------------------------
# Composite SOFA result
# ---------------------------------------------------------------------------

@dataclass
class SofaResult:
    """Complete SOFA assessment result."""
    respiratory: int
    coagulation: int
    liver: int
    cardiovascular: int
    cns: int
    renal: int
    total: int = field(init=False)

    def __post_init__(self) -> None:
        self.total = (
            self.respiratory
            + self.coagulation
            + self.liver
            + self.cardiovascular
            + self.cns
            + self.renal
        )

    def to_dict(self) -> dict:
        """Return a plain dictionary representation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string representation."""
        return json.dumps(self.to_dict(), indent=indent)


def calculate_sofa(
    # Respiratory
    pao2_fio2: float,
    mechanical_ventilation: bool = False,
    # Coagulation
    platelets: float = 999,
    # Liver
    bilirubin: float = 0.0,
    # Cardiovascular
    map_mmhg: Optional[float] = None,
    dopamine: Optional[float] = None,
    dobutamine: Optional[float] = None,
    norepinephrine: Optional[float] = None,
    epinephrine: Optional[float] = None,
    # CNS
    gcs: int = 15,
    # Renal
    creatinine: Optional[float] = None,
    urine_output_ml_day: Optional[float] = None,
) -> SofaResult:
    """Calculate the full SOFA score from clinical parameters.

    Args:
        pao2_fio2: PaO2/FiO2 ratio.
        mechanical_ventilation: On mechanical ventilation?
        platelets: Platelet count (×10³/µL).
        bilirubin: Total bilirubin (mg/dL).
        map_mmhg: Mean arterial pressure (mmHg).
        dopamine: Dopamine dose (µg/kg/min).
        dobutamine: Dobutamine dose (µg/kg/min).
        norepinephrine: Norepinephrine dose (µg/kg/min).
        epinephrine: Epinephrine dose (µg/kg/min).
        gcs: Glasgow Coma Scale (3-15).
        creatinine: Serum creatinine (mg/dL).
        urine_output_ml_day: Urine output (mL/day).

    Returns:
        SofaResult with all 6 sub-scores and the total.
    """
    return SofaResult(
        respiratory=score_respiration(pao2_fio2, mechanical_ventilation),
        coagulation=score_coagulation(platelets),
        liver=score_liver(bilirubin),
        cardiovascular=score_cardiovascular(
            map_mmhg=map_mmhg,
            dopamine=dopamine,
            dobutamine=dobutamine,
            norepinephrine=norepinephrine,
            epinephrine=epinephrine,
        ),
        cns=score_cns(gcs),
        renal=score_renal(creatinine, urine_output_ml_day),
    )


# ---------------------------------------------------------------------------
# qSOFA (quick SOFA) bedside screening
# ---------------------------------------------------------------------------

@dataclass
class QsofaResult:
    """qSOFA bedside screening result."""
    respiratory_rate_ge_22: bool
    altered_mentation: bool
    systolic_bp_le_100: bool
    score: int = field(init=False)
    suggests_sepsis: bool = field(init=False)

    def __post_init__(self) -> None:
        self.score = (
            int(self.respiratory_rate_ge_22)
            + int(self.altered_mentation)
            + int(self.systolic_bp_le_100)
        )
        self.suggests_sepsis = self.score >= 2

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_qsofa(
    respiratory_rate: int,
    gcs: int = 15,
    systolic_bp: int = 120,
) -> QsofaResult:
    """Calculate the quick SOFA (qSOFA) bedside screening score.

    Args:
        respiratory_rate: Respiratory rate (breaths/min). Must be non-negative.
        gcs: Glasgow Coma Scale (3-15); altered mentation = GCS < 15.
        systolic_bp: Systolic blood pressure (mmHg). Must be non-negative.

    Returns:
        QsofaResult with individual criteria and total score.

    Raises:
        ValueError: If respiratory_rate or systolic_bp is negative, or gcs is out of range.
    """
    _validate_non_negative(respiratory_rate, "respiratory_rate")
    _validate_gcs(gcs)
    _validate_non_negative(systolic_bp, "systolic_bp")
    return QsofaResult(
        respiratory_rate_ge_22=respiratory_rate >= 22,
        altered_mentation=gcs < 15,
        systolic_bp_le_100=systolic_bp <= 100,
    )


# ---------------------------------------------------------------------------
# SOFA delta (change from baseline)
# ---------------------------------------------------------------------------

def sofa_delta(baseline: SofaResult, current: SofaResult) -> dict:
    """Calculate the change in SOFA score from a baseline measurement.

    Used to detect acute organ dysfunction (Sepsis-3 requires delta >= 2).

    Args:
        baseline: The baseline SofaResult.
        current: The current SofaResult.

    Returns:
        Dictionary with per-system deltas and total delta.
    """
    return {
        "respiratory": current.respiratory - baseline.respiratory,
        "coagulation": current.coagulation - baseline.coagulation,
        "liver": current.liver - baseline.liver,
        "cardiovascular": current.cardiovascular - baseline.cardiovascular,
        "cns": current.cns - baseline.cns,
        "renal": current.renal - baseline.renal,
        "total_delta": current.total - baseline.total,
    }


# ---------------------------------------------------------------------------
# Sepsis-3 criteria
# ---------------------------------------------------------------------------

@dataclass
class Sepsis3Result:
    """Sepsis-3 assessment result."""
    suspected_infection: bool
    sofa_increase: int
    meets_criteria: bool
    qsofa: Optional[QsofaResult] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.qsofa is not None:
            d["qsofa"] = self.qsofa.to_dict()
        return d


def assess_sepsis3(
    suspected_infection: bool,
    baseline_sofa: SofaResult,
    current_sofa: SofaResult,
    qsofa: Optional[QsofaResult] = None,
) -> Sepsis3Result:
    """Assess Sepsis-3 criteria: suspected infection + acute SOFA increase >= 2.

    Args:
        suspected_infection: Clinical suspicion of infection.
        baseline_sofa: Baseline SOFA score (often 0 for previously healthy).
        current_sofa: Current SOFA score.
        qsofa: Optional qSOFA result for additional context.

    Returns:
        Sepsis3Result with criteria assessment.
    """
    delta = sofa_delta(baseline_sofa, current_sofa)
    increase = delta["total_delta"]
    return Sepsis3Result(
        suspected_infection=suspected_infection,
        sofa_increase=increase,
        meets_criteria=suspected_infection and increase >= 2,
        qsofa=qsofa,
    )
