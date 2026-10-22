# DevOps regression CI demo

A small FastAPI order-total service for demonstrating how tests, GitHub Actions,
branch rules, mutation testing, and an AI fix proposal work together. The demo
has two examples:

1. An intentional discount bug makes a pull request's tests fail. When `tests`
   is required by the `main` ruleset, that check keeps the change out of
   `main` until a developer fixes it.
2. A failing pull request from `jules-sandbox` starts Jules. Jules proposes a fix
   on a separate branch and opens a pull request. CI tests that proposal, and a
   developer reviews and decides whether to merge it.

The AI workflow is limited to the sandbox example. It does not automatically
fix the discount regression or merge any pull request.

## Run the service locally

Use Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

In another terminal, send an order:

```bash
curl -sS -X POST http://127.0.0.1:8000/orders/total \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"price":100,"quantity":1},{"price":50,"quantity":1}],"discount_code":"SAVE10"}'
```

The response is `{"subtotal":150.0,"discount":15.0,"total":135.0}`. `SAVE10`
and `SAVE20` discount the **whole order subtotal** by 10% and 20%, respectively.
Unknown or absent codes give no discount. Pricing uses `Decimal` and rounds money
to cents before the API returns JSON numbers.

## Tests and CI

Run the full suite, or reproduce the CI test command:

```bash
pytest -q
pytest --cov=app --cov-report=term-missing --cov-fail-under=90
```

`tests/unit/` checks the pricing functions directly. `tests/integration/`
checks request handling, pricing, and JSON output through the FastAPI endpoint.
The `tests` CI job runs both groups and fails if a test fails or coverage of
`app/` falls below 90%.

The [CI workflow](.github/workflows/ci.yml) runs on every pull request and on
pushes to `main`. Pushing to a feature branch without an open pull request does
not start this workflow. It has two jobs:

| Job/check name | What it does | Result used for |
| --- | --- | --- |
| `tests` | Installs dependencies, runs all pytest tests, and enforces at least 90% line coverage of `app/`. | The regression gate; configure this exact check as required in the `main` ruleset. |
| `mutation` | Runs `mutmut` against `app/pricing.py` with the unit tests and lists surviving mutants. | Feedback about test strength. The current workflow ignores the mutation run's exit status and has no mutation score threshold. |

Line coverage shows that code ran; it cannot show that every behavior was
asserted. Surviving mutants identify changes the tests did not catch. The
mutation results are useful for improving tests, but the current `mutation`
job is informational rather than a mutation quality gate.

To inspect mutants locally, use the same pinned version and runner as CI:

```bash
pip install mutmut==2.4.4
mutmut run --paths-to-mutate app/pricing.py --runner "python -m pytest -x -q tests/unit"
mutmut results
```

GitHub branch rules enforce merging restrictions; a workflow file alone does
not block a red pull request. For `main`, require a pull request and the actual
`tests` check name in the ruleset's required status checks. The ruleset can
allow zero required approvals if review should remain optional. Requiring a
human approval is a separate settings choice. Requiring `mutation` as a status
check would only require that job to finish successfully; it would **not**
reject surviving mutants with the current workflow.

## Demonstrate the discount regression

1. Start from `main`: the multi-item discount tests expect a 150.00 subtotal,
   15.00 discount, and 135.00 total for a `SAVE10` order.
2. On `regression/discount-bug`, change `order_total` so it calculates the
   discount from the first item's unit price instead of the subtotal. The
   [regression notes](docs/regression.md) show the code change and expected
   failing tests.
3. Open or update a pull request from that branch to `main`. The multi-item
   unit tests and the end-to-end API test fail in the `tests` job. A one-item
   test still passes, showing why the broader cases matter.
4. Restore the subtotal calculation in a fix pull request targeting the
   regression branch. Its checks turn green. Updating the regression branch
   causes its pull request to `main` to run CI again.

This is a deliberately broken branch for the demo. Leave its pull request
unmerged while showing the red required check and blocked merge.

## Demonstrate the Jules fix proposal

The [Jules workflow](.github/workflows/jules-autofix.yml) listens for a
completed `CI` run. Its job starts only when all of these are true:

- The CI run failed on a pull request.
- The pull request's head branch is `jules-sandbox` in this repository, not a
  fork.
- It is the first attempt of that CI run.

Set up the remote demo:

1. Give Jules access to this GitHub repository and add its API key as the
   repository Actions secret `JULES_API_KEY`.
2. Open a pull request from `jules-sandbox` to `main`. The `scratch/` example
   lives on that branch; it is not part of `main`.
3. Push a failing change under `scratch/` to `jules-sandbox`. The open pull
   request triggers `CI`, which runs the full test suite and reports the
   failure.
4. The failed run starts `Jules auto-fix (sandbox only)`. The workflow gives
   Jules the failed run URL and commit SHA, asks it to run pytest and inspect
   the failure, and restricts the requested edit to `scratch/`.
5. Jules creates a new branch and a pull request back to `jules-sandbox`. The
   workflow waits for that pull request URL and reports it in its job summary.
   Jules's new pull request triggers `CI` again; the Jules trigger skips it
   because its head branch is different.
6. A developer inspects the diff and CI result. If the fix is acceptable,
   mark the Jules pull request ready for review if it is a draft, then merge
   it into `jules-sandbox`. This updates the original pull request and runs
   its CI checks again. Merge to `main` only after that pull request is green.

The workflow uses Jules's `AUTO_CREATE_PR` mode, but neither Jules nor the
workflow merges the fix. A green check is evidence that these tests passed;
the developer still has to judge whether the proposed code is correct.
For an existing example, see the [failing sandbox pull request](https://github.com/DD2482-project/devops-regression-ci-demo/pull/6)
and a [Jules fix pull request](https://github.com/DD2482-project/devops-regression-ci-demo/pull/9).

## Why this setup, and its limits

- Unit tests give fast feedback on the pricing rule; integration tests catch
  mistakes at the HTTP boundary. The same suite runs locally and in CI.
- GitHub Actions runs checks where pull requests are reviewed. Configuring
  `tests` as a required check in the `main` ruleset turns its result into a
  merge condition.
- Mutation testing exposes weak assertions even when coverage is high. Its
  output is currently advisory, so surviving mutants do not fail CI.
- The Jules workflow shows a possible recovery step after CI failure while
  keeping a human in control of the proposed patch. It only handles the
  `jules-sandbox` pull request and asks Jules to edit `scratch/`; it is not a
  general automatic repair system.
- A failing CI run can also come from coverage, dependencies, or runner
  problems. Jules may be unable to find a code fix, may time out, or may
  propose an incorrect one. Flaky tests can also block a good pull request.
  This project demonstrates validation and review, not deployment.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/pricing.py` | Subtotal, discount, and order-total calculations. |
| `app/main.py` | FastAPI `POST /orders/total` endpoint. |
| `tests/unit/` | Direct pricing tests. |
| `tests/integration/` | HTTP endpoint tests. |
| `.github/workflows/ci.yml` | Tests, coverage gate, and mutation report. |
| `.github/workflows/jules-autofix.yml` | Sandbox-only Jules trigger and fix PR handoff. |
| `docs/regression.md` | Intentional discount bug and expected failing tests. |
| `docs/demo-script.md` | Demo speaker notes. |

[Course proposal](https://github.com/KTH/devops-course/pull/2964)
