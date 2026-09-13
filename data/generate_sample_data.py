"""
Generates sample data since we don't have the real CSVs from the assignment.
Deliberately injects the exact kinds of mess the brief describes:
- record_ref written 3+ different ways (REC-001, rec_001, 001, REC001)
- blank fields, unparseable numbers ("N/A", "$120.50", "")
- an entry pointing at a record that doesn't exist (orphan)
- a record entered twice in system B (duplicate)
- records with no system B entry at all (missing)
- value mismatches between the two systems
- multiple tenants (orgs) via locations.csv, so isolation can be tested
"""
import csv
import random

random.seed(42)

ORGS = ["ORG-1", "ORG-2", "ORG-3"]
LOCATIONS_PER_ORG = 4
NUM_RECORDS = 120

# ---- 1. locations.csv : every location belongs to exactly one org ----
locations = []
loc_id = 1
for org in ORGS:
    for _ in range(LOCATIONS_PER_ORG):
        locations.append({
            "location_id": f"LOC-{loc_id:03d}",
            "org_id": org,
            "name": f"{org} Site {loc_id}",
        })
        loc_id += 1

with open("/home/claude/reconciliation-engine/data/locations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["location_id", "org_id", "name"])
    w.writeheader()
    w.writerows(locations)

# ---- 2. system_a.csv : the source of truth for what SHOULD exist ----
event_types = ["PAYMENT", "REFUND", "ADJUSTMENT", "TRANSFER"]
records_a = []
for i in range(1, NUM_RECORDS + 1):
    rid = f"REC-{i:03d}"
    loc = random.choice(locations)
    value = round(random.uniform(10, 2000), 2)
    records_a.append({
        "record_id": rid,
        "location_id": loc["location_id"],
        "event_type": random.choice(event_types),
        "value": f"{value:.2f}",
        "event_date": "2025-0" + str(random.randint(1, 6)) + "-" + f"{random.randint(1,28):02d}",
    })

# sprinkle a few dirty rows directly into system A too (blank value, weird location)
records_a[5]["value"] = ""                     # blank value
records_a[12]["value"] = "N/A"                  # unparseable
records_a[20]["location_id"] = "LOC-999"        # location that doesn't exist in locations.csv

with open("/home/claude/reconciliation-engine/data/system_a.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["record_id", "location_id", "event_type", "value", "event_date"])
    w.writeheader()
    w.writerows(records_a)

# ---- 3. system_b.csv : independently recorded, messier ref formatting ----
def ref_variant(rid: str, style: int) -> str:
    num = rid.split("-")[1]
    return {
        0: rid,                     # "REC-045"
        1: rid.lower().replace("-", "_"),   # "rec_045"
        2: num,                     # "045"
        3: rid.replace("-", ""),    # "REC045"
        4: f" {rid} ",              # padded whitespace
    }[style]

records_b = []
entry_num = 1

# Decide which A records get which treatment:
# - indices 0..99  -> normal 1:1 match (with some value drift)
# - 100..109       -> MISSING_IN_SYSTEM_B (no entry created)
# - 110..114       -> DUPLICATE_IN_SYSTEM_B (two entries for same record_ref)
# 5 extra entries will be ORPHAN_IN_SYSTEM_B (ref points nowhere)

for idx, rec in enumerate(records_a):
    rid = rec["record_id"]
    loc_id = rec["location_id"]
    base_val = rec["value"]

    if 100 <= idx <= 109:
        continue  # MISSING_IN_SYSTEM_B: System A has it, System B never got it

    style = random.randint(0, 4)
    ref = ref_variant(rid, style)

    # value mismatch for a deliberate subset
    try:
        num_val = float(base_val)
        if idx % 13 == 0 and base_val not in ("", "N/A"):
            num_val = round(num_val + random.choice([5, -5, 0.5, 10]), 2)
        val_str = f"${num_val:,.2f}"
    except ValueError:
        val_str = base_val  # keep as-is if source was already blank/N/A

    records_b.append({
        "entry_id": f"ENT-{entry_num:03d}",
        "record_ref": ref,
        "location_id": loc_id,
        "value": val_str,
        "entry_date": rec["event_date"],
    })
    entry_num += 1

    if 110 <= idx <= 114:
        # DUPLICATE_IN_SYSTEM_B: add a second entry, different ref style, maybe different value
        dup_style = random.choice([s for s in range(5) if s != style])
        records_b.append({
            "entry_id": f"ENT-{entry_num:03d}",
            "record_ref": ref_variant(rid, dup_style),
            "location_id": loc_id,
            "value": val_str,
            "entry_date": rec["event_date"],
        })
        entry_num += 1

# ORPHAN_IN_SYSTEM_B: entries whose record_ref matches no System A record at all
for fake_num in [501, 502, 503, "NULL", ""]:
    records_b.append({
        "entry_id": f"ENT-{entry_num:03d}",
        "record_ref": f"REC-{fake_num}" if fake_num not in ("NULL", "") else fake_num,
        "location_id": random.choice(locations)["location_id"],
        "value": f"{round(random.uniform(10, 500), 2):.2f}",
        "entry_date": "2025-04-01",
    })
    entry_num += 1

random.shuffle(records_b)

with open("/home/claude/reconciliation-engine/data/system_b.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["entry_id", "record_ref", "location_id", "value", "entry_date"])
    w.writeheader()
    w.writerows(records_b)

print(f"locations: {len(locations)}")
print(f"system_a rows: {len(records_a)}")
print(f"system_b rows: {len(records_b)}")
