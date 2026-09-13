const REASONS = [
  { value: "ALL", label: "All reasons" },
  { value: "MISSING_IN_SYSTEM_B", label: "Missing in B" },
  { value: "ORPHAN_IN_SYSTEM_B", label: "Orphan in B" },
  { value: "DUPLICATE_IN_SYSTEM_B", label: "Duplicate in B" },
  { value: "VALUE_MISMATCH", label: "Value mismatch" },
];

export default function FilterBar({ orgs, org, setOrg, reason, setReason, sort, setSort }) {
  return (
    <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", alignItems: "center" }}>
      <label>
        Tenant:{" "}
        <select value={org} onChange={(e) => setOrg(e.target.value)}>
          {orgs.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </label>

      <label>
        Reason:{" "}
        <select value={reason} onChange={(e) => setReason(e.target.value)}>
          {REASONS.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </label>

      <label>
        Sort by value:{" "}
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="">None</option>
          <option value="value_asc">Ascending</option>
          <option value="value_desc">Descending</option>
        </select>
      </label>
    </div>
  );
}
