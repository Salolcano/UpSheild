import { Link, useLoaderData } from "react-router-dom";
import { CheckClaimButton } from "@/components/write-actions";
import { formatThreshold, fromWei, type Policy } from "@/lib/format";

export default function PolicyPage() {
  const p = useLoaderData() as Policy | null;
  if (!p) return <section><div className="wrap"><h2>Policy not found</h2><Link to="/policies" className="btn ghost">Back to the Ledger</Link></div></section>;
  return (
    <section><div className="wrap">
      <div className="eyebrow">Policy</div><h2>{p.id} <span className="st">{p.status}</span></h2>
      <div className="widget" style={{ maxWidth: 720 }}>
        <dl className="kv">
          <dt>Condition</dt><dd>{formatThreshold(p.provider, p.threshold_minutes)}</dd>
          <dt>Coverage window</dt><dd>{p.coverage_start} to {p.coverage_end}</dd>
          <dt>Premium paid</dt><dd>{fromWei(p.premium)} GEN</dd>
          <dt>Payout</dt><dd>{fromWei(p.payout_amount)} GEN</dd>
          <dt>Holder</dt><dd>{p.holder}</dd>
          <dt>From quote</dt><dd>{p.quote_id}</dd>
          <dt>Resolved outage</dt><dd>{p.status === "ACTIVE" ? "Not settled yet" : `${p.resolved_outage_minutes} minutes`}</dd>
          <dt>Evidence note</dt><dd>{p.evidence_note || "None yet"}</dd>
        </dl>
        {p.status === "ACTIVE" && (Date.now() / 1000 >= p.end_ts
          ? <><CheckClaimButton policyId={p.id} /><div className="info">The window has closed. Anyone can run this check.</div></>
          : <div className="info">Claims open when the coverage window closes ({p.coverage_end}). The contract refuses a claim check before then.</div>)}
      </div>
    </div></section>
  );
}
