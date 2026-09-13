export default function DiscrepancyTable({ rows }) {
  if (rows.length === 0) {
    return <p>No discrepancies for this filter.</p>;
  }

  return (
    <table border="1" cellPadding="8" style={{ borderCollapse: "collapse", width: "100%" }}>
      <thead>
        <tr>
          <th>Reason</th>
          <th>Record</th>
          <th>Location</th>
          <th>Org</th>
          <th>System A value</th>
          <th>System B value</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, idx) => (
          <tr key={`${row.record_id}-${idx}`}>
            <td>{row.reason}</td>
            <td>{row.record_id}</td>
            <td>{row.location_id || "—"}</td>
            <td>{row.org_id}</td>
            <td>{row.value_a ?? "—"}</td>
            <td>{row.value_b ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
