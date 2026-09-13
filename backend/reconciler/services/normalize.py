import re
from decimal import Decimal, InvalidOperation

_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]")
_LEADING_ZEROS = re.compile(r"^0+(?=\d)")

NULL_TOKENS = {"", "N/A", "NA", "NULL", "NONE", "-", "--"}


def normalize_reference(value: str) -> str:
    """
    Collapses 'REC-001', ' rec_001 ', '001', 'REC001' all down to the same
    canonical key ('1'), so record_id (System A) and record_ref (System B)
    can be matched regardless of which of the observed formats was used.

    Applied identically to both System A's record_id and System B's
    record_ref, so the matching is symmetric -- there's exactly one
    normalization function, not one per side.
    """
    if not value:
        return ""
    cleaned = _NON_ALNUM.sub("", value).lower()
    if cleaned.startswith("rec"):
        cleaned = cleaned[3:]
    cleaned = _LEADING_ZEROS.sub("", cleaned)
    return cleaned


def safe_parse_value(value: str):
    """
    Parses a value field that may be '', 'N/A', '$1,780.53', '231.55', etc.
    Returns a Decimal for anything that looks numeric once currency
    formatting is stripped, or None for anything that doesn't (blank,
    N/A, free text). None is treated as "no comparable number", not as
    zero -- two blanks are not a mismatch, but a blank vs. a real number
    should be caught by VALUE_MISMATCH, so callers distinguish that case
    explicitly rather than relying on None == None.
    """
    if value is None:
        return None
    stripped = value.strip()
    if stripped.upper() in NULL_TOKENS:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", stripped)
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
