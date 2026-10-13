#!/usr/bin/env python3
"""
Comprehensive tests for the SOFA Score Calculator.

Covers:
- All 6 individual organ system scoring functions
- Total SOFA calculation
- qSOFA screening
- Sepsis-3 criteria
- Clinical scenarios (septic shock, ARDS, liver failure, etc.)
- Edge cases and boundary values
- CLI smoke tests

Uses unittest (stdlib only). Run with:
    python -m unittest test_sofa -v
    python -m pytest test_sofa.py -v
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from sofa import (
    QsofaResult,
    SofaResult,
    assess_sepsis3,
    calculate_qsofa,
    calculate_sofa,
    score_cardiovascular,
    score_cns,
    score_coagulation,
    score_liver,
    score_renal,
    score_respiration,
    sofa_delta,
)


# ======================================================================
# Respiratory sub-score
# ======================================================================
class TestRespiration(unittest.TestCase):
    """Test score_respiration() — PaO2/FiO2 ± mechanical ventilation."""

    def test_normal(self):
        self.assertEqual(score_respiration(450), 0)

    def test_boundary_400(self):
        self.assertEqual(score_respiration(400), 0)

    def test_score_1(self):
        self.assertEqual(score_respiration(350), 1)

    def test_boundary_just_below_400(self):
        self.assertEqual(score_respiration(399), 1)

    def test_score_2(self):
        self.assertEqual(score_respiration(250), 2)

    def test_boundary_300(self):
        # Exactly 300 is NOT <300, so score is 1 (<400)
        self.assertEqual(score_respiration(300), 1)

    def test_boundary_just_below_300(self):
        self.assertEqual(score_respiration(299), 2)

    def test_score_3_with_ventilation(self):
        self.assertEqual(score_respiration(150, mechanical_ventilation=True), 3)

    def test_score_3_boundary_200(self):
        # Exactly 200 is NOT <200, so score is 2 (<300)
        self.assertEqual(score_respiration(200, mechanical_ventilation=True), 2)

    def test_score_3_just_below_200(self):
        self.assertEqual(score_respiration(199, mechanical_ventilation=True), 3)

    def test_score_4_with_ventilation(self):
        self.assertEqual(score_respiration(80, mechanical_ventilation=True), 4)

    def test_score_4_boundary_100(self):
        # Exactly 100 is NOT <100, so score is 3 (<200 with vent)
        self.assertEqual(score_respiration(100, mechanical_ventilation=True), 3)

    def test_score_4_just_below_100(self):
        self.assertEqual(score_respiration(99, mechanical_ventilation=True), 4)

    def test_below_200_no_ventilation_is_2(self):
        """Without ventilation, PaO2/FiO2 < 200 caps at 2, not 3."""
        self.assertEqual(score_respiration(150, mechanical_ventilation=False), 2)

    def test_below_100_no_ventilation_is_2(self):
        """Without ventilation, PaO2/FiO2 < 100 caps at 2."""
        self.assertEqual(score_respiration(50, mechanical_ventilation=False), 2)

    def test_extreme_low(self):
        self.assertEqual(score_respiration(10, mechanical_ventilation=True), 4)

    def test_extreme_high(self):
        self.assertEqual(score_respiration(600), 0)


# ======================================================================
# Coagulation sub-score
# ======================================================================
class TestCoagulation(unittest.TestCase):
    """Test score_coagulation() — platelet count."""

    def test_normal(self):
        self.assertEqual(score_coagulation(250), 0)

    def test_boundary_150(self):
        self.assertEqual(score_coagulation(150), 0)

    def test_score_1(self):
        self.assertEqual(score_coagulation(120), 1)

    def test_just_below_150(self):
        self.assertEqual(score_coagulation(149), 1)

    def test_score_2(self):
        self.assertEqual(score_coagulation(75), 2)

    def test_boundary_100(self):
        # Exactly 100 is NOT <100, so score is 1 (<150)
        self.assertEqual(score_coagulation(100), 1)

    def test_just_below_100(self):
        self.assertEqual(score_coagulation(99), 2)

    def test_score_3(self):
        self.assertEqual(score_coagulation(30), 3)

    def test_boundary_50(self):
        # Exactly 50 is NOT <50, so score is 2 (<100)
        self.assertEqual(score_coagulation(50), 2)

    def test_just_below_50(self):
        self.assertEqual(score_coagulation(49), 3)

    def test_score_4(self):
        self.assertEqual(score_coagulation(10), 4)

    def test_boundary_20(self):
        self.assertEqual(score_coagulation(20), 3)

    def test_just_below_20(self):
        self.assertEqual(score_coagulation(19), 4)

    def test_extreme_low(self):
        self.assertEqual(score_coagulation(1), 4)

    def test_extreme_high(self):
        self.assertEqual(score_coagulation(500), 0)


# ======================================================================
# Liver sub-score
# ======================================================================
class TestLiver(unittest.TestCase):
    """Test score_liver() — total bilirubin."""

    def test_normal(self):
        self.assertEqual(score_liver(0.5), 0)

    def test_boundary_1_2(self):
        self.assertEqual(score_liver(1.2), 1)

    def test_just_below_1_2(self):
        self.assertEqual(score_liver(1.19), 0)

    def test_score_1(self):
        self.assertEqual(score_liver(1.5), 1)

    def test_boundary_2_0(self):
        self.assertEqual(score_liver(2.0), 2)

    def test_just_below_2_0(self):
        self.assertEqual(score_liver(1.99), 1)

    def test_score_2(self):
        self.assertEqual(score_liver(3.5), 2)

    def test_boundary_6_0(self):
        self.assertEqual(score_liver(6.0), 3)

    def test_just_below_6_0(self):
        self.assertEqual(score_liver(5.99), 2)

    def test_score_3(self):
        self.assertEqual(score_liver(9.0), 3)

    def test_boundary_12_0(self):
        self.assertEqual(score_liver(12.0), 4)

    def test_just_below_12_0(self):
        self.assertEqual(score_liver(11.99), 3)

    def test_score_4(self):
        self.assertEqual(score_liver(20.0), 4)

    def test_zero(self):
        self.assertEqual(score_liver(0.0), 0)


# ======================================================================
# Cardiovascular sub-score
# ======================================================================
class TestCardiovascular(unittest.TestCase):
    """Test score_cardiovascular() — MAP and vasopressors."""

    def test_normal_map_no_pressors(self):
        self.assertEqual(score_cardiovascular(map_mmhg=80), 0)

    def test_no_data(self):
        self.assertEqual(score_cardiovascular(), 0)

    def test_low_map(self):
        self.assertEqual(score_cardiovascular(map_mmhg=65), 1)

    def test_boundary_map_70(self):
        self.assertEqual(score_cardiovascular(map_mmhg=70), 0)

    def test_just_below_70(self):
        self.assertEqual(score_cardiovascular(map_mmhg=69), 1)

    def test_dobutamine_any_dose(self):
        self.assertEqual(score_cardiovascular(dobutamine=5.0), 2)

    def test_dobutamine_low_dose(self):
        self.assertEqual(score_cardiovascular(dobutamine=0.1), 2)

    def test_dopamine_low(self):
        self.assertEqual(score_cardiovascular(dopamine=3.0), 2)

    def test_dopamine_boundary_5(self):
        self.assertEqual(score_cardiovascular(dopamine=5.0), 2)

    def test_dopamine_just_above_5(self):
        self.assertEqual(score_cardiovascular(dopamine=5.1), 3)

    def test_dopamine_high(self):
        self.assertEqual(score_cardiovascular(dopamine=10.0), 3)

    def test_dopamine_boundary_15(self):
        self.assertEqual(score_cardiovascular(dopamine=15.0), 3)

    def test_dopamine_just_above_15(self):
        self.assertEqual(score_cardiovascular(dopamine=15.1), 4)

    def test_dopamine_very_high(self):
        self.assertEqual(score_cardiovascular(dopamine=20.0), 4)

    def test_norepinephrine_low(self):
        self.assertEqual(score_cardiovascular(norepinephrine=0.05), 3)

    def test_norepinephrine_boundary_0_1(self):
        self.assertEqual(score_cardiovascular(norepinephrine=0.1), 3)

    def test_norepinephrine_just_above_0_1(self):
        self.assertEqual(score_cardiovascular(norepinephrine=0.11), 4)

    def test_norepinephrine_high(self):
        self.assertEqual(score_cardiovascular(norepinephrine=0.5), 4)

    def test_epinephrine_low(self):
        self.assertEqual(score_cardiovascular(epinephrine=0.05), 3)

    def test_epinephrine_high(self):
        self.assertEqual(score_cardiovascular(epinephrine=0.2), 4)

    def test_highest_wins(self):
        """Multiple vasopressors: highest applicable score wins."""
        self.assertEqual(
            score_cardiovascular(
                map_mmhg=65, dopamine=2.0, norepinephrine=0.15
            ),
            4,
        )

    def test_low_map_with_pressor(self):
        """Pressor score overrides low MAP score."""
        self.assertEqual(
            score_cardiovascular(map_mmhg=65, dopamine=8.0),
            3,
        )


# ======================================================================
# CNS sub-score
# ======================================================================
class TestCNS(unittest.TestCase):
    """Test score_cns() — Glasgow Coma Scale."""

    def test_normal(self):
        self.assertEqual(score_cns(15), 0)

    def test_score_1(self):
        self.assertEqual(score_cns(14), 1)

    def test_score_1_lower(self):
        self.assertEqual(score_cns(13), 1)

    def test_just_below_13(self):
        self.assertEqual(score_cns(12), 2)

    def test_score_2(self):
        self.assertEqual(score_cns(10), 2)

    def test_just_below_10(self):
        self.assertEqual(score_cns(9), 3)

    def test_score_3(self):
        self.assertEqual(score_cns(6), 3)

    def test_just_below_6(self):
        self.assertEqual(score_cns(5), 4)

    def test_score_4(self):
        self.assertEqual(score_cns(3), 4)

    def test_gcs_below_range_raises(self):
        """GCS below 3 is clinically invalid and must raise ValueError."""
        with self.assertRaises(ValueError):
            score_cns(1)

    def test_gcs_above_range_raises(self):
        """GCS above 15 is clinically invalid and must raise ValueError."""
        with self.assertRaises(ValueError):
            score_cns(16)


# ======================================================================
# Renal sub-score
# ======================================================================
class TestRenal(unittest.TestCase):
    """Test score_renal() — creatinine and/or urine output."""

    def test_normal_creatinine(self):
        self.assertEqual(score_renal(creatinine=0.9), 0)

    def test_boundary_1_2(self):
        self.assertEqual(score_renal(creatinine=1.2), 1)

    def test_just_below_1_2(self):
        self.assertEqual(score_renal(creatinine=1.19), 0)

    def test_score_1(self):
        self.assertEqual(score_renal(creatinine=1.5), 1)

    def test_boundary_2_0(self):
        self.assertEqual(score_renal(creatinine=2.0), 2)

    def test_score_2(self):
        self.assertEqual(score_renal(creatinine=3.0), 2)

    def test_boundary_3_5(self):
        self.assertEqual(score_renal(creatinine=3.5), 3)

    def test_score_3(self):
        self.assertEqual(score_renal(creatinine=4.0), 3)

    def test_boundary_5_0(self):
        self.assertEqual(score_renal(creatinine=5.0), 4)

    def test_score_4(self):
        self.assertEqual(score_renal(creatinine=6.0), 4)

    def test_no_data(self):
        self.assertEqual(score_renal(), 0)

    def test_uo_normal(self):
        self.assertEqual(score_renal(urine_output_ml_day=1000), 0)

    def test_uo_boundary_500(self):
        self.assertEqual(score_renal(urine_output_ml_day=500), 0)

    def test_uo_just_below_500(self):
        self.assertEqual(score_renal(urine_output_ml_day=499), 3)

    def test_uo_low(self):
        self.assertEqual(score_renal(urine_output_ml_day=300), 3)

    def test_uo_boundary_200(self):
        self.assertEqual(score_renal(urine_output_ml_day=200), 3)

    def test_uo_just_below_200(self):
        self.assertEqual(score_renal(urine_output_ml_day=199), 4)

    def test_uo_very_low(self):
        self.assertEqual(score_renal(urine_output_ml_day=50), 4)

    def test_both_creatinine_and_uo_takes_higher(self):
        """Creatinine=1.5 → 1, UO=300 → 3. Higher wins."""
        self.assertEqual(score_renal(creatinine=1.5, urine_output_ml_day=300), 3)

    def test_both_high_creatinine_low_uo(self):
        """Creatinine=4.0 → 3, UO=150 → 4. Higher wins."""
        self.assertEqual(score_renal(creatinine=4.0, urine_output_ml_day=150), 4)


# ======================================================================
# Total SOFA calculation
# ======================================================================
class TestCalculateSofa(unittest.TestCase):
    """Test calculate_sofa() composite scoring."""

    def test_healthy_patient(self):
        """All normal values should yield SOFA = 0."""
        result = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.respiratory, 0)
        self.assertEqual(result.coagulation, 0)
        self.assertEqual(result.liver, 0)
        self.assertEqual(result.cardiovascular, 0)
        self.assertEqual(result.cns, 0)
        self.assertEqual(result.renal, 0)

    def test_max_score(self):
        """Worst possible values in every system should yield 24."""
        result = calculate_sofa(
            pao2_fio2=50,
            mechanical_ventilation=True,
            platelets=10,
            bilirubin=15.0,
            map_mmhg=50,
            dopamine=20.0,
            gcs=3,
            creatinine=6.0,
            urine_output_ml_day=100,
        )
        self.assertEqual(result.total, 24)
        self.assertEqual(result.respiratory, 4)
        self.assertEqual(result.coagulation, 4)
        self.assertEqual(result.liver, 4)
        self.assertEqual(result.cardiovascular, 4)
        self.assertEqual(result.cns, 4)
        self.assertEqual(result.renal, 4)

    def test_result_type(self):
        result = calculate_sofa(pao2_fio2=400, platelets=200, gcs=15)
        self.assertIsInstance(result, SofaResult)

    def test_to_dict(self):
        result = calculate_sofa(pao2_fio2=400, platelets=200, gcs=15)
        d = result.to_dict()
        self.assertIn("total", d)
        self.assertIn("respiratory", d)
        self.assertEqual(d["total"], 0)

    def test_to_json(self):
        result = calculate_sofa(pao2_fio2=400, platelets=200, gcs=15)
        j = result.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["total"], 0)

    def test_total_is_sum_of_parts(self):
        result = calculate_sofa(
            pao2_fio2=250,       # 2
            platelets=80,        # 2
            bilirubin=3.0,       # 2
            map_mmhg=65,         # 1
            gcs=11,              # 2
            creatinine=2.5,      # 2
        )
        expected = 2 + 2 + 2 + 1 + 2 + 2
        self.assertEqual(result.total, expected)
        self.assertEqual(result.total, 11)


# ======================================================================
# qSOFA
# ======================================================================
class TestQsofa(unittest.TestCase):
    """Test calculate_qsofa() bedside screening."""

    def test_healthy(self):
        result = calculate_qsofa(respiratory_rate=16, gcs=15, systolic_bp=130)
        self.assertEqual(result.score, 0)
        self.assertFalse(result.suggests_sepsis)

    def test_rr_only(self):
        result = calculate_qsofa(respiratory_rate=24, gcs=15, systolic_bp=130)
        self.assertEqual(result.score, 1)
        self.assertFalse(result.suggests_sepsis)

    def test_two_criteria(self):
        result = calculate_qsofa(respiratory_rate=24, gcs=14, systolic_bp=130)
        self.assertEqual(result.score, 2)
        self.assertTrue(result.suggests_sepsis)

    def test_all_three(self):
        result = calculate_qsofa(respiratory_rate=28, gcs=10, systolic_bp=85)
        self.assertEqual(result.score, 3)
        self.assertTrue(result.suggests_sepsis)

    def test_boundary_rr_22(self):
        result = calculate_qsofa(respiratory_rate=22, gcs=15, systolic_bp=130)
        self.assertEqual(result.score, 1)

    def test_rr_just_below_22(self):
        result = calculate_qsofa(respiratory_rate=21, gcs=15, systolic_bp=130)
        self.assertEqual(result.score, 0)

    def test_boundary_sbp_100(self):
        result = calculate_qsofa(respiratory_rate=16, gcs=15, systolic_bp=100)
        self.assertEqual(result.score, 1)

    def test_sbp_just_above_100(self):
        result = calculate_qsofa(respiratory_rate=16, gcs=15, systolic_bp=101)
        self.assertEqual(result.score, 0)

    def test_gcs_14_is_altered(self):
        result = calculate_qsofa(respiratory_rate=16, gcs=14, systolic_bp=130)
        self.assertEqual(result.score, 1)

    def test_gcs_15_is_normal(self):
        result = calculate_qsofa(respiratory_rate=16, gcs=15, systolic_bp=130)
        self.assertEqual(result.score, 0)

    def test_result_type(self):
        result = calculate_qsofa(respiratory_rate=16)
        self.assertIsInstance(result, QsofaResult)

    def test_to_dict(self):
        result = calculate_qsofa(respiratory_rate=24, gcs=13, systolic_bp=90)
        d = result.to_dict()
        self.assertEqual(d["score"], 3)
        self.assertTrue(d["suggests_sepsis"])


# ======================================================================
# SOFA delta
# ======================================================================
class TestSofaDelta(unittest.TestCase):
    """Test sofa_delta() change tracking."""

    def test_no_change(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        delta = sofa_delta(baseline, current)
        self.assertEqual(delta["total_delta"], 0)

    def test_worsening(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(
            pao2_fio2=180, platelets=80, gcs=10, creatinine=3.0
        )
        delta = sofa_delta(baseline, current)
        self.assertGreater(delta["total_delta"], 0)

    def test_improvement(self):
        baseline = calculate_sofa(
            pao2_fio2=180, platelets=80, gcs=10, creatinine=3.0
        )
        current = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        delta = sofa_delta(baseline, current)
        self.assertLess(delta["total_delta"], 0)

    def test_per_system_deltas(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(pao2_fio2=180, platelets=80, gcs=15)
        delta = sofa_delta(baseline, current)
        self.assertEqual(delta["respiratory"], 2)
        self.assertEqual(delta["coagulation"], 2)
        self.assertEqual(delta["cns"], 0)
        self.assertEqual(delta["total_delta"], 4)


# ======================================================================
# Sepsis-3 criteria
# ======================================================================
class TestSepsis3(unittest.TestCase):
    """Test assess_sepsis3() criteria."""

    def test_meets_criteria(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(
            pao2_fio2=180, platelets=80, gcs=10, creatinine=2.5
        )
        result = assess_sepsis3(
            suspected_infection=True,
            baseline_sofa=baseline,
            current_sofa=current,
        )
        self.assertTrue(result.meets_criteria)
        self.assertGreaterEqual(result.sofa_increase, 2)

    def test_no_infection(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(
            pao2_fio2=180, platelets=80, gcs=10, creatinine=2.5
        )
        result = assess_sepsis3(
            suspected_infection=False,
            baseline_sofa=baseline,
            current_sofa=current,
        )
        self.assertFalse(result.meets_criteria)

    def test_infection_but_no_delta(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(pao2_fio2=400, platelets=200, gcs=15)
        result = assess_sepsis3(
            suspected_infection=True,
            baseline_sofa=baseline,
            current_sofa=current,
        )
        self.assertFalse(result.meets_criteria)

    def test_infection_delta_exactly_2(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(pao2_fio2=250, platelets=250, gcs=15)
        result = assess_sepsis3(
            suspected_infection=True,
            baseline_sofa=baseline,
            current_sofa=current,
        )
        self.assertTrue(result.meets_criteria)
        self.assertEqual(result.sofa_increase, 2)

    def test_with_qsofa(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(
            pao2_fio2=180, platelets=80, gcs=10, creatinine=2.5
        )
        qsofa = calculate_qsofa(respiratory_rate=26, gcs=10, systolic_bp=90)
        result = assess_sepsis3(
            suspected_infection=True,
            baseline_sofa=baseline,
            current_sofa=current,
            qsofa=qsofa,
        )
        self.assertTrue(result.meets_criteria)
        self.assertIsNotNone(result.qsofa)
        self.assertEqual(result.qsofa.score, 3)

    def test_result_to_dict(self):
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        result = assess_sepsis3(
            suspected_infection=False,
            baseline_sofa=baseline,
            current_sofa=current,
        )
        d = result.to_dict()
        self.assertIn("suspected_infection", d)
        self.assertIn("sofa_increase", d)
        self.assertIn("meets_criteria", d)


# ======================================================================
# Clinical scenarios
# ======================================================================
class TestClinicalScenarios(unittest.TestCase):
    """Realistic clinical scenarios to validate the calculator."""

    def test_septic_shock(self):
        """65M with pneumonia, on norepinephrine, intubated, AKI.
        Expected: high SOFA across multiple systems."""
        result = calculate_sofa(
            pao2_fio2=120,
            mechanical_ventilation=True,
            platelets=90,
            bilirubin=1.5,
            map_mmhg=55,
            norepinephrine=0.2,
            gcs=8,
            creatinine=3.8,
            urine_output_ml_day=250,
        )
        # Resp: 3 (120 on vent), Coag: 2, Liver: 1, CV: 4, CNS: 3, Renal: 3
        self.assertEqual(result.respiratory, 3)
        self.assertEqual(result.coagulation, 2)
        self.assertEqual(result.liver, 1)
        self.assertEqual(result.cardiovascular, 4)
        self.assertEqual(result.cns, 3)
        self.assertEqual(result.renal, 3)
        self.assertEqual(result.total, 16)
        self.assertGreaterEqual(result.total, 15)

    def test_ards(self):
        """ARDS patient: severe hypoxemia on vent, otherwise stable."""
        result = calculate_sofa(
            pao2_fio2=90,
            mechanical_ventilation=True,
            platelets=200,
            bilirubin=0.8,
            map_mmhg=75,
            gcs=15,
            creatinine=1.0,
        )
        self.assertEqual(result.respiratory, 4)
        self.assertEqual(result.total, 4)

    def test_liver_failure(self):
        """Acute liver failure: massively elevated bilirubin, coagulopathy,
        encephalopathy."""
        result = calculate_sofa(
            pao2_fio2=350,
            platelets=45,
            bilirubin=18.0,
            map_mmhg=72,
            gcs=7,
            creatinine=2.2,
        )
        # Resp: 1, Coag: 3, Liver: 4, CV: 0, CNS: 3, Renal: 2
        self.assertEqual(result.liver, 4)
        self.assertEqual(result.coagulation, 3)
        self.assertEqual(result.cns, 3)
        self.assertEqual(result.total, 13)

    def test_post_surgical_stable(self):
        """Post-op patient, all systems normal."""
        result = calculate_sofa(
            pao2_fio2=420,
            platelets=220,
            bilirubin=0.6,
            map_mmhg=85,
            gcs=15,
            creatinine=0.9,
        )
        self.assertEqual(result.total, 0)

    def test_acute_kidney_injury(self):
        """Isolated AKI, other systems normal."""
        result = calculate_sofa(
            pao2_fio2=400,
            platelets=200,
            gcs=15,
            creatinine=4.5,
            urine_output_ml_day=350,
        )
        self.assertEqual(result.renal, 3)
        self.assertEqual(result.total, 3)

    def test_dobutamine_patient(self):
        """Patient on dobutamine for cardiogenic shock."""
        result = calculate_sofa(
            pao2_fio2=300,
            platelets=180,
            map_mmhg=75,
            dobutamine=5.0,
            gcs=15,
            creatinine=1.0,
        )
        # Resp: pao2_fio2=300 → score 1 (NOT <300, so falls to <400 tier)
        # CV: dobutamine → 2
        self.assertEqual(result.respiratory, 1)
        self.assertEqual(result.cardiovascular, 2)
        self.assertEqual(result.total, 3)

    def test_multi_pressor_patient(self):
        """Patient on dopamine + norepinephrine — highest score wins."""
        result = calculate_sofa(
            pao2_fio2=400,
            platelets=200,
            map_mmhg=60,
            dopamine=12.0,
            norepinephrine=0.08,
            gcs=15,
        )
        # Dopamine 12 → 3, norepi 0.08 → 3, MAP <70 → 1. Max = 3
        self.assertEqual(result.cardiovascular, 3)
        self.assertEqual(result.total, 3)

    def test_brain_injury(self):
        """Severe TBI: GCS 4, everything else normal."""
        result = calculate_sofa(
            pao2_fio2=450,
            platelets=250,
            gcs=4,
        )
        self.assertEqual(result.cns, 4)
        self.assertEqual(result.total, 4)

    def test_sepsis3_scenario(self):
        """Full Sepsis-3 scenario: previously healthy → sepsis."""
        baseline = calculate_sofa(pao2_fio2=450, platelets=250, gcs=15)
        current = calculate_sofa(
            pao2_fio2=180,
            platelets=80,
            bilirubin=2.0,
            map_mmhg=60,
            norepinephrine=0.15,
            gcs=11,
            creatinine=2.5,
        )
        qsofa = calculate_qsofa(respiratory_rate=28, gcs=11, systolic_bp=90)
        sepsis = assess_sepsis3(
            suspected_infection=True,
            baseline_sofa=baseline,
            current_sofa=current,
            qsofa=qsofa,
        )
        self.assertTrue(sepsis.meets_criteria)
        self.assertTrue(qsofa.suggests_sepsis)
        self.assertGreater(sepsis.sofa_increase, 5)


# ======================================================================
# Edge cases
# ======================================================================
class TestEdgeCases(unittest.TestCase):
    """Boundary and edge case tests."""

    def test_respiration_boundary_at_each_cutoff(self):
        """Verify exact boundary behavior at each PaO2/FiO2 cutoff.
        SOFA uses strict < so at exact boundary the lower score applies."""
        self.assertEqual(score_respiration(400), 0)
        self.assertEqual(score_respiration(399.9), 1)
        # 300 is NOT <300 → score 1
        self.assertEqual(score_respiration(300), 1)
        self.assertEqual(score_respiration(299.9), 2)
        # 200 is NOT <200 → score 2
        self.assertEqual(score_respiration(200, True), 2)
        self.assertEqual(score_respiration(199.9, True), 3)
        # 100 is NOT <100 → score 3
        self.assertEqual(score_respiration(100, True), 3)
        self.assertEqual(score_respiration(99.9, True), 4)

    def test_coagulation_boundary_at_each_cutoff(self):
        """SOFA uses strict < so at exact boundary the lower score applies."""
        self.assertEqual(score_coagulation(150), 0)
        self.assertEqual(score_coagulation(149.9), 1)
        # 100 is NOT <100 → score 1
        self.assertEqual(score_coagulation(100), 1)
        self.assertEqual(score_coagulation(99.9), 2)
        # 50 is NOT <50 → score 2
        self.assertEqual(score_coagulation(50), 2)
        self.assertEqual(score_coagulation(49.9), 3)
        # 20 is NOT <20 → score 3
        self.assertEqual(score_coagulation(20), 3)
        self.assertEqual(score_coagulation(19.9), 4)

    def test_liver_boundary_at_each_cutoff(self):
        self.assertEqual(score_liver(1.19), 0)
        self.assertEqual(score_liver(1.2), 1)
        self.assertEqual(score_liver(1.99), 1)
        self.assertEqual(score_liver(2.0), 2)
        self.assertEqual(score_liver(5.99), 2)
        self.assertEqual(score_liver(6.0), 3)
        self.assertEqual(score_liver(11.99), 3)
        self.assertEqual(score_liver(12.0), 4)

    def test_cns_boundary_at_each_cutoff(self):
        self.assertEqual(score_cns(15), 0)
        self.assertEqual(score_cns(14), 1)
        self.assertEqual(score_cns(13), 1)
        self.assertEqual(score_cns(12), 2)
        self.assertEqual(score_cns(10), 2)
        self.assertEqual(score_cns(9), 3)
        self.assertEqual(score_cns(6), 3)
        self.assertEqual(score_cns(5), 4)

    def test_renal_creatinine_boundary_at_each_cutoff(self):
        self.assertEqual(score_renal(creatinine=1.19), 0)
        self.assertEqual(score_renal(creatinine=1.2), 1)
        self.assertEqual(score_renal(creatinine=1.99), 1)
        self.assertEqual(score_renal(creatinine=2.0), 2)
        self.assertEqual(score_renal(creatinine=3.49), 2)
        self.assertEqual(score_renal(creatinine=3.5), 3)
        self.assertEqual(score_renal(creatinine=4.99), 3)
        self.assertEqual(score_renal(creatinine=5.0), 4)

    def test_renal_uo_boundary_at_each_cutoff(self):
        self.assertEqual(score_renal(urine_output_ml_day=500), 0)
        self.assertEqual(score_renal(urine_output_ml_day=499), 3)
        self.assertEqual(score_renal(urine_output_ml_day=200), 3)
        self.assertEqual(score_renal(urine_output_ml_day=199), 4)

    def test_cardiovascular_map_boundary(self):
        self.assertEqual(score_cardiovascular(map_mmhg=70), 0)
        self.assertEqual(score_cardiovascular(map_mmhg=69.9), 1)

    def test_cardiovascular_dopamine_boundaries(self):
        self.assertEqual(score_cardiovascular(dopamine=5.0), 2)
        self.assertEqual(score_cardiovascular(dopamine=5.01), 3)
        self.assertEqual(score_cardiovascular(dopamine=15.0), 3)
        self.assertEqual(score_cardiovascular(dopamine=15.01), 4)

    def test_cardiovascular_norepinephrine_boundaries(self):
        self.assertEqual(score_cardiovascular(norepinephrine=0.1), 3)
        self.assertEqual(score_cardiovascular(norepinephrine=0.101), 4)

    def test_zero_platelets(self):
        self.assertEqual(score_coagulation(0), 4)

    def test_zero_bilirubin(self):
        self.assertEqual(score_liver(0.0), 0)

    def test_gcs_minimum(self):
        self.assertEqual(score_cns(3), 4)

    def test_sofa_result_total_auto_calculated(self):
        r = SofaResult(respiratory=1, coagulation=2, liver=3,
                       cardiovascular=4, cns=0, renal=1)
        self.assertEqual(r.total, 11)

    def test_sofa_result_total_is_not_settable(self):
        """Total is computed, not passed in."""
        r = SofaResult(respiratory=2, coagulation=2, liver=2,
                       cardiovascular=2, cns=2, renal=2)
        self.assertEqual(r.total, 12)


# ======================================================================
# CLI smoke tests
# ======================================================================
class TestCLI(unittest.TestCase):
    """Smoke tests for the CLI entry point."""

    def test_sofa_command(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main(["sofa", "--pao2-fio2", "450", "--platelets", "250",
                        "--gcs", "15"])
        self.assertEqual(rc, 0)
        output = f.getvalue()
        self.assertIn("SOFA Score: 0/24", output)

    def test_sofa_json_output(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main(["sofa", "--json", "--pao2-fio2", "450",
                        "--platelets", "250", "--gcs", "15"])
        self.assertEqual(rc, 0)
        parsed = json.loads(f.getvalue())
        self.assertEqual(parsed["total"], 0)

    def test_qsofa_command(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main(["qsofa", "--respiratory-rate", "26", "--gcs", "13",
                        "--systolic-bp", "95"])
        self.assertEqual(rc, 0)
        output = f.getvalue()
        self.assertIn("qSOFA Score: 3/3", output)
        self.assertIn("qSOFA >= 2", output)

    def test_qsofa_json_output(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main(["qsofa", "--json", "--respiratory-rate", "16",
                        "--gcs", "15", "--systolic-bp", "130"])
        self.assertEqual(rc, 0)
        parsed = json.loads(f.getvalue())
        self.assertEqual(parsed["score"], 0)

    def test_no_command_shows_help(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main([])
        self.assertEqual(rc, 1)

    def test_batch_command(self):
        import os
        import tempfile

        from cli import main

        csv_content = (
            "pao2_fio2,platelets,bilirubin,gcs,creatinine\n"
            "450,250,0.5,15,0.9\n"
            "180,80,2.5,10,3.0\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as inp:
            inp.write(csv_content)
            inp_path = inp.name

        out_path = inp_path.replace(".csv", "_out.csv")
        try:
            import contextlib
            import io
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                rc = main(["batch", "-i", inp_path, "-o", out_path])
            self.assertEqual(rc, 0)
            self.assertIn("Processed 2", f.getvalue())

            with open(out_path, newline="") as f2:
                reader = csv.DictReader(f2)
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["sofa_total"], "0")
            self.assertEqual(int(rows[1]["sofa_total"]), 10)
        finally:
            os.unlink(inp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


# ======================================================================
# Input validation tests
# ======================================================================
class TestInputValidation(unittest.TestCase):
    """Test that invalid inputs are properly rejected."""

    def test_negative_pao2_fio2_raises(self):
        with self.assertRaises(ValueError):
            score_respiration(-10)

    def test_negative_platelets_raises(self):
        with self.assertRaises(ValueError):
            score_coagulation(-5)

    def test_negative_bilirubin_raises(self):
        with self.assertRaises(ValueError):
            score_liver(-1.0)

    def test_negative_map_raises(self):
        with self.assertRaises(ValueError):
            score_cardiovascular(map_mmhg=-50)

    def test_negative_dopamine_raises(self):
        with self.assertRaises(ValueError):
            score_cardiovascular(dopamine=-1.0)

    def test_negative_dobutamine_raises(self):
        with self.assertRaises(ValueError):
            score_cardiovascular(dobutamine=-1.0)

    def test_negative_norepinephrine_raises(self):
        with self.assertRaises(ValueError):
            score_cardiovascular(norepinephrine=-0.1)

    def test_negative_epinephrine_raises(self):
        with self.assertRaises(ValueError):
            score_cardiovascular(epinephrine=-0.1)

    def test_negative_creatinine_raises(self):
        with self.assertRaises(ValueError):
            score_renal(creatinine=-1.0)

    def test_negative_urine_output_raises(self):
        with self.assertRaises(ValueError):
            score_renal(urine_output_ml_day=-100)

    def test_gcs_too_low_raises(self):
        with self.assertRaises(ValueError):
            score_cns(2)

    def test_gcs_too_high_raises(self):
        with self.assertRaises(ValueError):
            score_cns(16)

    def test_gcs_valid_range_boundaries(self):
        """GCS=3 and GCS=15 are valid boundaries."""
        self.assertEqual(score_cns(3), 4)
        self.assertEqual(score_cns(15), 0)

    def test_qsofa_negative_rr_raises(self):
        with self.assertRaises(ValueError):
            calculate_qsofa(respiratory_rate=-5)

    def test_qsofa_negative_sbp_raises(self):
        with self.assertRaises(ValueError):
            calculate_qsofa(respiratory_rate=16, systolic_bp=-10)

    def test_qsofa_gcs_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            calculate_qsofa(respiratory_rate=16, gcs=2)

    def test_calculate_sofa_negative_pao2_raises(self):
        with self.assertRaises(ValueError):
            calculate_sofa(pao2_fio2=-100, platelets=200, gcs=15)

    def test_calculate_sofa_gcs_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            calculate_sofa(pao2_fio2=400, platelets=200, gcs=2)

    def test_zero_values_are_valid(self):
        """Zero is a valid value for parameters that can be zero."""
        self.assertEqual(score_respiration(0), 2)  # <300, no vent
        self.assertEqual(score_coagulation(0), 4)
        self.assertEqual(score_liver(0), 0)
        self.assertEqual(score_renal(creatinine=0), 0)
        self.assertEqual(score_renal(urine_output_ml_day=0), 4)


# ======================================================================
# Batch CLI error handling tests
# ======================================================================
class TestBatchCLI(unittest.TestCase):
    """Test batch command error handling."""

    def test_batch_missing_file(self):
        import contextlib
        import io

        from cli import main

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            rc = main(["batch", "-i", "nonexistent_file_xyz.csv"])
        self.assertEqual(rc, 1)

    def test_batch_invalid_csv_data(self):
        import contextlib
        import io
        import os
        import tempfile

        from cli import main

        # CSV with invalid numeric data
        csv_content = "pao2_fio2,platelets,gcs\nnot_a_number,200,15\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as inp:
            inp.write(csv_content)
            inp_path = inp.name

        out_path = inp_path.replace(".csv", "_out.csv")
        try:
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                rc = main(["batch", "-i", inp_path, "-o", out_path])
            self.assertEqual(rc, 1)
        finally:
            os.unlink(inp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_batch_valid_csv_still_works(self):
        import contextlib
        import io
        import os
        import tempfile

        from cli import main

        csv_content = (
            "pao2_fio2,platelets,bilirubin,gcs\n"
            "450,250,0.5,15\n"
            "200,100,1.5,13\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as inp:
            inp.write(csv_content)
            inp_path = inp.name

        out_path = inp_path.replace(".csv", "_out.csv")
        try:
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                rc = main(["batch", "-i", inp_path, "-o", out_path])
            self.assertEqual(rc, 0)
            self.assertIn("Processed 2", f.getvalue())
        finally:
            os.unlink(inp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)



# ======================================================================
# Regression coverage for input safety and batch handling
# ======================================================================
class TestSafetyRegressions(unittest.TestCase):
    def test_reject_non_finite_measurements(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for scorer in (
                score_respiration,
                score_coagulation,
                score_liver,
            ):
                with self.subTest(value=value, scorer=scorer.__name__):
                    with self.assertRaises(ValueError):
                        scorer(value)
            with self.assertRaises(ValueError):
                score_renal(creatinine=value)
            with self.assertRaises(ValueError):
                score_cardiovascular(norepinephrine=value)
            with self.assertRaises(ValueError):
                calculate_qsofa(respiratory_rate=value)

    def test_reject_non_integer_gcs_and_invalid_ventilation(self):
        for value in (14.5, float("nan"), True, "14"):
            with self.subTest(gcs=value), self.assertRaises(ValueError):
                score_cns(value)
        with self.assertRaises(ValueError):
            score_respiration(90, mechanical_ventilation="false")
        with self.assertRaises(ValueError):
            SofaResult(0, 0, 0, 0, 0, 5)

    def test_batch_rejects_bad_boolean_and_fractional_gcs(self):
        from cli import main

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            dest = Path(directory) / "result.csv"
            for invalid_row in (
                "450,perhaps,250,0.5,15",
                "450,no,250,0.5,14.8",
                "nan,no,250,0.5,15",
            ):
                path.write_text(
                    "pao2_fio2,mechanical_ventilation,platelets,bilirubin,gcs\n"
                    + invalid_row + "\n",
                    encoding="utf-8",
                )
                self.assertEqual(main(["batch", "-i", str(path), "-o", str(dest)]), 1)
                self.assertFalse(dest.exists())

    def test_batch_rejects_overwriting_source(self):
        from cli import main

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            original = "pao2_fio2,platelets\n450,250\n"
            path.write_text(original, encoding="utf-8")
            self.assertEqual(main(["batch", "-i", str(path), "-o", str(path)]), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_strict_batch_requires_clinical_inputs(self):
        from cli import main

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            dest = Path(directory) / "out.csv"
            path.write_text("pao2_fio2,platelets,gcs\n450,250,15\n", encoding="utf-8")
            self.assertEqual(
                main(["batch", "-i", str(path), "-o", str(dest), "--strict"]),
                1,
            )
            self.assertFalse(dest.exists())

    def test_single_patient_invalid_input_is_handled(self):
        from cli import main

        self.assertEqual(main(["sofa", "--pao2-fio2", "nan"]), 2)


if __name__ == "__main__":
    unittest.main()
