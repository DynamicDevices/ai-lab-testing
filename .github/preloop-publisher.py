"""Publish authoritative Preloop results without executing PR code or rerunning models."""
import base64
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

KEY = "SHA256:vBkafuWAZYu5NnpYdbW8z1ZbZp/VFuSl8mad9jo0UFc"
NAMESPACE = "briar-preloop-publication"
DIFF_ARGS = [
    "diff",
    "--no-ext-diff",
    "--no-textconv",
    "--no-color",
    "--full-index",
    "--no-renames",
    "--diff-algorithm=myers",
    "--no-indent-heuristic",
    "--unified=3",
    "--inter-hunk-context=0",
    "--src-prefix=a/",
    "--dst-prefix=b/",
]


class InvalidReviewError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidReviewError(message)


def request(origin, path, token, method="GET", body=None):
    # Never follow a provider/GitHub redirect with credentials.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Briar-Preloop-Publisher/1",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(origin + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
            # Read the complete authoritative result. Transport and workflow
            # deadlines bound this attempt; a guessed byte quota must not
            # discard review findings or turn a partial result into approval.
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise InvalidReviewError(f"{method} API request failed HTTP{exc.code}") from None


def execution_id(url):
    match = re.fullmatch(r"https://preloop\.ai/console/flows/executions/([0-9a-f-]{36})", url or "")
    require(match is not None, "Unexpected execution URL")
    import uuid

    return str(uuid.UUID(match[1]))


def verify_workload_jwt(
    token, jwks, binding, repository, run_id, now=None, workflow="preloop-review-publish.yml"
):
    import time

    parts = token.split(".")
    require(len(parts) == 3 and len(token) <= 32_000, "Invalid workload identity")

    def decode(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    header, claims = (json.loads(decode(x)) for x in parts[:2])
    require(header.get("alg") == "RS256", "Unsupported workload signature")
    keys = [k for k in jwks["keys"] if k.get("kid") == header.get("kid") and k.get("kty") == "RSA"]
    require(len(keys) == 1, "Unknown workload signing key")
    with tempfile.TemporaryDirectory() as temp:

        def der(tag, content):
            length = len(content)
            encoded = (
                bytes([length])
                if length < 128
                else bytes([128 + ((length.bit_length() + 7) // 8)])
                + length.to_bytes((length.bit_length() + 7) // 8, "big")
            )
            return bytes([tag]) + encoded + content

        def integer(value):
            number = decode(value).lstrip(b"\0") or b"\0"
            return der(2, (b"\0" if number[0] & 128 else b"") + number)

        require(256 <= len(decode(keys[0]["n"])) <= 1024, "Unsafe RSA modulus size")
        encoded_key = Path(temp) / "public.der"
        encoded_key.write_bytes(der(48, integer(keys[0]["n"]) + integer(keys[0]["e"])))
        extracted = subprocess.run(
            [
                "openssl",
                "rsa",
                "-RSAPublicKey_in",
                "-inform",
                "DER",
                "-in",
                str(encoded_key),
                "-pubout",
            ],
            check=False,
            capture_output=True,
        )
        require(extracted.returncode == 0, "Invalid workload certificate")
        public_key = Path(temp) / "public.pem"
        public_key.write_bytes(extracted.stdout)
        signature = Path(temp) / "signature"
        signature.write_bytes(decode(parts[2]))
        verified = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                str(public_key),
                "-signature",
                str(signature),
            ],
            check=False,
            input=(parts[0] + "." + parts[1]).encode(),
            capture_output=True,
        )
        require(verified.returncode == 0, "Workload signature invalid")
    clock = int(time.time()) if now is None else now
    require(
        claims.get("iss") == "https://token.actions.githubusercontent.com",
        "Workload issuer mismatch",
    )
    require(claims.get("aud") == "briar-preloop-publication", "Workload audience mismatch")
    require(claims["iat"] <= clock < claims["exp"], "Workload token not current")
    require(
        claims.get("repository") == repository
        and str(claims.get("repository_id")) == str(binding["repository_id"]),
        "Workload repository mismatch",
    )
    require(str(claims.get("run_id")) == str(run_id), "Workload run mismatch")
    require(
        claims.get("ref") == "refs/heads/" + binding["default_branch"], "Untrusted workflow branch"
    )
    require(
        workflow in ["preloop-review-publish.yml", "preloop-review-trigger.yml"],
        "Unapproved workflow",
    )
    expected = (
        repository + "/.github/workflows/" + workflow + "@refs/heads/" + binding["default_branch"]
    )
    require(claims.get("workflow_ref") == expected, "Workload workflow mismatch")
    events = (
        ["status", "workflow_dispatch"]
        if workflow == "preloop-review-publish.yml"
        else ["pull_request_target", "workflow_dispatch"]
    )
    require(claims.get("event_name") in events, "Unexpected workload event")
    return claims


def verify_workload(binding, repository, workflow="preloop-review-publish.yml"):
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    parsed = urllib.parse.urlsplit(url)
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.hostname.endswith(".actions.githubusercontent.com")
        and parsed.username is None
        and parsed.port in [None, 443],
        "Untrusted OIDC endpoint",
    )
    separator = "&" if parsed.query else "?"
    endpoint = url + separator + "audience=briar-preloop-publication"
    response = request(
        "https://" + parsed.netloc,
        endpoint.split(parsed.netloc, 1)[1],
        os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    )
    jwks = request("https://token.actions.githubusercontent.com", "/.well-known/jwks", "")
    claims = verify_workload_jwt(
        response["value"], jwks, binding, repository, os.environ["GITHUB_RUN_ID"], workflow=workflow
    )
    require(claims["event_name"] == os.environ["GITHUB_EVENT_NAME"], "Workload event changed")
    return claims


def binding_from_proof(package, root):
    binding = package["binding"]
    raw = json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.sha256(b"\x00" + raw).digest()
    proof = package["proof"]
    require(isinstance(proof, list) and len(proof) <= 32, "Invalid binding proof")
    for step in proof:
        require(
            step["side"] in ["left", "right"] and re.fullmatch("[0-9a-f]{64}", step["sha256"]),
            "Invalid proof step",
        )
        sibling = bytes.fromhex(step["sha256"])
        left, right = (sibling, digest) if step["side"] == "left" else (digest, sibling)
        digest = hashlib.sha256(b"\x01" + left + right).digest()
    require(digest.hex() == root, "Repository binding is not in signed authority")
    return binding


def load_authority(folder, repository, now=None):
    folder = Path(folder)
    raw = (folder / "preloop-publication-authority.json").read_bytes()
    key = folder / "preloop-publication-key.pub"
    fingerprint = subprocess.check_output(["ssh-keygen", "-lf", str(key)], text=True).split()[1]
    require(fingerprint == KEY, "Publisher authority key changed")
    with tempfile.TemporaryDirectory() as temp:
        signers = Path(temp) / "signers"
        signers.write_text("ajlennon@dynamicdevices.co.uk " + key.read_text().strip() + "\n")
        p = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(signers),
                "-I",
                "ajlennon@dynamicdevices.co.uk",
                "-n",
                NAMESPACE,
                "-s",
                str(folder / "preloop-publication-authority.json.sig"),
            ],
            check=False,
            input=raw,
            capture_output=True,
        )
        require(p.returncode == 0, "Publisher authority signature invalid")
    grant = json.loads(raw)
    clock = now or dt.datetime.now(dt.timezone.utc)
    authority = grant["publisher_authority"]
    issued = dt.datetime.fromisoformat(authority["issued_at"])
    expires = dt.datetime.fromisoformat(authority["expires_at"])
    require(issued <= clock < expires, "Publisher authority not currently valid")
    require(authority["non_delegable"] is True, "Publisher grant must be non-delegable")
    if "bindings_root" in authority:
        package = json.loads((folder / "preloop-binding.json").read_text())
        binding = binding_from_proof(package, authority["bindings_root"])
        require(binding["repository"] == repository, "Binding belongs to another repository")
    else:
        binding = next((b for b in authority["bindings"] if b["repository"] == repository), None)
    require(binding is not None, "Repository not enrolled in publisher authority")
    for rel, expected in authority["files"].items():
        require(
            hashlib.sha256((folder.parent / rel).read_bytes()).hexdigest() == expected,
            "Publisher code/workflow changed since approval",
        )
    return {
        **binding,
        "publication_enabled": authority.get("publication_enabled", False),
        "approved_files": authority["files"],
        "native_ci_contract": authority.get("native_ci_contract"),
        "approved_workflow_sha256": authority["files"][
            ".github/workflows/preloop-review-publish.yml"
        ],
    }


def validate(detail, artifact, binding, eid, event_sha, receipt=None):
    native = "trigger_event_details" not in detail
    if native:
        policy = binding.get("native_ci_contract", {})
        require(
            policy.get("model_verification") == "approved_flow_configuration"
            and policy.get("explicit_posture_approval") is True
            and policy.get("model_id") == binding["model_id"]
            and receipt is not None
            and receipt.get("model_id") == binding["model_id"]
            and receipt.get("flow_config_sha256") == policy.get("flow_config_sha256"),
            "Missing explicitly approved native model contract",
        )
        require(isinstance(receipt, dict), "Missing trusted trigger receipt")
        for k, value in {
            "execution_id": eid,
            "flow_id": binding["flow_id"],
            "project_id": binding["project_id"],
            "repository_identifier": str(binding["repository_id"]),
            "pr_number": detail.get("pr_number"),
            "head_sha": event_sha,
        }.items():
            require(receipt.get(k) == value, "Trigger receipt binding mismatch")
        require(
            detail["repository_identifier"] == str(binding["repository_id"])
            and detail["project_id"] == binding["project_id"]
            and detail["head_sha"] == event_sha,
            "Native execution binding mismatch",
        )
        if artifact is not None:
            require(
                artifact["result"].get("base_sha") == receipt["base_sha"],
                "Reviewed base differs from controller binding; merge current main into the feature branch before a new review",
            )
        detail = {
            **detail,
            "trigger_event_details": {
                "project_id": detail["project_id"],
                "payload": {
                    "pull_request": {
                        "number": detail["pr_number"],
                        "head": {"sha": detail["head_sha"]},
                        "base": {
                            "sha": receipt["base_sha"],
                            "repo": {
                                "id": binding["repository_id"],
                                "full_name": binding["repository"],
                            },
                        },
                    }
                },
            },
        }
    require(detail["id"] == eid, "Execution mismatch")
    if detail["status"] == "SUCCEEDED":
        require(
            artifact is not None and artifact["execution_id"] == eid, "Artifact execution mismatch"
        )
    require(detail["flow_id"] == binding["flow_id"], "Flow mismatch")
    context = detail["trigger_event_details"]
    require(context["project_id"] == binding["project_id"], "Project mismatch")
    if not native:
        require(context["_model_routing"]["ai_model_id"] == binding["model_id"], "Model mismatch")
    pr = context["payload"]["pull_request"]
    require(pr["base"]["repo"]["id"] == binding["repository_id"], "Repository identity mismatch")
    require(pr["base"]["repo"]["full_name"] == binding["repository"], "Repository name mismatch")
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    require(head == event_sha and re.fullmatch("[0-9a-f]{40}", head), "Head mismatch")
    require(re.fullmatch("[0-9a-f]{40}", base), "Invalid base")
    require(
        detail["status"] in ["SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"], "Review not terminal"
    )
    if detail["status"] != "SUCCEEDED":
        return {
            "execution_id": eid,
            "pr": pr["number"],
            "head": head,
            "base": base,
            "verdict": "execution_failed",
            "findings": [],
            "diff_sha256": None,
        }
    require(artifact["status"] == "SUCCEEDED", "Artifact did not succeed")
    review = artifact["result"]
    require(review["status"] == "success" and review["head_sha"] == head, "Review result mismatch")
    require(review["verdict"] in ["pass", "pass_with_findings", "fail"], "Invalid verdict")
    require(re.fullmatch("[0-9a-f]{64}", review["diff_sha256"]), "Invalid diff digest")
    require(re.fullmatch("[0-9a-f]{48}", review["challenge"]), "Missing review challenge")
    require(
        isinstance(review["findings"], list)
        and all(isinstance(f, dict) for f in review["findings"]),
        "Invalid findings",
    )
    require(review["verdict"] != "pass" or not review["findings"], "Clean verdict with findings")
    return {
        "execution_id": eid,
        "pr": pr["number"],
        "head": head,
        "base": base,
        "verdict": review["verdict"],
        "findings": review["findings"],
        "diff_sha256": review["diff_sha256"],
    }


def current_pr(pr, candidate, binding):
    require(pr["state"] == "open", "PR is closed")
    require(pr["base"]["repo"]["id"] == binding["repository_id"], "PR target changed")
    require(
        pr["head"]["sha"] == candidate["head"] and pr["base"]["sha"] == candidate["base"],
        "PR head/base changed; review is stale. Merge current main into the feature branch before a new review",
    )


def verify_diff(candidate, repository, github_token):
    if candidate["diff_sha256"] is None:
        return
    # Bare object storage: no checkout, hooks, PR scripts, textconv or external diff.
    with tempfile.TemporaryDirectory() as temp:
        env = dict(
            os.environ,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_NO_REPLACE_OBJECTS="1",
            GIT_TERMINAL_PROMPT="0",
        )

        def git(*args, output=None):
            p = subprocess.run(
                ["git", "-C", temp, "-c", "core.hooksPath=/dev/null", *args],
                check=False,
                env=env,
                stdout=output if output is not None else subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
            )
            require(p.returncode == 0, "Could not verify canonical Git diff")
            return p.stdout

        git("init", "--bare", "--quiet")
        auth = base64.b64encode(("x-access-token:" + github_token).encode()).decode()
        env.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0="AUTHORIZATION: basic " + auth,
        )
        git(
            "fetch",
            "--quiet",
            "--no-tags",
            "https://github.com/" + repository + ".git",
            candidate["base"],
            candidate["head"],
        )
        env.pop("GIT_CONFIG_VALUE_0")
        env["GIT_CONFIG_COUNT"] = "0"
        base = git("merge-base", candidate["base"], candidate["head"]).decode().strip()
        # Spool the complete canonical diff to private temporary storage rather
        # than allocating it in Python memory. The existing 90-second Git timeout
        # and nonzero-exit refusal remain; storage/timeout failures never approve.
        with tempfile.TemporaryFile() as diff:
            git(*DIFF_ARGS, base, candidate["head"], "--", output=diff)
            diff.seek(0)
            digest = hashlib.file_digest(diff, "sha256").hexdigest()
        require(digest == candidate["diff_sha256"], "Diff digest mismatch")


def body(candidate):
    verdict = candidate["verdict"]
    summary = {
        "pass": "**No findings.**",
        "pass_with_findings": "**Findings reported.**",
        "fail": "**Changes required.**",
        "execution_failed": "**Review failed to complete.**",
    }[verdict]
    findings = candidate["findings"]
    rendered = ""
    if findings:
        # Findings are untrusted text. Keep them readable without allowing HTML,
        # Markdown links/headings or mention notifications from repository input.
        def prose(value):
            text = html.escape(str(value), quote=False).replace("@", "@\u200b")
            return re.sub(r"([\\`*_{}\[\]()#+\-.!|~>])", r"\\\1", text)

        colours = {
            "CRITICAL": "🔴",
            "HIGH": "🔴",
            "MEDIUM": "🟠",
            "LOW": "🟡",
            "P0": "🔴",
            "P1": "🔴",
            "P2": "🟠",
            "P3": "🟡",
        }
        sections = []
        for finding in findings:
            severity = str(finding.get("severity", finding.get("priority", "Unknown"))).upper()
            category = str(finding.get("category", "Finding")).replace("-", " ").capitalize()
            sections.append(
                f'### {colours.get(severity, "⚪")} {prose(severity.title())} — {prose(category)}\n\n'
                f'**Where:** {prose(finding.get("file", "Not specified"))}:{prose(finding.get("line", ""))}\n\n'
                f'**Problem:** {prose(finding.get("evidence", "Not specified"))}\n\n'
                f'**Suggested fix:** {prose(finding.get("fix", "Not specified"))}'
            )
        rendered = "\n\n" + "\n\n".join(sections)
    eid = candidate["execution_id"]
    marker = f'<!-- preloop-publication:{eid}:{candidate["pr"]}:{candidate["head"]} -->'
    text = (
        f"### Preloop review\n\n{summary}\n\n"
        f'Reviewed commit: `{candidate["head"]}`\n\nBase commit: `{candidate["base"]}`\n\n'
        f"[Review execution](https://preloop.ai/console/flows/executions/{eid})"
        + rendered
        + "\n\nA review result does not approve merging.\n\nAssisted-by: Briar\n\n"
        + marker
    )
    # Submit the complete body. GitHub enforces its actual API limit; rejection
    # remains a publication failure, never a truncated or passing review.
    return text, marker


def clean(candidate):
    return candidate["verdict"] in ["pass", "pass_with_findings"] and all(
        str(f.get("severity", f.get("priority", "unknown"))).lower() in ["low", "p3"]
        for f in candidate["findings"]
    )


def publish(candidate, binding, github, run_url, check=None):
    repo = "/repos/" + binding["repository"]
    path = repo + "/pulls/" + str(candidate["pr"])
    text, marker = body(candidate)
    check = check or github(
        repo + "/check-runs",
        "POST",
        {
            "name": "Preloop review",
            "head_sha": candidate["head"],
            "status": "in_progress",
            "details_url": run_url,
            "external_id": "preloop:" + candidate["execution_id"],
            "output": {
                "title": "Validating review publication",
                "summary": "Waiting for comment readback.",
            },
        },
    )
    intent_written = False
    try:
        current_pr(github(path), candidate, binding)
        existing = []
        for page in range(1, 11):
            items = github(path + f"/reviews?per_page=100&page={page}")
            existing.extend(items)
            if len(items) < 100:
                break
        else:
            raise InvalidReviewError("Review history exceeds deduplication bound")
        matching = [
            r
            for r in existing
            if marker in r.get("body", "")
            and r.get("user", {}).get("login") == "github-actions[bot]"
            and r.get("commit_id") == candidate["head"]
            and r.get("state") == "COMMENTED"
        ]
        require(len(matching) <= 1, "Duplicate publication detected")
        prior_intents = []
        for page in range(1, 11):
            runs = github(
                repo
                + "/commits/"
                + candidate["head"]
                + f"/check-runs?check_name=Preloop%20review&filter=all&per_page=100&page={page}"
            )["check_runs"]
            prior_intents.extend(
                r
                for r in runs
                if r.get("external_id") == "preloop:" + candidate["execution_id"]
                and marker in (r.get("output", {}).get("text") or "")
            )
            if len(runs) < 100:
                break
        else:
            raise InvalidReviewError("Check history exceeds claim-reconciliation bound")
        require(
            matching or not prior_intents,
            "Prior publication intent has no receipt; reconcile before sending again",
        )
        current_pr(github(path), candidate, binding)
        if not matching:
            # Persist intent before transmission. An absent comment does not
            # prove a prior POST failed; ambiguous attempts are never replayed.
            github(
                repo + "/check-runs/" + str(check["id"]),
                "PATCH",
                {
                    "output": {
                        "title": "Publishing Preloop result",
                        "summary": "Publication intent recorded.",
                        "text": marker,
                    }
                },
            )
            intent_written = True
            current_pr(github(path), candidate, binding)
        posted = (
            matching[0]
            if matching
            else github(
                path + "/reviews",
                "POST",
                {"event": "COMMENT", "commit_id": candidate["head"], "body": text},
            )
        )
        proof = github(path + "/reviews/" + str(posted["id"]))
        require(
            proof.get("body") == text
            and proof.get("commit_id") == candidate["head"]
            and proof.get("user", {}).get("login") == "github-actions[bot]"
            and proof.get("state") == "COMMENTED"
            and proof.get("submitted_at"),
            "Comment readback mismatch",
        )
        current_pr(github(path), candidate, binding)
        conclusion = "success" if clean(candidate) else "failure"
        github(
            repo + "/check-runs/" + str(check["id"]),
            "PATCH",
            {
                "status": "completed",
                "conclusion": conclusion,
                "output": {
                    "title": "Published Preloop result",
                    "summary": proof["html_url"],
                    "text": marker,
                },
            },
        )
        return {
            "execution_id": candidate["execution_id"],
            "head_sha": candidate["head"],
            "review_url": proof["html_url"],
            "check_id": check["id"],
            "conclusion": conclusion,
        }
    except Exception:
        github(
            repo + "/check-runs/" + str(check["id"]),
            "PATCH",
            {
                "status": "completed",
                "conclusion": "failure",
                "output": {
                    "title": "Preloop publication failed",
                    "summary": "No validated publication receipt.",
                    "text": marker if intent_written else "",
                },
            },
        )
        raise


def verify_sources(github, binding, revision, paths):
    require(re.fullmatch("[0-9a-f]{40}", revision) is not None, "Invalid workflow revision")
    for path in paths:
        expected = binding["approved_files"].get(path)
        require(expected is not None, "Source not approved")
        source = github(
            "/repos/" + binding["repository"] + "/contents/" + path + "?ref=" + revision
        )
        require(source.get("encoding") == "base64", "Unsupported source representation")
        require(
            hashlib.sha256(base64.b64decode(source["content"])).hexdigest() == expected,
            "Trigger source differs from approved code",
        )


def receipt_from_zip(data):
    require(len(data) <= 65_536, "Trigger artifact too large")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(archive.namelist() == ["receipt.json"], "Unexpected trigger artifact files")
        require(archive.getinfo("receipt.json").file_size <= 4096, "Trigger receipt too large")
        receipt = json.loads(archive.read("receipt.json"))
    require(isinstance(receipt, dict), "Invalid trigger receipt")
    return receipt


def download_trigger_artifact(repository, artifact_id, github_token):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None

    require(type(artifact_id) is int and artifact_id > 0, "Invalid artifact ID")
    url = (
        "https://api.github.com/repos/"
        + repository
        + "/actions/artifacts/"
        + str(artifact_id)
        + "/zip"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + github_token,
            "Accept": "application/vnd.github+json",
        },
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as error:
        require(error.code == 302, "Artifact download failed")
        location = urllib.parse.urlsplit(error.headers.get("Location", ""))
        require(
            location.scheme == "https"
            and location.hostname
            and (
                location.hostname.endswith(".blob.core.windows.net")
                or location.hostname.endswith(".actions.githubusercontent.com")
                or location.hostname == "objects.githubusercontent.com"
            )
            and location.username is None
            and location.port in [None, 443],
            "Untrusted artifact download host",
        )
        # Never forward GitHub credentials to signed storage URLs or another redirect.
        response = opener.open(urllib.request.Request(location.geturl()), timeout=30)
    with response:
        data = response.read(65_537)
    return receipt_from_zip(data)


def trigger_workflow_sha(run, receipt, binding, head):
    if run["event"] == "pull_request_target":
        pulls = [
            p
            for p in run.get("pull_requests", [])
            if p.get("number") == receipt.get("pr_number")
            and p.get("head", {}).get("sha") == head
            and p.get("head", {}).get("repo", {}).get("id") == binding["repository_id"]
            and p.get("base", {}).get("repo", {}).get("id") == binding["repository_id"]
            and p.get("base", {}).get("ref") == binding["default_branch"]
        ]
        require(len(pulls) == 1 and run["head_sha"] == head, "Trigger PR provenance mismatch")
        workflow_sha = pulls[0]["base"]["sha"]
    else:
        require(run["event"] == "workflow_dispatch", "Unexpected trigger event")
        workflow_sha = run["head_sha"]
    require(
        re.fullmatch("[0-9a-f]{40}", workflow_sha) and receipt.get("workflow_sha") == workflow_sha,
        "Trigger workflow revision mismatch",
    )
    return workflow_sha


def load_trigger_receipt(github, binding, eid, head, github_token):
    path = "/repos/" + binding["repository"]
    name = "preloop-trigger-" + eid
    artifacts = github(path + "/actions/artifacts?name=" + name + "&per_page=100")
    require(artifacts["total_count"] <= 100, "Trigger artifact history exceeds bound")
    matches = []
    for artifact in artifacts["artifacts"]:
        if artifact.get("expired") or artifact.get("name") != name:
            continue
        run = github(path + "/actions/runs/" + str(artifact["workflow_run"]["id"]))
        require(
            run["event"] in ["pull_request_target", "workflow_dispatch"]
            and run["path"].split("@")[0] == ".github/workflows/preloop-review-trigger.yml"
            and run["status"] == "completed"
            and run["conclusion"] == "success",
            "Untrusted or incomplete trigger run",
        )
        receipt = download_trigger_artifact(binding["repository"], artifact["id"], github_token)
        workflow_sha = trigger_workflow_sha(run, receipt, binding, head)
        verify_sources(
            github,
            binding,
            workflow_sha,
            [
                ".github/preloop-publisher.py",
                ".github/preloop-trigger.py",
                ".github/workflows/preloop-review-trigger.yml",
            ],
        )
        require(
            receipt.get("execution_id") == eid
            and receipt.get("head_sha") == head
            and receipt.get("trigger_run_id") == str(run["id"]),
            "Trigger artifact binding mismatch",
        )
        matches.append(receipt)
    require(
        bool(matches) and all(x == matches[0] for x in matches),
        "Missing or conflicting trigger receipt",
    )
    return matches[0]


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    binding = load_authority(".github", repository)
    require(
        binding.get("publication_enabled") is True,
        "Publication requires final post-pilot hardware approval",
    )
    workload = verify_workload(binding, repository)
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        eid = execution_id(
            "https://preloop.ai/console/flows/executions/" + event["inputs"]["execution_id"]
        )
        event_sha = event["inputs"]["head_sha"]
    else:
        require(
            event["context"] == "preloop" and event["state"] != "pending",
            "Not a terminal Preloop status",
        )
        require(event["repository"]["id"] == binding["repository_id"], "Event repository mismatch")
        eid, event_sha = execution_id(event["target_url"]), event["sha"]
    require(re.fullmatch("[0-9a-f]{40}", event_sha), "Invalid event head")
    github_token = os.environ["GH_TOKEN"]

    def github(path, method="GET", payload=None):
        return request("https://api.github.com", path, github_token, method, payload)

    run_url = "https://github.com/" + repository + "/actions/runs/" + os.environ["GITHUB_RUN_ID"]
    check_path = "/repos/" + repository + "/check-runs"
    check = github(
        check_path,
        "POST",
        {
            "name": "Preloop review",
            "head_sha": event_sha,
            "status": "in_progress",
            "details_url": run_url,
            "external_id": "preloop:" + eid,
            "output": {
                "title": "Validating Preloop result",
                "summary": "Waiting for validated publication.",
            },
        },
    )
    try:
        source = github(
            "/repos/"
            + repository
            + "/contents/.github/workflows/preloop-review-publish.yml?ref="
            + workload["workflow_sha"]
        )
        require(
            hashlib.sha256(base64.b64decode(source["content"])).hexdigest()
            == binding["approved_workflow_sha256"],
            "Running workflow differs from signed source",
        )
        token = os.environ["PRELOOP_CI_TOKEN"]
        require(
            token.startswith("ci_"), "Only repository-bound read-only Preloop identity accepted"
        )
        detail = request("https://preloop.ai", "/api/v1/flows/executions/" + eid, token)
        artifact = (
            request("https://preloop.ai", "/api/v1/flows/executions/" + eid + "/result", token)
            if detail["status"] == "SUCCEEDED"
            else None
        )
        receipt = (
            load_trigger_receipt(github, binding, eid, event_sha, github_token)
            if "trigger_event_details" not in detail
            else None
        )
        candidate = validate(detail, artifact, binding, eid, event_sha, receipt)
        current_pr(
            github("/repos/" + repository + "/pulls/" + str(candidate["pr"])), candidate, binding
        )
        verify_diff(candidate, repository, github_token)
    except Exception:
        github(
            check_path + "/" + str(check["id"]),
            "PATCH",
            {
                "status": "completed",
                "conclusion": "failure",
                "output": {
                    "title": "Preloop validation failed",
                    "summary": "No validated review publication.",
                },
            },
        )
        raise
    receipt = publish(candidate, binding, github, run_url, check=check)
    Path(os.environ.get("PUBLICATION_RECEIPT", "publication-receipt.json")).write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt))
    return 0 if receipt["conclusion"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
