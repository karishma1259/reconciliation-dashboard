# Decisions

### 1. No database-level foreign keys between System A and System B
**Decision:** `SystemBEntry.record_ref_raw` is a plain string, not a Django `ForeignKey` to `SystemARecord`.
**Alternative:** A real FK with `on_delete` handling.
**Reasoning:** The dataset deliberately contains refs that point at nothing. A DB-level FK would reject those rows at insert time, which is the "silently dropping rows" behavior the brief explicitly says not to do. Matching happens in application code instead, where an unmatched ref becomes data (an orphan discrepancy) rather than an import failure.

### 2. Values stored as raw strings, parsed defensively only at compare time
**Decision:** `value_raw` fields keep the original CSV text (`"N/A"`, `"$120.50"`, `""`) untouched. Parsing into a comparable number happens once, inside `comparator.py`.
**Alternative:** Cast to `Decimal`/`float` during import and store the parsed value.
**Reasoning:** Casting at import time forces a decision about what "invalid" means before we even know what we're using the number for. Keeping raw values means the importer can never fail on a bad number, and the comparator (the one place that actually needs a numeric value) owns the definition of "unparseable."

### 3. One normalization function for both sides
**Decision:** `normalize_reference()` is applied identically to System A's `record_id` and System B's `record_ref`, collapsing `REC-001` / `rec_001` / `001` / `REC001` to the same key.
**Alternative:** Write separate cleanup logic per system, since they're formatted differently.
**Reasoning:** If the two sides used different normalization rules, a bug in either one would silently break matching for that side only, and it'd be much harder to reason about from the outside. One shared function means there's exactly one place to check when a match doesn't happen.

### 4. Both-sides-blank is not a VALUE_MISMATCH
**Decision:** If both System A and System B have an unparseable/blank value for a record, that record produces no discrepancy at all.
**Alternative:** Flag it as a mismatch since the values aren't equal, or flag it as its own new discrepancy category.
**Reasoning:** The brief calls out "the non-error is correctly identified as a non-error" as something being graded. Two blanks agreeing that there's no value isn't a disagreement between the systems, so it shouldn't produce a row demanding a human's attention. A blank vs. a real number is still a mismatch — only both-blank is treated as non-comparable.

### 5. Malformed rows are logged to `ImportIssue`, not dropped
**Decision:** Every row the importer can't fully make sense of (missing `location_id` reference, missing `entry_id`, empty `record_ref`) is still inserted with whatever fields could be recovered, plus a row in `ImportIssue` explaining what was off.
**Alternative:** Skip and log to console/stdout only.
**Reasoning:** A console log disappears after the run. A queryable table lets anyone (including the evaluator) verify "nothing was silently dropped" is actually true, instead of taking it on faith.

### 6. Discrepancies computed in Python, cached per-process, not stored in the DB
**Decision:** `reconcile_from_db()` runs the comparison on demand and results are cached in a module-level dict for the life of the process.
**Alternative:** Persist a `Discrepancy` table and recompute on every import.
**Reasoning:** At 120 rows per side, recomputing is effectively free, and not persisting means there's no risk of a stale discrepancy record surviving a re-import. The obvious cost — cache never invalidates without a process restart — is fine for a take-home and called out explicitly as a "second day" fix, not hidden.

### 7. Tenant scoping enforced by rejecting requests with no `org_id`, not by session/auth
**Decision:** `DiscrepancyListView` returns HTTP 400 if `org_id` is absent, and never has a code path that returns rows for more than one org in a single response.
**Alternative:** Build real auth and derive the tenant from a logged-in session.
**Reasoning:** The brief explicitly waives authentication. But it does *not* waive tenant isolation, so the isolation still has to be real at the query layer — it just can't rely on a session to prove who's asking. A production version would swap "trust the query param" for "derive org_id from the authenticated user," without changing the filtering logic itself.

### 8. Sample data was generated, not provided
**Decision:** Since the actual `system_a.csv` / `system_b.csv` / `locations.csv` were not available, a generator script (`data/generate_sample_data.py`) produces 120-row datasets with the same deliberate mess the brief describes (ref format variants, blanks, orphans, duplicates, value drift).
**Alternative:** Wait for the real files, or build against a minimal hand-written fixture.
**Reasoning:** A generator seeded deterministically (`random.seed(42)`) gives reproducible, realistically dirty data to build and test against, and documents exactly what kinds of mess the importer is expected to survive. If the real CSVs use different column names, only `import_data.py`'s field lookups need to change — the model and comparator design don't assume anything the brief didn't specify.
