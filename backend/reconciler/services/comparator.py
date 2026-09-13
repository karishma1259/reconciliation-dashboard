"""
The comparison engine. Deliberately kept as plain Python operating on
dicts, with zero Django ORM calls -- that's what lets test_comparator.py
run against in-memory fixtures instead of a real database, which is what
the brief asks for ("tests that run fast, use in-memory data").

Four passes, matching the brief's four required cases exactly:
  1. MISSING_IN_SYSTEM_B  - A record exists, no B entry references it
  2. ORPHAN_IN_SYSTEM_B   - B entry references a record_id that doesn't exist
  3. DUPLICATE_IN_SYSTEM_B - two or more B entries reference the same record
  4. VALUE_MISMATCH       - exactly one B entry matches, but values differ
"""
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional

from reconciler.services.normalize import normalize_reference, safe_parse_value

REASON_MISSING = "MISSING_IN_SYSTEM_B"
REASON_ORPHAN = "ORPHAN_IN_SYSTEM_B"
REASON_DUPLICATE = "DUPLICATE_IN_SYSTEM_B"
REASON_VALUE_MISMATCH = "VALUE_MISMATCH"


@dataclass
class Discrepancy:
    reason: str
    record_id: str          # record_id if known, else the raw record_ref (orphans)
    location_id: str
    org_id: str
    value_a: Optional[str]  # raw string as originally recorded, for display
    value_b: Optional[str]

    def as_dict(self):
        return asdict(self)


def _resolve_org(location_id: str, location_org_map: dict) -> str:
    return location_org_map.get(location_id, "UNKNOWN")


def reconcile(records_a: list[dict], entries_b: list[dict], location_org_map: dict) -> list[Discrepancy]:
    """
    records_a: list of {record_id, location_id, value_raw}
    entries_b: list of {entry_id, record_ref_raw, location_id, value_raw}
               (record_ref_normalized is (re)computed here so callers can
               pass raw CSV-shaped dicts directly, e.g. in tests)
    location_org_map: {location_id: org_id}, from locations.csv
    """
    discrepancies: list[Discrepancy] = []

    # Group B entries by normalized record_ref.
    b_by_ref = defaultdict(list)
    for b in entries_b:
        norm = normalize_reference(b.get("record_ref_raw", b.get("record_ref", "")))
        b_by_ref[norm].append(b)

    a_by_norm_id = {}
    for a in records_a:
        norm = normalize_reference(a["record_id"])
        a_by_norm_id[norm] = a

    matched_norms = set()

    # Pass over A: MISSING and VALUE_MISMATCH cases live here, DUPLICATE
    # is detected here too since it's keyed off how many B entries a given
    # A record has.
    for a in records_a:
        norm = normalize_reference(a["record_id"])
        org_id = _resolve_org(a.get("location_id", ""), location_org_map)
        b_matches = b_by_ref.get(norm, [])

        if not b_matches:
            discrepancies.append(Discrepancy(
                reason=REASON_MISSING,
                record_id=a["record_id"],
                location_id=a.get("location_id", ""),
                org_id=org_id,
                value_a=a.get("value_raw") or None,
                value_b=None,
            ))
            continue

        matched_norms.add(norm)

        if len(b_matches) > 1:
            discrepancies.append(Discrepancy(
                reason=REASON_DUPLICATE,
                record_id=a["record_id"],
                location_id=a.get("location_id", ""),
                org_id=org_id,
                value_a=a.get("value_raw") or None,
                value_b="; ".join((b.get("value_raw") or "—") for b in b_matches),
            ))
            continue

        # Exactly one match: compare values.
        b = b_matches[0]
        val_a = safe_parse_value(a.get("value_raw"))
        val_b = safe_parse_value(b.get("value_raw"))

        # Both unparseable/blank -> nothing to compare, not treated as a
        # mismatch (this is the "non-error correctly identified as
        # non-error" case the brief calls out).
        if val_a is None and val_b is None:
            continue

        if val_a != val_b:
            discrepancies.append(Discrepancy(
                reason=REASON_VALUE_MISMATCH,
                record_id=a["record_id"],
                location_id=a.get("location_id", ""),
                org_id=org_id,
                value_a=a.get("value_raw") or None,
                value_b=b.get("value_raw") or None,
            ))

    # Pass over B: anything whose normalized ref never matched an A record,
    # and isn't blank, is an orphan.
    for norm, b_matches in b_by_ref.items():
        if norm and norm not in a_by_norm_id:
            for b in b_matches:
                org_id = _resolve_org(b.get("location_id", ""), location_org_map)
                discrepancies.append(Discrepancy(
                    reason=REASON_ORPHAN,
                    record_id=b.get("record_ref_raw", b.get("record_ref", "")),
                    location_id=b.get("location_id", ""),
                    org_id=org_id,
                    value_a=None,
                    value_b=b.get("value_raw") or None,
                ))

    return discrepancies


def reconcile_from_db():
    """Thin adapter: pulls rows from the DB, hands them to the pure reconcile()."""
    from reconciler.models import SystemARecord, SystemBEntry, Location

    location_org_map = dict(Location.objects.values_list("location_id", "org_id"))

    records_a = list(SystemARecord.objects.values("record_id", "location_id", "value_raw"))
    entries_b = list(
        SystemBEntry.objects.values("entry_id", "record_ref_raw", "location_id", "value_raw")
    )
    return reconcile(records_a, entries_b, location_org_map)
