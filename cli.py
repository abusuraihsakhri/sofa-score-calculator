#!/usr/bin/env python3
"""
Command-line interface for the SOFA Score Calculator.

Provides subcommands for single-patient SOFA/qSOFA calculation and
batch processing of CSV files.

Stdlib only.
"""
import argparse
import csv
import json
import sys
from typing import Optional

from sofa import (
    calculate_sofa,
    calculate_qsofa,
    sofa_delta,
    assess_sepsis3,
    SofaResult,
)


def _add_common_sofa_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared SOFA parameter arguments to a parser."""
    # Respiratory
    parser.add_argument(
        "--pao2-fio2", type=float, required=True,
        help="PaO2/FiO2 ratio (mmHg)",
    )
    parser.add_argument(
        "--mechanical-ventilation", action="store_true",
        help="Patient is on mechanical ventilation",
    )
    # Coagulation
    parser.add_argument(
        "--platelets", type=float, default=999,
        help="Platelet count (×10³/µL, default 999 = normal)",
    )
    # Liver
    parser.add_argument(
        "--bilirubin", type=float, default=0.0,
        help="Total bilirubin (mg/dL, default 0.0)",
    )
    # Cardiovascular
    parser.add_argument(
        "--map", type=float, default=None, dest="map_mmhg",
        help="Mean arterial pressure (mmHg)",
    )
    parser.add_argument(
        "--dopamine", type=float, default=None,
        help="Dopamine dose (µg/kg/min)",
    )
    parser.add_argument(
        "--dobutamine", type=float, default=None,
        help="Dobutamine dose (µg/kg/min)",
    )
    parser.add_argument(
        "--norepinephrine", type=float, default=None,
        help="Norepinephrine dose (µg/kg/min)",
    )
    parser.add_argument(
        "--epinephrine", type=float, default=None,
        help="Epinephrine dose (µg/kg/min)",
    )
    # CNS
    parser.add_argument(
        "--gcs", type=int, default=15,
        help="Glasgow Coma Scale (3-15, default 15)",
    )
    # Renal
    parser.add_argument(
        "--creatinine", type=float, default=None,
        help="Serum creatinine (mg/dL)",
    )
    parser.add_argument(
        "--urine-output", type=float, default=None, dest="urine_output_ml_day",
        help="Urine output (mL/day)",
    )


def _sofa_from_args(args: argparse.Namespace) -> SofaResult:
    """Build a SofaResult from parsed CLI arguments."""
    return calculate_sofa(
        pao2_fio2=args.pao2_fio2,
        mechanical_ventilation=args.mechanical_ventilation,
        platelets=args.platelets,
        bilirubin=args.bilirubin,
        map_mmhg=args.map_mmhg,
        dopamine=args.dopamine,
        dobutamine=args.dobutamine,
        norepinephrine=args.norepinephrine,
        epinephrine=args.epinephrine,
        gcs=args.gcs,
        creatinine=args.creatinine,
        urine_output_ml_day=args.urine_output_ml_day,
    )


def cmd_sofa(args: argparse.Namespace) -> int:
    """Handle the 'sofa' subcommand."""
    result = _sofa_from_args(args)
    if args.json:
        print(result.to_json())
    else:
        print(f"SOFA Score: {result.total}/24")
        print(f"  Respiratory:    {result.respiratory}")
        print(f"  Coagulation:    {result.coagulation}")
        print(f"  Liver:          {result.liver}")
        print(f"  Cardiovascular: {result.cardiovascular}")
        print(f"  CNS:            {result.cns}")
        print(f"  Renal:          {result.renal}")
    return 0


def cmd_qsofa(args: argparse.Namespace) -> int:
    """Handle the 'qsofa' subcommand."""
    result = calculate_qsofa(
        respiratory_rate=args.respiratory_rate,
        gcs=args.gcs,
        systolic_bp=args.systolic_bp,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"qSOFA Score: {result.score}/3")
        print(f"  RR >= 22:      {'Yes' if result.respiratory_rate_ge_22 else 'No'}")
        print(f"  Altered mental: {'Yes' if result.altered_mentation else 'No'}")
        print(f"  SBP <= 100:    {'Yes' if result.systolic_bp_le_100 else 'No'}")
        if result.suggests_sepsis:
            print("  ** qSOFA >= 2 -- consider sepsis evaluation")
    return 0


def cmd_sepsis(args: argparse.Namespace) -> int:
    """Handle the 'sepsis' subcommand (Sepsis-3 criteria)."""
    baseline = calculate_sofa(
        pao2_fio2=args.baseline_pao2_fio2,
        platelets=args.baseline_platelets,
        bilirubin=args.baseline_bilirubin,
        map_mmhg=args.baseline_map,
        gcs=args.baseline_gcs,
        creatinine=args.baseline_creatinine,
    )
    current = _sofa_from_args(args)
    qsofa = calculate_qsofa(
        respiratory_rate=args.respiratory_rate,
        gcs=args.gcs,
        systolic_bp=args.systolic_bp,
    )
    result = assess_sepsis3(
        suspected_infection=args.suspected_infection,
        baseline_sofa=baseline,
        current_sofa=current,
        qsofa=qsofa,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        delta = sofa_delta(baseline, current)
        print(f"Sepsis-3 Assessment")
        print(f"  Suspected infection: {'Yes' if result.suspected_infection else 'No'}")
        print(f"  Baseline SOFA:      {baseline.total}")
        print(f"  Current SOFA:       {current.total}")
        print(f"  SOFA delta:         {delta['total_delta']}")
        print(f"  qSOFA:              {qsofa.score}/3")
        if result.meets_criteria:
            print("  ** MEETS Sepsis-3 criteria (infection + SOFA increase >= 2)")
        else:
            print("  OK Does NOT meet Sepsis-3 criteria")
    return 0


def _parse_float(row: dict, key: str, default: Optional[float] = None) -> Optional[float]:
    """Parse a float value from a CSV row, returning default if empty."""
    v = row.get(key, "")
    if v == "" or v is None:
        return default
    try:
        return float(v)
    except ValueError:
        raise ValueError(f"Invalid numeric value for '{key}': '{v}'")


def _parse_int(row: dict, key: str, default: int = 15) -> int:
    """Parse an int value from a CSV row, returning default if empty."""
    v = row.get(key, "")
    if v == "" or v is None:
        return default
    try:
        return int(float(v))
    except ValueError:
        raise ValueError(f"Invalid integer value for '{key}': '{v}'")


def _parse_bool(row: dict, key: str) -> bool:
    """Parse a boolean value from a CSV row."""
    v = str(row.get(key, "")).strip().lower()
    return v in ("1", "true", "yes", "y")


def cmd_batch(args: argparse.Namespace) -> int:
    """Handle the 'batch' subcommand — process a CSV of patient data."""
    try:
        with open(args.input, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Error: Permission denied reading: {args.input}", file=sys.stderr)
        return 1
    except csv.Error as e:
        print(f"Error: Malformed CSV in {args.input}: {e}", file=sys.stderr)
        return 1

    out_fields = fieldnames + [
        "sofa_respiratory", "sofa_coagulation", "sofa_liver",
        "sofa_cardiovascular", "sofa_cns", "sofa_renal", "sofa_total",
    ]
    out_rows = []
    for i, row in enumerate(rows, start=2):  # start=2 because row 1 is header
        try:
            result = calculate_sofa(
                pao2_fio2=_parse_float(row, "pao2_fio2", 400),
                mechanical_ventilation=_parse_bool(row, "mechanical_ventilation"),
                platelets=_parse_float(row, "platelets", 999),
                bilirubin=_parse_float(row, "bilirubin", 0.0),
                map_mmhg=_parse_float(row, "map_mmhg"),
                dopamine=_parse_float(row, "dopamine"),
                dobutamine=_parse_float(row, "dobutamine"),
                norepinephrine=_parse_float(row, "norepinephrine"),
                epinephrine=_parse_float(row, "epinephrine"),
                gcs=_parse_int(row, "gcs", 15),
                creatinine=_parse_float(row, "creatinine"),
                urine_output_ml_day=_parse_float(row, "urine_output_ml_day"),
            )
        except (ValueError, TypeError) as e:
            print(f"Error: Row {i}: {e}", file=sys.stderr)
            return 1

        merged = dict(row)
        merged["sofa_respiratory"] = result.respiratory
        merged["sofa_coagulation"] = result.coagulation
        merged["sofa_liver"] = result.liver
        merged["sofa_cardiovascular"] = result.cardiovascular
        merged["sofa_cns"] = result.cns
        merged["sofa_renal"] = result.renal
        merged["sofa_total"] = result.total
        out_rows.append(merged)

    try:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
    except PermissionError:
        print(f"Error: Permission denied writing: {args.output}", file=sys.stderr)
        return 1

    print(f"Processed {len(out_rows)} patients -> {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="sofa",
        description="SOFA (Sequential Organ Failure Assessment) Score Calculator",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    sub = parser.add_subparsers(dest="command")

    # sofa subcommand
    p_sofa = sub.add_parser("sofa", help="Calculate full SOFA score (0-24)")
    _add_common_sofa_args(p_sofa)
    p_sofa.add_argument("--json", action="store_true")

    # qsofa subcommand
    p_qsofa = sub.add_parser("qsofa", help="Calculate qSOFA bedside screening (0-3)")
    p_qsofa.add_argument(
        "--respiratory-rate", type=int, required=True,
        help="Respiratory rate (breaths/min)",
    )
    p_qsofa.add_argument("--gcs", type=int, default=15, help="GCS (3-15)")
    p_qsofa.add_argument(
        "--systolic-bp", type=int, default=120,
        help="Systolic BP (mmHg)",
    )
    p_qsofa.add_argument("--json", action="store_true")

    # sepsis subcommand
    p_sepsis = sub.add_parser("sepsis", help="Sepsis-3 criteria assessment")
    _add_common_sofa_args(p_sepsis)
    p_sepsis.add_argument(
        "--suspected-infection", action="store_true",
        help="Clinical suspicion of infection",
    )
    p_sepsis.add_argument(
        "--respiratory-rate", type=int, default=16,
        help="Respiratory rate (breaths/min)",
    )
    p_sepsis.add_argument(
        "--systolic-bp", type=int, default=120,
        help="Systolic BP (mmHg)",
    )
    # Baseline SOFA parameters
    p_sepsis.add_argument("--baseline-pao2-fio2", type=float, default=400)
    p_sepsis.add_argument("--baseline-platelets", type=float, default=999)
    p_sepsis.add_argument("--baseline-bilirubin", type=float, default=0.0)
    p_sepsis.add_argument("--baseline-map", type=float, default=None)
    p_sepsis.add_argument("--baseline-gcs", type=int, default=15)
    p_sepsis.add_argument("--baseline-creatinine", type=float, default=None)
    p_sepsis.add_argument("--json", action="store_true")

    # batch subcommand
    p_batch = sub.add_parser("batch", help="Batch process CSV of patient data")
    p_batch.add_argument("-i", "--input", required=True, help="Input CSV file")
    p_batch.add_argument("-o", "--output", default="results.csv", help="Output CSV file")

    return parser


def main(argv=None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    handlers = {
        "sofa": cmd_sofa,
        "qsofa": cmd_qsofa,
        "sepsis": cmd_sepsis,
        "batch": cmd_batch,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
