from django.db import models


class Location(models.Model):
    """
    Every location belongs to exactly one org (tenant).
    This is the ONLY place the location -> org mapping exists,
    so every other table hangs its tenant scoping off of this one.
    """
    location_id = models.CharField(max_length=64, primary_key=True)
    org_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    """
    One row per event as System A recorded it.
    record_id is the identifier System B tries to reference.

    Design choice: location is a plain string FK-by-value (not a Django
    ForeignKey) on purpose. system_a.csv had a row pointing at a location_id
    that doesn't exist in locations.csv. A real ForeignKey would reject that
    row at import time -- which is exactly the "silently dropping rows"
    behaviour the brief tells us not to do. We store the raw location_id and
    resolve org_id defensively at query/compare time, tagging it UNKNOWN if
    it doesn't resolve.
    """
    record_id = models.CharField(max_length=64, primary_key=True)
    location_id = models.CharField(max_length=64, blank=True)
    event_type = models.CharField(max_length=64, blank=True)

    # Raw value exactly as it appeared in the CSV ("", "N/A", "231.55" ...).
    # We never cast this at import time -- casting happens defensively,
    # once, inside the comparator, where we control exactly what "invalid"
    # means for comparison purposes.
    value_raw = models.CharField(max_length=64, blank=True)
    event_date_raw = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [models.Index(fields=["location_id"])]


class SystemBEntry(models.Model):
    """
    One row per entry as System B recorded it. There can be more than one
    entry per record_ref (that's the duplicate case we need to catch), and
    record_ref may point at a record_id that doesn't exist in System A at
    all (the orphan case). So record_ref is NOT a ForeignKey to
    SystemARecord -- it's a raw string, matched at compare time via a
    normalized key.
    """
    entry_id = models.CharField(max_length=64, primary_key=True)
    record_ref_raw = models.CharField(max_length=64, blank=True)
    record_ref_normalized = models.CharField(max_length=64, blank=True, db_index=True)
    location_id = models.CharField(max_length=64, blank=True)
    value_raw = models.CharField(max_length=64, blank=True)
    entry_date_raw = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [models.Index(fields=["record_ref_normalized"])]


class ImportIssue(models.Model):
    """
    Every row we couldn't cleanly interpret gets logged here instead of
    being dropped -- this is how we prove "nothing is silently dropped"
    to the reader, without them having to trust us.
    """
    source_file = models.CharField(max_length=32)   # system_a / system_b / locations
    row_number = models.IntegerField()
    issue = models.CharField(max_length=255)
    raw_row = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
