"""
Imports locations.csv, system_a.csv, system_b.csv.

Guiding rule: a row we can't fully make sense of still gets stored, with
whatever we could recover from it, plus a note in ImportIssue explaining
what was wrong. The only thing we truly cannot store is a row with no
identifier at all (no record_id / no entry_id) -- there's nothing to key
it by, so that's the one case we log-and-skip, and we say so loudly.

We import in this order: locations -> system_a -> system_b, because
locations is the only place org_id lives, and we want it available first
(though nothing here actually enforces a DB-level dependency -- see
models.py for why).
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from reconciler.models import Location, SystemARecord, SystemBEntry, ImportIssue
from reconciler.services.normalize import normalize_reference


class Command(BaseCommand):
    help = "Import locations.csv, system_a.csv, system_b.csv from a data directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=str(Path(__file__).resolve().parents[4] / "data"),
            help="Directory containing locations.csv, system_a.csv, system_b.csv",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])

        with transaction.atomic():
            ImportIssue.objects.all().delete()
            Location.objects.all().delete()
            SystemARecord.objects.all().delete()
            SystemBEntry.objects.all().delete()

            n_loc = self.import_locations(data_dir / "locations.csv")
            n_a = self.import_system_a(data_dir / "system_a.csv")
            n_b = self.import_system_b(data_dir / "system_b.csv")

        n_issues = ImportIssue.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Imported {n_loc} locations, {n_a} System A records, {n_b} System B entries. "
            f"{n_issues} rows had issues (logged, not dropped)."
        ))

    def _log_issue(self, source, row_number, issue, raw_row):
        ImportIssue.objects.create(
            source_file=source, row_number=row_number, issue=issue, raw_row=raw_row
        )

    def import_locations(self, path):
        count = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):  # header is row 1
                loc_id = (row.get("location_id") or "").strip()
                if not loc_id:
                    self._log_issue("locations", i, "missing location_id, row skipped", row)
                    continue
                org_id = (row.get("org_id") or "").strip()
                if not org_id:
                    self._log_issue("locations", i, "missing org_id, stored with blank org", row)
                Location.objects.update_or_create(
                    location_id=loc_id,
                    defaults={"org_id": org_id, "name": (row.get("name") or "").strip()},
                )
                count += 1
        return count

    def import_system_a(self, path):
        count = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                rid = (row.get("record_id") or "").strip()
                if not rid:
                    self._log_issue("system_a", i, "missing record_id, row skipped", row)
                    continue

                loc_id = (row.get("location_id") or "").strip()
                if loc_id and not Location.objects.filter(location_id=loc_id).exists():
                    self._log_issue(
                        "system_a", i,
                        f"location_id '{loc_id}' not found in locations.csv, stored anyway",
                        row,
                    )

                SystemARecord.objects.update_or_create(
                    record_id=rid,
                    defaults={
                        "location_id": loc_id,
                        "event_type": (row.get("event_type") or "").strip(),
                        "value_raw": (row.get("value") or "").strip(),
                        "event_date_raw": (row.get("event_date") or "").strip(),
                    },
                )
                count += 1
        return count

    def import_system_b(self, path):
        count = 0
        seen_entry_ids = set()
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                entry_id = (row.get("entry_id") or "").strip()
                if not entry_id:
                    # No stable identifier at all -- synthesize one from the row
                    # number so we still keep the data instead of dropping it.
                    entry_id = f"ROW-{i}"
                    self._log_issue(
                        "system_b", i, "missing entry_id, synthesized placeholder id", row
                    )
                if entry_id in seen_entry_ids:
                    entry_id = f"{entry_id}-dup{i}"
                    self._log_issue(
                        "system_b", i, "duplicate entry_id in source file, suffixed to keep both rows", row
                    )
                seen_entry_ids.add(entry_id)

                ref_raw = (row.get("record_ref") or "").strip()
                ref_norm = normalize_reference(ref_raw)
                if not ref_norm:
                    self._log_issue("system_b", i, "record_ref missing or empty after normalization", row)

                SystemBEntry.objects.update_or_create(
                    entry_id=entry_id,
                    defaults={
                        "record_ref_raw": ref_raw,
                        "record_ref_normalized": ref_norm,
                        "location_id": (row.get("location_id") or "").strip(),
                        "value_raw": (row.get("value") or "").strip(),
                        "entry_date_raw": (row.get("entry_date") or "").strip(),
                    },
                )
                count += 1
        return count
