import { Link, useLoaderData } from "react-router-dom";
import { NAMES, fromWei, type Policy } from "@/lib/format";

export default function Policies() {
  const rows = useLoaderData() as Policy[];
  return (
    <section><div className="wrap">
      <div className="eyebrow">The Ledger</div><h2>Every policy, public</h2>
      <p className="sub" style={{ margin: "0 0 20px" }}>No wallet needed to read it.</p>
      <div className="scroll"><table>
        <thead><tr><th>Policy</th><th>Provider</th><th>Threshold</th><th>Payout (GEN)</th><th>Status</th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={5} style={{ color: "var(--muted)" }}>No policies yet.</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/policy/${r.id}`} style={{ color: "var(--accent2)" }}>{r.id}</Link></td>
              <td>{NAMES[r.provider] ?? r.provider}</td><td>{r.threshold_minutes} min</td>
              <td>{fromWei(r.payout_amount)}</td><td><span className="st">{r.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div></section>
  );
}
