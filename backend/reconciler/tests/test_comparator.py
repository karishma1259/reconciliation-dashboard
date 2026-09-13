"""
Pure-function tests against reconcile() -- no DB, no fixtures, no
pytest-django dependency for these. They run in milliseconds, which is
what lets us test the part that actually matters (the decision logic)
without paying for a database round trip per test.
"""
from reconciler.services.comparator import (
    reconcile,
    REASON_MISSING,
    REASON_ORPHAN,
    REASON_DUPLICATE,
    REASON_VALUE_MISMATCH,
)

LOC_MAP = {"LOC-1": "ORG-1", "LOC-2": "ORG-2"}


def test_detects_record_missing_in_system_b():
    records_a = [{"record_id": "REC-01", "location_id": "LOC-1", "value_raw": "100.00"}]
    entries_b = []

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert len(result) == 1
    assert result[0].reason == REASON_MISSING
    assert result[0].record_id == "REC-01"
    assert result[0].org_id == "ORG-1"


def test_detects_orphan_record_in_system_b():
    records_a = []
    entries_b = [{"entry_id": "E1", "record_ref_raw": "REC-999", "location_id": "LOC-1", "value_raw": "250"}]

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert len(result) == 1
    assert result[0].reason == REASON_ORPHAN
    assert result[0].record_id == "REC-999"


def test_detects_duplicate_entries_in_system_b():
    records_a = [{"record_id": "REC-01", "location_id": "LOC-1", "value_raw": "100.00"}]
    # Two B entries for the same record, written in different ref formats --
    # this is exactly the kind of mess normalize_reference exists to catch.
    entries_b = [
        {"entry_id": "E1", "record_ref_raw": "REC-01", "location_id": "LOC-1", "value_raw": "100.00"},
        {"entry_id": "E2", "record_ref_raw": " rec_01 ", "location_id": "LOC-1", "value_raw": "100.00"},
    ]

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert len(result) == 1
    assert result[0].reason == REASON_DUPLICATE


def test_detects_value_mismatch():
    records_a = [{"record_id": "REC-01", "location_id": "LOC-1", "value_raw": "100.00"}]
    entries_b = [{"entry_id": "E1", "record_ref_raw": "REC-01", "location_id": "LOC-1", "value_raw": "$120.00"}]

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert len(result) == 1
    assert result[0].reason == REASON_VALUE_MISMATCH
    assert result[0].value_a == "100.00"
    assert result[0].value_b == "$120.00"


def test_matching_record_produces_no_discrepancy():
    """The non-error case: values agree once currency formatting is stripped."""
    records_a = [{"record_id": "REC-01", "location_id": "LOC-1", "value_raw": "100.00"}]
    entries_b = [{"entry_id": "E1", "record_ref_raw": "REC001", "location_id": "LOC-1", "value_raw": "$100.00"}]

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert result == []


def test_both_sides_blank_is_not_a_mismatch():
    """
    A record where neither system recorded a usable value shouldn't be
    reported as a VALUE_MISMATCH -- there's nothing to compare, so it's
    correctly treated as a non-error, per the brief's "handling the mess"
    criterion.
    """
    records_a = [{"record_id": "REC-01", "location_id": "LOC-1", "value_raw": "N/A"}]
    entries_b = [{"entry_id": "E1", "record_ref_raw": "REC-01", "location_id": "LOC-1", "value_raw": ""}]

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert result == []


def test_reference_format_variants_all_match():
    """REC-001, rec_001, 001, REC001 must all resolve to the same record."""
    records_a = [{"record_id": "REC-001", "location_id": "LOC-1", "value_raw": "50.00"}]
    for variant in ["REC-001", "rec_001", "001", "REC001", " REC-001 "]:
        entries_b = [{"entry_id": "E1", "record_ref_raw": variant, "location_id": "LOC-1", "value_raw": "50.00"}]
        result = reconcile(records_a, entries_b, LOC_MAP)
        assert result == [], f"variant '{variant}' failed to match"


def test_tenant_org_resolution_from_location():
    """org_id is derived from location_id via the locations map, not hardcoded."""
    records_a = [{"record_id": "REC-01", "location_id": "LOC-2", "value_raw": "10"}]
    entries_b = []

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert result[0].org_id == "ORG-2"


def test_unknown_location_does_not_crash():
    """A location_id not present in locations.csv resolves to UNKNOWN, not an exception."""
    records_a = [{"record_id": "REC-01", "location_id": "LOC-999", "value_raw": "10"}]
    entries_b = []

    result = reconcile(records_a, entries_b, LOC_MAP)

    assert result[0].org_id == "UNKNOWN"
