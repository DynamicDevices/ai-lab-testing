"""Offline trust-boundary tests; keys generated here are synthetic test fixtures."""

# These regressions intentionally use unittest assertions.
# ruff: noqa: PT009, PT027

import base64
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("preloop-publisher.py")
)
assert SPEC is not None
assert SPEC.loader is not None
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def encoded(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


class WorkloadIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="preloop-synthetic-key-")
        cls.addClassCleanup(temporary.cleanup)
        cls.key = Path(temporary.name) / "fixture.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(cls.key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        modulus = (
            subprocess.check_output(
                ["openssl", "rsa", "-in", str(cls.key), "-modulus", "-noout"], text=True
            )
            .strip()
            .split("=", 1)[1]
        )
        cls.jwks = {
            "keys": [
                {
                    "kid": "synthetic",
                    "kty": "RSA",
                    "n": encoded(bytes.fromhex(modulus)),
                    "e": "AQAB",
                }
            ]
        }

    def claims(self):
        repository = "DynamicDevices/ai-lab-testing"
        return {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "briar-preloop-publication",
            "iat": 99,
            "exp": 101,
            "repository": repository,
            "repository_id": "1097600942",
            "run_id": "123",
            "ref": "refs/heads/main",
            "event_name": "status",
            "workflow_ref": repository
            + "/.github/workflows/preloop-review-publish.yml@refs/heads/main",
        }

    def token(self, claims, header=None):
        header = header or {"alg": "RS256", "kid": "synthetic"}
        payload = encoded(json.dumps(header).encode()) + "." + encoded(json.dumps(claims).encode())
        signature = subprocess.check_output(
            ["openssl", "dgst", "-sha256", "-sign", str(self.key)], input=payload.encode()
        )
        return payload + "." + encoded(signature)

    def verify(self, token):
        return publisher.verify_workload_jwt(
            token,
            self.jwks,
            {"repository_id": 1097600942, "default_branch": "main"},
            "DynamicDevices/ai-lab-testing",
            "123",
            now=100,
        )

    def test_real_signature_for_exact_workload_is_accepted(self):
        claims = self.claims()
        self.assertEqual(self.verify(self.token(claims)), claims)

    def test_signed_wrong_identity_branch_event_or_lifetime_is_denied(self):
        replacements = {
            "iss": "https://example.invalid",
            "aud": "wrong-audience",
            "iat": 101,
            "exp": 100,
            "repository": "DynamicDevices/another-repository",
            "repository_id": "1",
            "run_id": "124",
            "ref": "refs/heads/untrusted",
            "event_name": "pull_request",
            "workflow_ref": "DynamicDevices/ai-lab-testing/.github/workflows/other.yml@refs/heads/main",
        }
        for field, value in replacements.items():
            with self.subTest(field=field):
                claims = self.claims()
                claims[field] = value
                with self.assertRaises(publisher.InvalidReviewError):
                    self.verify(self.token(claims))

    def test_tampered_claims_are_denied_by_signature_verification(self):
        token = self.token(self.claims()).split(".")
        claims = self.claims()
        claims["extra"] = "tampered"
        token[1] = encoded(json.dumps(claims).encode())
        with self.assertRaises(publisher.InvalidReviewError):
            self.verify(".".join(token))

    def test_unknown_key_is_denied(self):
        with self.assertRaises(publisher.InvalidReviewError):
            self.verify(self.token(self.claims(), {"alg": "RS256", "kid": "foreign"}))


class RevisionAndNativeContractTests(unittest.TestCase):
    def fixture(self):
        binding = {
            "repository": "DynamicDevices/ai-lab-testing",
            "repository_id": 1097600942,
            "project_id": "project",
            "flow_id": "flow",
            "model_id": "model",
            "native_ci_contract": {
                "explicit_posture_approval": True,
                "model_verification": "approved_flow_configuration",
                "model_id": "model",
                "flow_config_sha256": "f" * 64,
            },
        }
        detail = {
            "id": "execution",
            "flow_id": "flow",
            "project_id": "project",
            "repository_identifier": "1097600942",
            "pr_number": 1,
            "head_sha": "a" * 40,
            "status": "SUCCEEDED",
        }
        artifact = {
            "execution_id": "execution",
            "status": "SUCCEEDED",
            "result": {
                "status": "success",
                "head_sha": "a" * 40,
                "base_sha": "b" * 40,
                "verdict": "pass",
                "diff_sha256": "d" * 64,
                "challenge": "c" * 48,
                "findings": [],
            },
        }
        receipt = {
            **detail,
            "execution_id": "execution",
            "base_sha": "b" * 40,
            "model_id": "model",
            "flow_config_sha256": "f" * 64,
        }
        return binding, detail, artifact, receipt

    def test_exact_native_result_requires_owned_receipt_and_explicit_contract(self):
        binding, detail, artifact, receipt = self.fixture()
        candidate = publisher.validate(detail, artifact, binding, "execution", "a" * 40, receipt)
        self.assertEqual(candidate["verdict"], "pass")
        with self.assertRaises(publisher.InvalidReviewError):
            publisher.validate(detail, artifact, binding, "execution", "a" * 40)
        binding["native_ci_contract"]["explicit_posture_approval"] = False
        with self.assertRaises(publisher.InvalidReviewError):
            publisher.validate(detail, artifact, binding, "execution", "a" * 40, receipt)

    def test_stale_base_and_altered_receipt_are_denied(self):
        for field, replacement in {
            "base_sha": "e" * 40,
            "project_id": "foreign",
            "flow_config_sha256": "0" * 64,
        }.items():
            with self.subTest(field=field):
                binding, detail, artifact, receipt = self.fixture()
                receipt[field] = replacement
                with self.assertRaises(publisher.InvalidReviewError):
                    publisher.validate(detail, artifact, binding, "execution", "a" * 40, receipt)

    def test_nonterminal_result_is_not_an_approval(self):
        binding, detail, artifact, receipt = self.fixture()
        detail["status"] = "RUNNING"
        with self.assertRaises(publisher.InvalidReviewError):
            publisher.validate(detail, artifact, binding, "execution", "a" * 40, receipt)

    def test_pr_changed_after_review_is_denied(self):
        binding, detail, artifact, receipt = self.fixture()
        candidate = publisher.validate(detail, artifact, binding, "execution", "a" * 40, receipt)
        pr = {
            "state": "open",
            "base": {"repo": {"id": 1097600942}, "sha": "b" * 40},
            "head": {"sha": "e" * 40},
        }
        with self.assertRaises(publisher.InvalidReviewError):
            publisher.current_pr(pr, candidate, binding)


if __name__ == "__main__":
    unittest.main()
