import datetime as dt
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from retention import expired

spec = importlib.util.spec_from_file_location("release_version", Path(__file__).with_name("release-version.py"))
release_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_version)


def daily(day, run=1):
    return f"0.4.0+daily{day}.{run}.1.g0123456789ab-1"


class RetentionTests(unittest.TestCase):
    today = dt.date(2026, 9, 13)

    def test_keeps_all_recent_runs_and_unknown_versions(self):
        entries = [("a", daily("20260912", 1)), ("b", daily("20260912", 2)),
                   ("stable", "0.4.0-1"), ("other", "daily-something-else")]
        self.assertEqual(expired(entries, self.today), [])

    def test_time_stamped_daily_is_retained_by_date(self):
        entries = [("a", "0.4.0+daily202609011230.000009.1.g0123456789ab-1"),
                   ("b", "0.4.0+daily202609011330.000010.1.g0123456789ab-1")]
        self.assertEqual(expired(entries, self.today), ["a"])

    def test_weekly_keeps_numerically_latest_run(self):
        entries = [("older", daily("20260901", 9)), ("newer", daily("20260901", 10))]
        self.assertEqual(expired(entries, self.today), ["older"])

    def test_monthly_retention_and_year_expiry(self):
        entries = [("old-month", daily("20260701")), ("new-month", daily("20260730")),
                   ("expired", daily("20240913"))]
        self.assertCountEqual(expired(entries, self.today), ["old-month", "expired"])

    def test_last_daily_survives_quiet_upstream(self):
        self.assertEqual(expired([("last", daily("20240913"))], self.today), [])

    def test_future_dates_not_deleted(self):
        self.assertEqual(expired([("future", daily("20270913"))], self.today), [])


class VersionTests(unittest.TestCase):
    sha = "a" * 40

    def resolve(self, tag="", source="", base="0.4.0"):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            env = {"GITHUB_OUTPUT": str(output), "GITHUB_RUN_NUMBER": "12",
                   "GITHUB_RUN_ATTEMPT": "2", "RELEASE_TAG": tag, "SOURCE_SHA": source}
            with patch.dict(os.environ, env), patch.object(release_version, "git", side_effect=[
                self.sha, f'[workspace.package]\nversion = "{base}"\n'
            ]):
                release_version.main()
            return dict(line.split("=", 1) for line in output.read_text().splitlines())

    def test_stable_tag(self):
        result = self.resolve("v0.4.0")
        self.assertEqual(result["version"], "0.4.0-1")
        self.assertEqual(result["prerelease"], "false")
        self.assertEqual(result["sha"], self.sha)

    def test_fork_revision(self):
        self.assertEqual(self.resolve("v0.4.0-db9cr.2")["version"], "0.4.0-2")

    def test_daily_is_unique_per_attempt(self):
        result = self.resolve(source=self.sha)
        self.assertIn(".000012.2.gaaaaaaaaaaaa-1", result["version"])
        self.assertEqual(result["tag"], "daily-" + result["version"])
        self.assertRegex(result["version"], r"\+daily\d{12}\.000012\.")
        self.assertEqual(result["prerelease"], "true")

    def test_mismatched_version_rejected(self):
        with self.assertRaises(SystemExit):
            self.resolve("v0.5.0")

    def test_mismatched_source_rejected(self):
        with self.assertRaises(SystemExit):
            self.resolve("v0.4.0", "b" * 40)

    def test_invalid_input_rejected(self):
        for tag, source in [("--help", ""), ("", "abc123"), ("v0.4.0;id", "")]:
            with self.subTest(tag=tag, source=source), self.assertRaises(SystemExit):
                self.resolve(tag, source)


if __name__ == "__main__":
    unittest.main()
