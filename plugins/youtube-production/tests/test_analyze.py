import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze.py"
SPEC = importlib.util.spec_from_file_location("youtube_analyze", SCRIPT)
analyze = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analyze)


class RetentionTests(unittest.TestCase):
    def test_short_video_seconds_axis_is_not_inferred_as_percent(self):
        rows = [
            {"position": "0", "retention": "100"},
            {"position": "20", "retention": "80"},
            {"position": "40", "retention": "60"},
            {"position": "45", "retention": "55"},
        ]
        result = analyze.analyze_retention(rows, "seconds", "percent", 45, "synthetic")
        self.assertEqual(result["measurement"]["axis_unit"], "seconds")
        self.assertEqual(result["measurement"]["endpoint_seconds"], 30.0)
        self.assertEqual(result["measurement"]["retention_at_endpoint_percent"], 70.0)

    def test_ratio_axis_and_values_are_converted(self):
        rows = [
            {"position": "0", "retention": "1"},
            {"position": "0.5", "retention": "0.7"},
            {"position": "1", "retention": "0.4"},
        ]
        result = analyze.analyze_retention(rows, "ratio", "ratio", 60)
        self.assertEqual(result["measurement"]["retention_at_endpoint_percent"], 70.0)

    def test_percent_axis_interpolates_at_real_30_seconds(self):
        rows = [
            {"position": "0", "retention": "100"},
            {"position": "25", "retention": "90"},
            {"position": "75", "retention": "50"},
            {"position": "100", "retention": "40"},
        ]
        result = analyze.analyze_retention(rows, "percent", "percent", 60)
        self.assertEqual(result["measurement"]["retention_at_endpoint_percent"], 70.0)

    def test_replay_allows_retention_above_one(self):
        rows = [
            {"position": "0", "retention": "1.4"},
            {"position": "30", "retention": "1.1"},
            {"position": "45", "retention": "0.9"},
        ]
        result = analyze.analyze_retention(rows, "seconds", "ratio", 45)
        measurement = result["measurement"]
        self.assertEqual(measurement["retention_at_endpoint_percent"], 110.0)
        self.assertEqual(measurement["change_to_endpoint_percentage_points"], -30.0)
        self.assertIn("not a probability", " ".join(result["uncertainty"]))

    def test_short_default_and_explicit_exact_endpoint(self):
        rows = [
            {"position": "0", "retention": "120"},
            {"position": "10", "retention": "100"},
            {"position": "15", "retention": "90"},
        ]
        short = analyze.analyze_retention(rows, "seconds", "percent", 15)
        self.assertEqual(short["measurement"]["endpoint_seconds"], 15.0)
        self.assertEqual(short["measurement"]["retention_at_endpoint_percent"], 90.0)
        exact = analyze.analyze_retention(rows, "seconds", "percent", 15, at_seconds=10)
        self.assertEqual(exact["measurement"]["endpoint_seconds"], 10.0)
        self.assertEqual(exact["measurement"]["retention_at_endpoint_percent"], 100.0)

    def test_ratio_conversion_overflow_fails_closed(self):
        rows = [
            {"position": "0", "retention": "1e308"},
            {"position": "30", "retention": "1"},
        ]
        with self.assertRaises(analyze.AnalysisError):
            analyze.analyze_retention(rows, "seconds", "ratio", 30)

    def test_unordered_nonfinite_and_out_of_bounds_are_rejected(self):
        cases = [
            ([{"position": "0", "retention": "100"}, {"position": "30", "retention": "nan"}], "seconds", "percent"),
            ([{"position": "30", "retention": "80"}, {"position": "20", "retention": "70"}], "seconds", "percent"),
            ([{"position": "0", "retention": "-.1"}, {"position": "30", "retention": ".5"}], "seconds", "ratio"),
            ([{"position": "0", "retention": "1"}, {"position": "1.1", "retention": ".5"}], "ratio", "ratio"),
        ]
        for rows, axis, values in cases:
            with self.subTest(rows=rows), self.assertRaises(analyze.AnalysisError):
                analyze.analyze_retention(rows, axis, values, 45)

    def test_csv_requires_named_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("time,value\n0,100\n30,50\n", encoding="utf-8")
            with self.assertRaises(analyze.AnalysisError):
                analyze.read_retention_csv(path)


class ExperimentTests(unittest.TestCase):
    def payload(self, **design):
        return {
            "source": "synthetic",
            "assumptions": ["fixed eligibility rule"],
            "design": {
                "assignment": "randomized",
                "horizon": "fixed",
                "prespecified": True,
                **design,
            },
            "arms": [
                {"name": "control", "clicks": 80, "impressions": 1000},
                {"name": "variant", "clicks": 120, "impressions": 1000},
            ],
        }

    def test_randomized_fixed_horizon_reports_wilson_and_test(self):
        result = analyze.analyze_experiment(self.payload())
        self.assertEqual(result["classification"], "randomized_fixed_horizon")
        self.assertIn("two_proportion_test", result)
        self.assertEqual(len(result["arms"][0]["wilson_interval_ratio"]), 2)
        self.assertNotIn("winner", json.dumps(result).lower())

    def test_sequential_rotation_is_observational_without_p_value(self):
        result = analyze.analyze_experiment(self.payload(assignment="sequential", horizon="sequential"))
        self.assertEqual(result["classification"], "observational")
        self.assertNotIn("two_proportion_test", result)
        self.assertIn("descriptive", result["next_action"])

    def test_not_prespecified_is_observational(self):
        result = analyze.analyze_experiment(self.payload(prespecified=False))
        self.assertEqual(result["classification"], "observational")
        self.assertNotIn("two_proportion_test", result)

    def test_insufficient_exposure_is_inconclusive(self):
        payload = self.payload()
        payload["arms"] = [
            {"name": "control", "clicks": 1, "impressions": 10},
            {"name": "variant", "clicks": 2, "impressions": 10},
        ]
        result = analyze.analyze_experiment(payload)
        self.assertEqual(result["classification"], "inconclusive")
        self.assertNotIn("two_proportion_test", result)
        self.assertIn("expected cell counts", result["inference"])

    def test_counts_must_be_integers_and_bounded(self):
        for clicks, impressions in [(1.5, 10), (11, 10), (-1, 10), (1, 0), (True, 10)]:
            payload = self.payload()
            payload["arms"][0].update(clicks=clicks, impressions=impressions)
            with self.subTest(clicks=clicks, impressions=impressions), self.assertRaises(analyze.AnalysisError):
                analyze.analyze_experiment(payload)

    def test_assumptions_must_be_string_array(self):
        payload = self.payload()
        payload["assumptions"] = "not an array"
        with self.assertRaises(analyze.AnalysisError):
            analyze.analyze_experiment(payload)

    def test_design_fields_must_be_strings(self):
        for field, value in (("assignment", []), ("horizon", {})):
            payload = self.payload()
            payload["design"][field] = value
            with self.subTest(field=field), self.assertRaises(analyze.AnalysisError):
                analyze.analyze_experiment(payload)

    def test_alpha_must_have_representable_normal_quantile(self):
        payload = self.payload(alpha=1e-100)
        with self.assertRaisesRegex(analyze.AnalysisError, "floating-point precision"):
            analyze.analyze_experiment(payload)


class CliTests(unittest.TestCase):
    def test_retention_cli_outputs_unicode_safe_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "유지율.csv"
            path.write_text("position,retention\n0,100\n15,80\n45,50\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "retention", str(path), "--axis-unit", "seconds", "--value-unit", "percent", "--duration-seconds", "45"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["measurement"]["retention_at_endpoint_percent"], 65.0)

    def test_cli_rejects_invalid_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "experiment", str(path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("error:", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_rejects_malformed_design_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text(json.dumps({
                "design": {"assignment": [], "horizon": "fixed", "prespecified": True},
                "arms": [
                    {"name": "a", "clicks": 10, "impressions": 100},
                    {"name": "b", "clicks": 12, "impressions": 100},
                ],
            }), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "experiment", str(path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("design.assignment", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
