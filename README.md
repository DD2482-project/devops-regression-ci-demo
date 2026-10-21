# devops-regression-ci-demo

A tiny FastAPI "order total" service used to demo automated regression testing with CI quality gates (KTH DevOps course).

## Install

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Test

```bash
pytest                 # unit + integration
pytest --cov=app       # with line coverage on app/
```

## Run

```bash
uvicorn app.main:app --reload
# POST /orders/total  {"items": [{"price": 100.0, "quantity": 1}], "discount_code": "SAVE10"}
```

## CI and Jules auto-fix demo

1. Configure the repository secret `JULES_API_KEY` and give Jules access to this repository.
2. Open a PR from `jules-sandbox` to `main`, then push a failing change under `scratch/`. CI runs the full pytest suite on the PR and reports a red `tests` check.
3. The failed PR CI run starts the Jules workflow. Jules tests and fixes the sandbox code on a new branch and automatically opens a PR back to `jules-sandbox`.
4. CI runs again on Jules's PR. A developer reviews its diff and green `tests` check, then approves and merges it. CI reruns on the original PR after its branch is updated.
5. Review the original PR's green check before merging it to `main`.

In GitHub **Settings → Branches**, protect `main`: require a pull request, the `tests` status check, and one approving review. These are repository settings; the workflow file alone does not block a red PR or enforce approval. Jules's fix PR may be a draft and must be marked ready for review before merging. The auto-fix trigger is deliberately limited to the same-repository `jules-sandbox` PR and changes under `scratch/`; it does not run on the intentional discount regression branch. The mutation job is informational in `main`'s CI.

## Layout

| Path | What |
| --- | --- |
| `app/pricing.py` | Pure pricing functions (subtotal, discount, order total). |
| `app/main.py` | FastAPI app exposing `POST /orders/total`. |
| `tests/unit/` | Fast checks on the pure functions. |
| `tests/integration/` | End-to-end checks through the HTTP app. |
| `docs/regression.md` | The intentional regression used in the demo. |
| `docs/demo-script.md` | Speaker notes. |

## Proposal

Course proposal PR: https://github.com/KTH/devops-course/pull/2964
