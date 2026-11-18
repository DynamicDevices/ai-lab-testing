# These regressions intentionally use unittest assertions.
# ruff: noqa: PT009, PT027
import ast
import json
import os
import re
import tempfile
import types
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent
SOURCE = (ROOT / "preloop-trigger.py").read_text()
TREE = ast.parse(SOURCE)


class DeniedError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise DeniedError(message)


namespace = {"publisher": types.SimpleNamespace(require=require, re=re)}
function = next(
    n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "select_owned_execution"
)
exec(
    compile(ast.Module(body=[function], type_ignores=[]), str(ROOT / "preloop-trigger.py"), "exec"),
    namespace,
)
select = namespace["select_owned_execution"]
EXPECTED = {
    "flow_id": "flow",
    "project_id": "project",
    "repository_identifier": "1385545254",
    "pr_number": 227,
    "head_sha": "a" * 40,
}
OLD = dict(EXPECTED, id="90464d9f-1103-4a08-9c62-0805ed082274", status="FAILED")
NEW = dict(EXPECTED, id="84d4d914-3940-49d0-9efc-157f2e9d62b4", status="RUNNING")


class ExplicitRetryTests(unittest.TestCase):
    def test_no_existing_execution_retains_normal_initial_launch(self):
        self.assertIsNone(select([], EXPECTED))

    def test_single_owned_execution_retains_normal_reuse(self):
        self.assertEqual(select([OLD], EXPECTED), OLD)

    def test_multiple_executions_require_explicit_selection(self):
        with self.assertRaises(DeniedError):
            select([OLD, NEW], EXPECTED)

    def test_explicit_retry_selects_exact_execution_without_status_approval(self):
        for status in ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]:
            with self.subTest(status=status):
                row = dict(NEW, status=status)
                self.assertEqual(select([OLD, row], EXPECTED, NEW["id"]), row)
        # Selection only supplies the receipt: the unchanged publisher owns verdict validation.

    def test_wrong_ownership_never_selects_or_launches(self):
        for field in EXPECTED:
            with self.subTest(field=field):
                foreign = dict(NEW, **{field: "foreign"})
                with self.assertRaises(DeniedError):
                    select([OLD, foreign], EXPECTED, NEW["id"])

    def test_unknown_or_absent_selected_execution_refuses_instead_of_launching(self):
        for rows in [[], [OLD]]:
            with self.subTest(rows=rows), self.assertRaises(DeniedError):
                select(rows, EXPECTED, NEW["id"])

    def test_malformed_execution_id_is_rejected(self):
        for value in [
            "",
            "not-an-id",
            "../result",
            227,
            {},
            "84D4D914-3940-49D0-9EFC-157F2E9D62B4",
        ]:
            with self.subTest(value=value), self.assertRaises(DeniedError):
                select([NEW], EXPECTED, value)

    def test_duplicate_selected_execution_is_rejected(self):
        with self.assertRaises(DeniedError):
            select([NEW, NEW], EXPECTED, NEW["id"])

    def test_unrelated_history_cannot_change_the_selected_owned_execution(self):
        foreign = dict(NEW, flow_id="foreign")
        self.assertEqual(select([foreign, OLD, NEW], EXPECTED, NEW["id"]), NEW)


class PrepareAndReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.rows = []
        self.pr_overrides = {}
        self.requests = []
        self.binding = dict(
            EXPECTED,
            repository="GenMinds-UK/innovateher-lms-work",
            repository_id=1385545254,
            default_branch="main",
            model_id="model",
            native_ci_contract={
                "explicit_posture_approval": True,
                "model_verification": "approved_flow_configuration",
                "model_id": "model",
                "flow_config_sha256": "d" * 64,
            },
        )
        fake = types.SimpleNamespace(
            require=require,
            re=re,
            load_authority=lambda *_: self.binding,
            verify_workload=lambda *_, **__: {"workflow_sha": "c" * 40},
            verify_sources=lambda *_: None,
            request=self.request,
            execution_id=lambda url: url.rsplit("/", 1)[-1],
        )
        self.module = {"publisher": fake, "json": json, "os": os, "Path": Path, "urllib": urllib}
        functions = [
            n
            for n in TREE.body
            if isinstance(n, ast.FunctionDef)
            and n.name in ["select_owned_execution", "prepare", "start"]
        ]
        exec(
            compile(
                ast.Module(body=functions, type_ignores=[]),
                str(ROOT / "preloop-trigger.py"),
                "exec",
            ),
            self.module,
        )
        environment = {
            "GITHUB_REPOSITORY": self.binding["repository"],
            "PRELOOP_CI_TRIGGER_TOKEN": "ci_synthetic",
            "GH_TOKEN": "synthetic",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_EVENT_PATH": str(self.directory / "event.json"),
            "GITHUB_RUN_ID": "123",
            "GITHUB_OUTPUT": str(self.directory / "output"),
            "RUNNER_TEMP": str(self.directory),
        }
        self.environment = mock.patch.dict(os.environ, environment)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def request(self, origin, path, _token, method="GET", payload=None):
        self.requests.append((method, origin, path))
        if method != "GET":
            raise AssertionError("Reusing an execution must never make a launch request")
        if path.startswith("/api/v1/flows/executions?"):
            return self.rows
        if path.startswith("/api/v1/flows/executions/"):
            return next(row for row in self.rows if path.endswith("/" + row["id"]))
        if path.endswith("/pulls/227"):
            response = {
                "state": "open",
                "draft": False,
                "user": {"login": "trusted-fixture"},
                "labels": [],
                "author_association": "MEMBER",
                "head": {"sha": EXPECTED["head_sha"], "repo": {"id": 1385545254}},
                "base": {"sha": "b" * 40, "ref": "main", "repo": {"id": 1385545254}},
            }
            response.update(self.pr_overrides)
            return response
        if "/actions/artifacts?" in path:
            return {"total_count": 0, "artifacts": []}
        raise AssertionError("Unexpected request: " + path)

    def prepare(self, rows, selection=None, automatic=False):
        self.rows = rows
        event = {"number": 227} if automatic else {"inputs": {"pr_number": "227"}}
        if selection is not None:
            event["inputs"]["execution_id"] = selection
        os.environ["GITHUB_EVENT_NAME"] = (
            "pull_request_target" if automatic else "workflow_dispatch"
        )
        (self.directory / "event.json").write_text(json.dumps(event))
        self.module["prepare"]()
        return (
            json.loads((self.directory / "preloop-trigger-intent.json").read_text()),
            (self.directory / "output").read_text(),
        )

    def test_first_automatic_review_writes_a_durable_intent_request(self):
        intent, output = self.prepare([], automatic=True)
        self.assertIsNone(intent["existing_execution_id"])
        self.assertIn("needs_intent=true", output)

    def test_dispatch_cannot_bypass_review_eligibility(self):
        for overrides in [
            {"draft": True},
            {"user": {"login": "dependabot[bot]"}},
            {"labels": [{"name": "preloop-skip-review"}]},
            {"author_association": "CONTRIBUTOR"},
        ]:
            with self.subTest(overrides=overrides):
                self.pr_overrides = overrides
                with self.assertRaises(DeniedError):
                    self.prepare([])
                self.assertFalse((self.directory / "preloop-trigger-intent.json").exists())

    def test_existing_automatic_review_is_reused_without_a_new_intent(self):
        intent, output = self.prepare([OLD], automatic=True)
        self.assertEqual(intent["existing_execution_id"], OLD["id"])
        self.assertIn("needs_intent=false", output)

    def test_explicit_owned_retry_writes_its_exact_binding(self):
        intent, output = self.prepare([OLD, NEW], NEW["id"])
        self.assertEqual(intent["existing_execution_id"], NEW["id"])
        self.assertEqual(intent["head_sha"], EXPECTED["head_sha"])
        self.assertEqual(intent["base_sha"], "b" * 40)
        self.assertIn("needs_intent=false", output)

    def test_automatic_ambiguity_refuses_before_writing_an_intent(self):
        with self.assertRaisesRegex(DeniedError, "Ambiguous existing review"):
            self.prepare([OLD, NEW], automatic=True)
        self.assertFalse((self.directory / "preloop-trigger-intent.json").exists())

    def test_unknown_explicit_retry_refuses_instead_of_launching(self):
        with self.assertRaisesRegex(DeniedError, "Selected execution is missing"):
            self.prepare([OLD], NEW["id"])
        self.assertFalse((self.directory / "preloop-trigger-intent.json").exists())

    def test_successful_selected_execution_is_reused_without_a_model_launch(self):
        successful = dict(NEW, status="SUCCEEDED")
        self.prepare([OLD, successful], NEW["id"])
        self.module["start"]()
        receipt = json.loads((self.directory / "preloop-trigger-receipt/receipt.json").read_text())
        self.assertEqual(receipt["execution_id"], NEW["id"])
        self.assertEqual(receipt["head_sha"], EXPECTED["head_sha"])
        self.assertEqual(receipt["base_sha"], "b" * 40)
        self.assertTrue(all(method == "GET" for method, _, _ in self.requests))


if __name__ == "__main__":
    unittest.main(verbosity=2)
