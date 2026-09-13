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

I used Claude to scaffold the Django models, the importer, the comparator, and the React frontend from the brief. I went through the code afterward to understand it section by section — the models, the normalization logic, the four-pass comparator, the API's tenant scoping — rather than just accepting it as-is, since I knew I'd need to defend it on a call. I ran the test suite and exercised the API and UI directly (filtering by reason, switching tenants, sorting by value) to check the behavior matched what was claimed, rather than trusting the code from reading it alone.

## Answers

**a. Name one thing the AI agent got wrong. How did you notice?**
The sort-by-value feature didn't originally account for orphan records having no System A value (an orphan only exists in System B, so there's nothing on the A side to show). I noticed this by filtering the table down to just ORPHAN_IN_SYSTEM_B and trying "Sort by value" — since orphans have no System A value, I wanted to confirm the sort was actually using their System B value rather than defaulting to zero or breaking. Testing it directly (rather than trusting the code from reading it) confirmed the fallback in the sort key correctly reads System B's value when System A's is missing.

**b. Which part of your submission are you least confident about, and why?**
The per-process cache in `views.py`: discrepancies are computed once and cached for the life of the server process. If you re-import data while the server is still running, the API keeps serving the old results until the server is restarted. I haven't tested that specific scenario end-to-end, so I'm not fully sure how it would surface to a user in practice.

**c. If you had a second day, what would you fix first?**
I'd fix the cache invalidation issue above first, since it's the kind of bug that fails silently — someone re-imports data, sees no change, and might assume the import didn't work rather than realizing the cache is stale.