"""Start one principal-owned review from trusted GitHub Actions code."""
import importlib.util
import json
import os
import sys
import urllib.parse
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("publisher", ".github/preloop-publisher.py")
assert SPEC is not None
assert SPEC.loader is not None
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def select_owned_execution(rows, expected, execution_id=None):
    """Choose an explicitly named owned retry; never launch from an unknown ID."""
    owned = [row for row in rows if all(row.get(k) == v for k, v in expected.items())]
    if execution_id is not None:
        publisher.require(
            isinstance(execution_id, str)
            and publisher.re.fullmatch(
                "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", execution_id
            ),
            "Invalid selected execution ID",
        )
        matches = [row for row in owned if row.get("id") == execution_id]
        publisher.require(
            len(matches) == 1, "Selected execution is missing, duplicated or not owned"
        )
        return matches[0]
    publisher.require(
        len(owned) <= 1, "Ambiguous existing review; select the exact owned execution"
    )
    return owned[0] if owned else None


def prepare():
    repository = os.environ["GITHUB_REPOSITORY"]
    binding = publisher.load_authority(".github", repository)
    workload = publisher.verify_workload(binding, repository, workflow="preloop-review-trigger.yml")
    policy = binding.get("native_ci_contract") or {}
    publisher.require(
        policy.get("explicit_posture_approval") is True
        and policy.get("model_verification") == "approved_flow_configuration"
        and policy.get("model_id") == binding["model_id"]
        and publisher.re.fullmatch("[0-9a-f]{64}", policy.get("flow_config_sha256", "")),
        "Incomplete approved native CI contract",
    )
    token = os.environ["PRELOOP_CI_TRIGGER_TOKEN"]
    publisher.require(token.startswith("ci_"), "Only the bound CI trigger identity is accepted")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ["GITHUB_EVENT_NAME"] == "workflow_dispatch":
        number = int(event["inputs"]["pr_number"])
        execution_id = event["inputs"].get("execution_id") or None
    else:
        publisher.require(
            os.environ["GITHUB_EVENT_NAME"] == "pull_request_target", "Wrong trigger event"
        )
        number = event["number"]
        execution_id = None
    publisher.require(type(number) is int and number > 0, "Invalid PR number")
    github_token = os.environ["GH_TOKEN"]

    def github(path):
        return publisher.request("https://api.github.com", path, github_token)

    # Verify every executable file against this run's trusted default-branch revision.
    publisher.verify_sources(
        github,
        binding,
        workload["workflow_sha"],
        [
            ".github/preloop-publisher.py",
            ".github/preloop-trigger.py",
            ".github/workflows/preloop-review-trigger.yml",
        ],
    )
    pr = github("/repos/" + repository + "/pulls/" + str(number))
    publisher.require(pr["state"] == "open", "PR is closed")
    publisher.require(not pr.get("draft", True), "Draft PRs are not reviewed")
    publisher.require(
        pr.get("user", {}).get("login") != "dependabot[bot]", "Dependabot PRs are not reviewed"
    )
    publisher.require(
        "preloop-skip-review" not in [label["name"] for label in pr.get("labels", [])],
        "PR explicitly skips Preloop review",
    )
    publisher.require(
        pr.get("author_association") in ["OWNER", "MEMBER", "COLLABORATOR"],
        "PR author is not an admitted repository collaborator",
    )
    publisher.require(
        pr["base"]["repo"]["id"] == binding["repository_id"]
        and pr["head"]["repo"]["id"] == binding["repository_id"],
        "Repository changed or fork refused",
    )
    publisher.require(pr["base"]["ref"] == binding["default_branch"], "Wrong target branch")
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    expected = {
        "flow_id": binding["flow_id"],
        "project_id": binding["project_id"],
        "repository_identifier": str(binding["repository_id"]),
        "pr_number": number,
        "head_sha": head,
    }
    query = urllib.parse.urlencode({"flow_id": binding["flow_id"], "limit": 100})
    rows = publisher.request("https://preloop.ai", "/api/v1/flows/executions?" + query, token)
    publisher.require(isinstance(rows, list), "Invalid owned review history")
    selected = select_owned_execution(rows, expected, execution_id)
    intent = {
        **expected,
        "base_sha": base,
        "model_id": binding["model_id"],
        "flow_config_sha256": policy["flow_config_sha256"],
        "trigger_run_id": os.environ["GITHUB_RUN_ID"],
        "workflow_sha": workload["workflow_sha"],
        "existing_execution_id": selected["id"] if selected else None,
    }
    if selected is None:
        name = "preloop-intent-" + str(number) + "-" + head
        journal = github("/repos/" + repository + "/actions/artifacts?name=" + name + "&per_page=1")
        publisher.require(
            journal["total_count"] == 0,
            "A prior durable trigger intent exists; reconcile it before another paid attempt",
        )
    Path(os.environ["RUNNER_TEMP"], "preloop-trigger-intent.json").write_text(json.dumps(intent))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write("pr_number=" + str(number) + "\nhead_sha=" + head + "\n")
        output.write("needs_intent=" + ("false" if selected is not None else "true") + "\n")


def start():
    intent = json.loads(Path(os.environ["RUNNER_TEMP"], "preloop-trigger-intent.json").read_text())
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["PRELOOP_CI_TRIGGER_TOKEN"]
    publisher.require(token.startswith("ci_"), "Invalid native trigger credential")
    number, head, base = intent["pr_number"], intent["head_sha"], intent["base_sha"]

    def github(path):
        return publisher.request("https://api.github.com", path, os.environ["GH_TOKEN"])

    current = github("/repos/" + repository + "/pulls/" + str(number))
    publisher.require(
        current["state"] == "open"
        and current["head"]["sha"] == head
        and current["base"]["sha"] == base,
        "PR changed before trigger",
    )
    if intent["existing_execution_id"]:
        execution = publisher.request(
            "https://preloop.ai",
            "/api/v1/flows/executions/" + intent["existing_execution_id"],
            token,
        )
    else:
        name = "preloop-intent-" + str(number) + "-" + head
        journal = github(
            "/repos/" + repository + "/actions/artifacts?name=" + name + "&per_page=100"
        )
        publisher.require(
            journal["total_count"] == 1
            and str(journal["artifacts"][0]["workflow_run"]["id"]) == os.environ["GITHUB_RUN_ID"],
            "Durable intent not confirmed for this run",
        )
        # The persisted artifact blocks a later run after an ambiguous POST failure.
        execution = publisher.request(
            "https://preloop.ai",
            "/api/v1/flows/" + intent["flow_id"] + "/trigger",
            token,
            "POST",
            {"pr_number": number, "head_sha": head},
        )
    expected = {
        k: intent[k]
        for k in ["flow_id", "project_id", "repository_identifier", "pr_number", "head_sha"]
    }
    publisher.require(
        all(execution.get(k) == v for k, v in expected.items()), "Native execution binding mismatch"
    )
    eid = publisher.execution_id("https://preloop.ai/console/flows/executions/" + execution["id"])
    current = github("/repos/" + repository + "/pulls/" + str(number))
    publisher.require(
        current["head"]["sha"] == head and current["base"]["sha"] == base,
        "PR changed during trigger",
    )
    receipt = {k: v for k, v in intent.items() if k != "existing_execution_id"}
    receipt["execution_id"] = eid
    folder = Path(os.environ["RUNNER_TEMP"]) / "preloop-trigger-receipt"
    folder.mkdir()
    (folder / "receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write("execution_id=" + eid + "\n")
    print("Started principal-owned Preloop execution " + eid)


if __name__ == "__main__":
    {"--prepare": prepare, "--start": start}[sys.argv[1]]()
