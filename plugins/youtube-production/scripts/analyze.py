#!/usr/bin/env python3
"""Dependency-free retention and two-arm experiment analysis."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist


class AnalysisError(ValueError):
    """Raised for invalid or insufficient analysis input."""


def _number(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisError(f"{label} must be a number") from exc
    if not math.isfinite(result):
        raise AnalysisError(f"{label} must be finite")
    return result


def _integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnalysisError(f"{label} must be an integer")
    return value


def _bounded(value, low, high, label):
    if not low <= value <= high:
        raise AnalysisError(f"{label} must be between {low:g} and {high:g}")


def _axis_seconds(value, unit, duration, label):
    limits = {"seconds": duration, "percent": 100.0, "ratio": 1.0}
    _bounded(value, 0.0, limits[unit], label)
    if unit == "seconds":
        return value
    scale = 100.0 if unit == "percent" else 1.0
    return duration * value / scale


def _value_percent(value, unit, label):
    if value < 0:
        raise AnalysisError(f"{label} must be nonnegative")
    converted = value if unit == "percent" else value * 100.0
    if not math.isfinite(converted):
        raise AnalysisError(f"{label} is too large to convert to percent")
    return converted


def read_retention_csv(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"position", "retention"}.issubset(reader.fieldnames):
                raise AnalysisError("CSV must have position and retention columns")
            rows = list(reader)
    except OSError as exc:
        raise AnalysisError(f"cannot read retention CSV: {exc}") from exc
    if not rows:
        raise AnalysisError("retention CSV must contain at least two data rows")
    return rows


def analyze_retention(rows, axis_unit, value_unit, duration_seconds, source="input CSV", at_seconds=None):
    if axis_unit not in {"seconds", "percent", "ratio"}:
        raise AnalysisError("axis unit must be seconds, percent, or ratio")
    if value_unit not in {"percent", "ratio"}:
        raise AnalysisError("value unit must be percent or ratio")
    duration = _number(duration_seconds, "duration_seconds")
    if duration <= 0:
        raise AnalysisError("duration_seconds must be greater than zero")
    endpoint = min(30.0, duration) if at_seconds is None else _number(at_seconds, "at_seconds")
    if endpoint <= 0 or endpoint > duration:
        raise AnalysisError("at_seconds must be greater than zero and no greater than duration_seconds")

    points = []
    for index, row in enumerate(rows, start=2):
        position = _number(row.get("position"), f"row {index} position")
        retention = _number(row.get("retention"), f"row {index} retention")
        seconds = _axis_seconds(position, axis_unit, duration, f"row {index} position")
        percent = _value_percent(retention, value_unit, f"row {index} retention")
        if points and seconds <= points[-1][0]:
            raise AnalysisError("retention positions must be strictly increasing")
        points.append((seconds, percent))

    if len(points) < 2:
        raise AnalysisError("retention CSV must contain at least two data rows")
    if points[0][0] > endpoint or points[-1][0] < endpoint:
        raise AnalysisError(f"retention positions must bracket the {endpoint:g}-second endpoint")

    at_endpoint = None
    for left, right in zip(points, points[1:]):
        if left[0] == endpoint:
            at_endpoint = left[1]
            break
        if left[0] < endpoint <= right[0]:
            fraction = (endpoint - left[0]) / (right[0] - left[0])
            at_endpoint = left[1] + fraction * (right[1] - left[1])
            break
    if at_endpoint is None and points[-1][0] == endpoint:
        at_endpoint = points[-1][1]
    if at_endpoint is None or not math.isfinite(at_endpoint):
        raise AnalysisError("could not interpolate the requested retention endpoint")

    return {
        "analysis": "retention",
        "source": source,
        "assumptions": [
            f"position is declared as {axis_unit}; units were not inferred",
            f"retention is declared as {value_unit}",
            f"linear interpolation is used between the observations surrounding {endpoint:g} seconds",
        ],
        "measurement": {
            "duration_seconds": duration,
            "point_count": len(points),
            "axis_unit": axis_unit,
            "value_unit": value_unit,
            "endpoint_seconds": endpoint,
            "retention_at_endpoint_percent": round(at_endpoint, 6),
            "change_to_endpoint_percentage_points": round(at_endpoint - points[0][1], 6),
        },
        "uncertainty": [
            "This is an aggregate audience-watch ratio: values may exceed 100% because of replay.",
            "Percentage-point change is not a probability or a count of unique viewers who exited.",
            "The aggregate curve does not identify individual exits, explain why viewing changed, or establish causality.",
        ],
        "next_action": f"Review the opening promise and first {endpoint:g} seconds against this measured endpoint.",
    }


def wilson_interval(clicks, impressions, alpha=0.05):
    z = NormalDist().inv_cdf(1 - alpha / 2)
    rate = clicks / impressions
    denominator = 1 + z * z / impressions
    center = (rate + z * z / (2 * impressions)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / impressions + z * z / (4 * impressions * impressions)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _expected_cells_sufficient(first, second):
    total_clicks = first[0] + second[0]
    total_impressions = first[1] + second[1]
    pooled = total_clicks / total_impressions
    expected = [
        first[1] * pooled,
        first[1] * (1 - pooled),
        second[1] * pooled,
        second[1] * (1 - pooled),
    ]
    return all(value >= 5 for value in expected)


def _experiment_arms(payload):
    arms = payload.get("arms")
    if arms is None and "control" in payload and "treatment" in payload:
        arms = [payload["control"], payload["treatment"]]
    if not isinstance(arms, list) or len(arms) != 2:
        raise AnalysisError("experiment must contain exactly two arms")
    parsed = []
    for index, arm in enumerate(arms, start=1):
        if not isinstance(arm, dict):
            raise AnalysisError(f"arm {index} must be an object")
        name = arm.get("name", f"arm_{index}")
        if not isinstance(name, str) or not name.strip():
            raise AnalysisError(f"arm {index} name must be a non-empty string")
        clicks = _integer(arm.get("clicks"), f"{name} clicks")
        impressions = _integer(arm.get("impressions"), f"{name} impressions")
        if impressions <= 0:
            raise AnalysisError(f"{name} impressions must be greater than zero")
        if clicks < 0 or clicks > impressions:
            raise AnalysisError(f"{name} clicks must be between zero and impressions")
        parsed.append((name.strip(), clicks, impressions))
    return parsed


def analyze_experiment(payload, source="input JSON"):
    if not isinstance(payload, dict):
        raise AnalysisError("experiment JSON must be an object")
    design = payload.get("design")
    if not isinstance(design, dict):
        raise AnalysisError("design must be an object")
    assignment = design.get("assignment")
    horizon = design.get("horizon")
    prespecified = design.get("prespecified")
    if not isinstance(assignment, str) or assignment not in {"randomized", "sequential"}:
        raise AnalysisError("design.assignment must be randomized or sequential")
    if not isinstance(horizon, str) or horizon not in {"fixed", "sequential"}:
        raise AnalysisError("design.horizon must be fixed or sequential")
    if not isinstance(prespecified, bool):
        raise AnalysisError("design.prespecified must be true or false")
    alpha = _number(design.get("alpha", 0.05), "design.alpha")
    if not 0 < alpha < 0.5:
        raise AnalysisError("design.alpha must be greater than 0 and less than 0.5")
    if 1.0 - alpha / 2.0 == 1.0:
        raise AnalysisError("design.alpha is too small for the available floating-point precision")
    input_assumptions = payload.get("assumptions", [])
    if not isinstance(input_assumptions, list) or not all(isinstance(item, str) for item in input_assumptions):
        raise AnalysisError("assumptions must be an array of strings")

    arms = _experiment_arms(payload)
    arm_results = []
    for name, clicks, impressions in arms:
        low, high = wilson_interval(clicks, impressions, alpha)
        arm_results.append({
            "name": name,
            "clicks": clicks,
            "impressions": impressions,
            "rate_ratio": round(clicks / impressions, 8),
            "wilson_interval_ratio": [round(low, 8), round(high, 8)],
        })

    first, second = arms
    difference = second[1] / second[2] - first[1] / first[2]
    eligible = assignment == "randomized" and horizon == "fixed" and prespecified
    sufficient = _expected_cells_sufficient((first[1], first[2]), (second[1], second[2]))
    result = {
        "analysis": "experiment",
        "source": payload.get("source", source),
        "assumptions": input_assumptions + [
            "The comparison is interpretable only if assignments/exposures are independent and clicks use the same definition in both arms; aggregate counts cannot verify these conditions.",
            f"Wilson intervals use {(1 - alpha) * 100:g}% confidence",
        ],
        "design": {
            "assignment": assignment,
            "horizon": horizon,
            "prespecified": prespecified,
            "alpha": alpha,
        },
        "arms": arm_results,
        "observed_difference_percentage_points": round(difference * 100, 6),
        "uncertainty": [
            "Intervals and tests quantify sampling uncertainty, not implementation errors or external validity.",
            "A single comparison does not support guaranteed uplift or universal causality.",
            "Repeated peeking or multiple comparisons require a separately prespecified analysis and correction.",
        ],
    }

    if not eligible:
        result.update({
            "classification": "observational",
            "inference": "No causal or fixed-horizon significance claim is made for this design.",
            "next_action": "Treat the difference as descriptive and predeclare a randomized fixed-horizon two-arm test.",
        })
        return result
    if not sufficient:
        result.update({
            "classification": "inconclusive",
            "inference": "The normal-approximation two-proportion test was not run because expected cell counts are below 5.",
            "next_action": "Collect the predeclared fixed horizon without peeking or changing assignment.",
        })
        return result

    pooled = (first[1] + second[1]) / (first[2] + second[2])
    standard_error = math.sqrt(pooled * (1 - pooled) * (1 / first[2] + 1 / second[2]))
    if standard_error == 0:
        z_score, p_value = 0.0, 1.0
    else:
        z_score = difference / standard_error
        p_value = math.erfc(abs(z_score) / math.sqrt(2))
    evidence = p_value < alpha
    result.update({
        "classification": "randomized_fixed_horizon",
        "two_proportion_test": {
            "z_score": round(z_score, 8),
            "p_value_two_sided": round(p_value, 8),
            "alpha": alpha,
            "statistical_evidence_of_difference": evidence,
        },
        "inference": (
            "The prespecified test found statistical evidence of a difference; it does not guarantee future uplift."
            if evidence else
            "The prespecified test did not find sufficient statistical evidence of a difference."
        ),
        "next_action": "Record the result and design assumptions before deciding whether to replicate or adopt.",
    })
    return result


def read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"cannot read experiment JSON: {exc}") from exc


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    retention = commands.add_parser("retention", help="analyze an audience-retention CSV")
    retention.add_argument("input", type=Path)
    retention.add_argument("--axis-unit", required=True, choices=("seconds", "percent", "ratio"))
    retention.add_argument("--value-unit", required=True, choices=("percent", "ratio"))
    retention.add_argument("--duration-seconds", required=True, type=float)
    retention.add_argument("--at-seconds", type=float, help="evaluation endpoint; defaults to min(30, duration)")
    experiment = commands.add_parser("experiment", help="analyze a two-arm experiment JSON file")
    experiment.add_argument("input", type=Path)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "retention":
            result = analyze_retention(
                read_retention_csv(args.input), args.axis_unit, args.value_unit,
                args.duration_seconds, str(args.input), args.at_seconds,
            )
        else:
            result = analyze_experiment(read_json(args.input), str(args.input))
    except AnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
