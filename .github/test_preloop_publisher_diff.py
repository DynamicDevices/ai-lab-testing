# These regressions intentionally use unittest assertions.
# ruff: noqa: PT009, PT027
"""Complete-diff verification regression; no network, credentials or model calls."""
import hashlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("preloop-publisher.py")
)
assert spec is not None
assert spec.loader is not None
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class CompleteDiffTests(unittest.TestCase):
    def verify(self, diff, digest=None, git_failure=False, diff_failure=False, diff_timeout=False):
        candidate = {
            "head": "a" * 40,
            "base": "b" * 40,
            "diff_sha256": digest or hashlib.sha256(diff).hexdigest(),
        }
        calls = []

        def git(argv, **kwargs):
            calls.append((argv, dict(kwargs["env"])))
            if "merge-base" in argv:
                result = ("c" * 40 + "\n").encode()
            elif "diff" in argv:
                if diff_timeout:
                    raise subprocess.TimeoutExpired(argv, 90)
                output = kwargs["stdout"]
                self.assertNotEqual(output, subprocess.PIPE)
                self.assertEqual(kwargs["timeout"], 90)
                output.write(diff)
                result = None
            else:
                result = b""
            return subprocess.CompletedProcess(
                argv, 1 if git_failure or ("diff" in argv and diff_failure) else 0, result, b""
            )

        with patch.object(publisher.subprocess, "run", side_effect=git):
            publisher.verify_diff(
                candidate, "GenMinds-UK/innovateher-lms-work", "synthetic-test-only"
            )
        diff_argv, diff_env = calls[-1]
        self.assertEqual(diff_argv[5:], [*publisher.DIFF_ARGS, "c" * 40, "a" * 40, "--"])
        self.assertNotIn("GIT_CONFIG_VALUE_0", diff_env)
        self.assertEqual(diff_env["GIT_CONFIG_COUNT"], "0")

    def test_complete_diff_just_above_former_cap(self):
        self.verify(b"x" * 100_001)

    def test_full_ih216_sized_diff_and_final_bytes_are_verified(self):
        diff = b"x" * 120_240 + b"final-bytes"
        self.assertEqual(len(diff), 120_251)
        self.verify(diff)
        with self.assertRaisesRegex(publisher.InvalidReviewError, "Diff digest mismatch"):
            self.verify(diff, hashlib.sha256(diff[:-1]).hexdigest())

    def test_altered_diff_is_refused(self):
        with self.assertRaisesRegex(publisher.InvalidReviewError, "Diff digest mismatch"):
            self.verify(b"changed", hashlib.sha256(b"original").hexdigest())

    def test_git_failure_is_not_an_approval(self):
        with self.assertRaisesRegex(
            publisher.InvalidReviewError, "Could not verify canonical Git diff"
        ):
            self.verify(b"diff", git_failure=True)

    def test_complete_multichunk_binary_diff(self):
        self.verify(bytes(range(256)) * 8192 + b"last-byte\xff")

    def test_diff_process_failure_is_not_an_approval(self):
        with self.assertRaisesRegex(
            publisher.InvalidReviewError, "Could not verify canonical Git diff"
        ):
            self.verify(b"partial diff", diff_failure=True)

    def test_diff_timeout_is_not_an_approval(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.verify(b"partial diff", diff_timeout=True)


class ReadableReviewTests(unittest.TestCase):
    def candidate(self, findings):
        return {
            "verdict": "pass_with_findings" if findings else "pass",
            "findings": findings,
            "execution_id": "12345678-1234-1234-1234-123456789abc",
            "pr": 235,
            "head": "a" * 40,
            "base": "b" * 40,
        }

    def finding(self, severity="MEDIUM", **overrides):
        return dict(
            severity=severity,
            category="test-coverage",
            file=".github/workflows/ci.yml",
            line=49,
            evidence="The new regression tests are not run in CI.",
            fix="Run the complete-diff test in CI.",
            **overrides,
        )

    def test_severities_are_readable_with_colour_and_text(self):
        findings = [self.finding(severity) for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]]
        text, marker = publisher.body(self.candidate(findings))
        for label in ["🔴 Critical", "🔴 High", "🟠 Medium", "🟡 Low"]:
            self.assertIn(label, text)
        self.assertEqual(text.count("**Problem:**"), 4)
        self.assertEqual(text.count("**Suggested fix:**"), 4)
        self.assertNotIn("<pre>", text)
        self.assertNotIn('"severity":', text)
        self.assertIn(marker, text)
        self.assertIn("a" * 40, text)
        self.assertIn("b" * 40, text)

    def test_untrusted_text_cannot_inject_html_links_or_mentions(self):
        finding = self.finding()
        finding[
            "evidence"
        ] = "<script>alert(1)</script> [click](https://example.org) @everyone\n# heading"
        text, _ = publisher.body(self.candidate([finding]))
        self.assertNotIn("<script>", text)
        self.assertNotIn("[click](https://example.org)", text)
        self.assertNotIn("@everyone", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("\\# heading", text)

    def test_large_comment_keeps_all_findings_for_github_validation(self):
        finding = self.finding()
        finding["evidence"] = "x" * 60000
        text, marker = publisher.body(self.candidate([finding]))
        self.assertIn(finding["evidence"], text)
        self.assertIn(marker, text)

    def test_authoritative_json_larger_than_former_client_limit_is_complete(self):
        value = "x" * 2_000_000 + "final-bytes"
        response = io.BytesIO(json.dumps({"result": value}).encode())
        with patch.object(publisher.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            actual = publisher.request("https://preloop.ai", "/synthetic", "synthetic")
        self.assertEqual(actual["result"], value)

    def test_no_findings_keeps_publication_identity(self):
        text, marker = publisher.body(self.candidate([]))
        self.assertIn("**No findings.**", text)
        self.assertIn(marker, text)
        self.assertNotIn("**Problem:**", text)


if __name__ == "__main__":
    unittest.main()
