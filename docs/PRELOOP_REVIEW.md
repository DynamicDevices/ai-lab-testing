# Preloop PR review

This bootstrap reuses DynamicDevices' existing shared PR and security-review
flow. It does not create another flow, change branch protection or authorise a
merge. Alex reviews and merges the bootstrap before the new trusted workflows
can review another PR.

## What runs

An eligible same-repository PR starts a default-branch controller. The controller
verifies the signed service policy and GitHub workload identity, records a durable
trigger intent, then starts one project-bound review. It never runs PR code with
review credentials. Drafts, Dependabot, `preloop-skip-review`, forks and unadmitted
authors are refused, including on manual dispatch.

A terminal Preloop GitHub status wakes the default-branch publisher. The status
is not a verdict. The publisher fetches the authoritative execution/result and
checks the repository, head, base, complete canonical diff, owned controller
receipt and signed source manifest. It publishes readable findings and a genuine
Actions-backed `Preloop review` check, then reads back the publication. Failed,
stale, ambiguous or incomplete results cannot become a passing review.

Both jobs require the current signed policy from repository secrets. There is no
committed policy fallback. Removing the policy secrets prevents either job from
using an older checked-in grant. The public signing key is pinned independently.

The integration source was adapted from
`GenMinds-UK/innovateher-lms-work@4c66924dee4ad37e74a084366c35dc8865da9d18`.
The native API omits per-result model identity. The separately signed service
policy explicitly accepts a fixed model and approved flow-configuration digest;
it does not claim stronger runtime model proof. The setup policy and initial CI
keys expire on 19 November 2026 at 16:45:53 GMT. Nothing renews them automatically.

## Custody and permissions

The trigger and result-reader keys are separately scoped to repository
1097600942, project `66a561b2-a557-4002-a94b-bdc01c906a4e` and the existing DD flow
`d644eec6-dd20-4346-8ac9-069968a15117`. Both keys belong to one stable project
principal because the API restricts execution reads to the starting principal.
The result-reader key cannot trigger reviews. Neither key grants source pushes
or merges. GitHub publication uses only
the publisher job's repository-scoped Actions token.

Provider-issued credentials are captured in dedicated Bitwarden Secrets Manager
items before installation as `PRELOOP_REVIEW_TRIGGER_TOKEN` and
`PRELOOP_PUBLICATION_READ_TOKEN`. The exact signed policy and detached signature
are installed as `PRELOOP_PUBLICATION_AUTHORITY` and
`PRELOOP_PUBLICATION_SIGNATURE`. No credential values belong in source or logs.

## Validation and operation

Offline regressions run in the `Preloop integration tests` workflow and locally:

```sh
python3 -m unittest discover -s .github -p 'test_preloop*.py' -v
```

After Alex merges the bootstrap, open the separate badge/hook PR. If an explicit
initial dispatch is necessary, use the trusted default branch:

```sh
gh workflow run preloop-review-trigger.yml --repo DynamicDevices/ai-lab-testing \
  --ref main -f pr_number=OPEN_PR_NUMBER
```

There must be one trigger owner, one bounded startup validation, and event-driven
completion rather than polling. A prior durable intent after an ambiguous launch
must be reconciled; it must not be bypassed by another paid attempt. After a
Preloop failure, preserve it and follow the authorised manual-review procedure,
not an automatic retry loop. Never post a manually green replacement status.

Offline tests and successful provisioning do not establish live acceptance.
Acceptance requires a real eligible PR, native clone/exact checkout and runner
deadline evidence, the complete exact-head result, readable findings/no-findings
publication and independently verified Actions check. Any required specialist
security review remains a separate gate. Alex alone merges development PRs.

Assisted-by: Briar.
