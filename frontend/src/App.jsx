import { useEffect, useState } from "react";
import FilterBar from "./components/FilterBar.jsx";
import DiscrepancyTable from "./components/DiscrepancyTable.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export default function App() {
  const [orgs, setOrgs] = useState([]);
  const [org, setOrg] = useState("");
  const [reason, setReason] = useState("ALL");
  const [sort, setSort] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load the list of tenants once, on mount.
  useEffect(() => {
    fetch(`${API_BASE}/orgs/`)
      .then((r) => r.json())
      .then((data) => {
        setOrgs(data.orgs);
        if (data.orgs.length > 0) setOrg(data.orgs[0]);
      })
      .catch(() => setError("Could not reach the backend. Is it running on :8000?"));
  }, []);

  // Re-fetch discrepancies whenever the tenant, reason filter, or sort changes.
  // org_id is always sent -- the backend rejects requests without it, so
  // there is no code path here that can accidentally request cross-tenant data.
  useEffect(() => {
    if (!org) return;
    setLoading(true);
    const params = new URLSearchParams({ org_id: org, reason, ...(sort ? { sort } : {}) });
    fetch(`${API_BASE}/discrepancies/?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setRows(data.results || []);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load discrepancies.");
        setLoading(false);
      });
  }, [org, reason, sort]);

  return (
    <div style={{ fontFamily: "sans-serif", padding: "2rem", maxWidth: "1000px", margin: "0 auto" }}>
      <h1>Reconciliation Discrepancies</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {orgs.length > 0 && (
        <FilterBar
          orgs={orgs}
          org={org}
          setOrg={setOrg}
          reason={reason}
          setReason={setReason}
          sort={sort}
          setSort={setSort}
        />
      )}
      {loading ? <p>Loading…</p> : <DiscrepancyTable rows={rows} />}
    </div>
  );
}
