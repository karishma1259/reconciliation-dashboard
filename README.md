# Reconciliation Dashboard

Finds where System A and System B disagree about the same events, scoped per tenant.

## How to run

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py import_data          # loads data/*.csv into the DB
python manage.py runserver 8000
```

### Tests
```bash
cd backend
python -m pytest reconciler/tests/test_comparator.py -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173
```
Backend must be running on `:8000` first — the frontend talks to `http://localhost:8000/api`.

### Regenerating sample data
`data/generate_sample_data.py` produces `system_a.csv` / `system_b.csv` / `locations.csv` with the mess described in the brief (ref format variants, blanks, orphans, duplicates, value drift), seeded deterministically. Re-run it and re-import if you want a fresh dataset with the same characteristics.

> **Note on the data:** the real `system_a.csv` / `system_b.csv` / `locations.csv` referenced in the brief weren't available when this was built, so this generator stands in for them. The importer reads column names (`record_id`, `record_ref`, `location_id`, `org_id`, `value`, etc.) exactly as the brief specifies them; if the real files use different headers, only `import_data.py` needs adjusting.

## What I built

- **Importer** (`import_data.py`): loads all three CSVs, never rejects a row outright except one with no identifier at all — even then it's logged, not silently discarded. Every row it can't fully interpret is recorded in an `ImportIssue` table with a reason, so "nothing was silently dropped" is checkable, not just claimed.
- **Reference normalization**: one function (`normalize_reference`) used identically on both `record_id` and `record_ref`, collapsing `REC-001` / `rec_001` / `001` / `REC001` / padded whitespace to the same key.
- **Comparator** (`comparator.py`): pure Python, no DB calls, four passes covering the four required discrepancy types, plus explicit handling for "both sides blank" so that doesn't get flagged as a false mismatch.
- **API**: `GET /api/discrepancies/?org_id=...&reason=...&sort=...` — rejects requests with no `org_id` (400), and there's no code path that returns more than one tenant's rows in one response. `GET /api/orgs/` lists tenants for the selector.
- **Frontend**: tenant dropdown, reason filter, value sort, plain HTML table. No styling effort spent beyond readability.
- **Tests**: 9 tests against the pure comparator — one per required discrepancy type, plus non-error handling, reference-format matching, and org resolution.

## What I deliberately did not build

- **Authentication** — waived explicitly by the brief.
- **CSS / visual design** — plain table, as instructed.
- **Pagination** — 120 rows fits on one screen.
- **Persisted discrepancy table / cache invalidation on re-import** — discrepancies are recomputed in memory and cached per-process; a second import while the server is running won't be picked up without a restart. Documented in DECISIONS.md, not hidden.
- **Real numeric parsing of dates** — dates are stored and displayed as raw strings; no date comparison logic, since the brief's four required cases are all about identity and value, not date.

## How I worked with the agent

[**You'll need to fill this in honestly based on what actually happened in your session** — this section, and the three answers below, are the part of the submission with the most weight (20%) precisely because they can't be faked convincingly on a follow-up call. A rough shape to work from:]

I used [tool] to scaffold the Django models, importer, comparator, and React frontend from the brief. I drove the design decisions myself — particularly the "no DB-level FK between the two systems" call, and treating both-sides-blank as a non-error — and had the agent implement them, checking each piece by running the actual test suite and hitting the API with curl rather than trusting the code by inspection. [Add anything you changed, rejected, or had to fix yourself.]

## Answers

**a. Name one thing the AI agent got wrong. How did you notice?**
[Answer this from something that actually happened while you built/reviewed this. One real candidate from this codebase, if you want to use it and can genuinely defend it: the first version of the sort key in `views.py` didn't handle rows where `value_a` is `None` (orphans have no System A value) — sorting by value would have thrown or silently used `0` for every orphan, burying them at one end regardless of their actual System B value. Caught by testing sort against a filtered orphan-only view and seeing them all pinned to the top. Replace this with your own if you found something else while reviewing.]

**b. Which part of your submission are you least confident about, and why?**
[Answer honestly. A defensible real candidate: the per-process cache in `views.py` — it's correct for a single import-then-serve run, but re-importing while the server is up won't invalidate it, and that's the kind of bug that's easy to not notice until someone reports "I re-imported and nothing changed."]

**c. If you had a second day, what would you fix first?**
[Your call — cache invalidation, date-based discrepancy checks, or handling the real CSVs once they're available are all legitimate answers given what's in DECISIONS.md.]
