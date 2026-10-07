import { Link, useLoaderData } from "react-router-dom";
import { QuoteAndBuy, FundPool } from "@/components/write-actions";
import { NAMES, PROVIDERS, TAGS, fromWei } from "@/lib/format";
import type { Summary } from "@/lib/genlayer";

export default function Home() {
  const s = useLoaderData() as Summary;
  return (
    <>
      <header className="hero" id="top"><div className="wrap">
        <span className="pill">Built on GenLayer &middot; Studio Next</span>
        <h1>Outage cover, <em>settled by consensus.</em></h1>
        <p className="sub">Insure your business against a GitHub, Cloudflare, Discord or Vercel outage. Validators price the risk and judge the claim from real status-page evidence. No adjuster.</p>
        <div className="cta"><a className="btn" href="#cover">Request a quote</a><Link className="btn ghost" to="/policies">View the ledger</Link></div>
        <div className="stats">
          <div className="stat"><b>{fromWei(s.pool_balance)}</b><span>Pool balance (GEN)</span></div>
          <div className="stat"><b>{fromWei(s.outstanding_liability)}</b><span>Open liability (GEN)</span></div>
          <div className="stat"><b>{s.policy_count}</b><span>Policies</span></div>
          <div className="stat"><b>{s.quote_count}</b><span>Quotes priced</span></div>
        </div>
      </div></header>

      <section id="how"><div className="wrap">
        <div className="eyebrow">How it works</div><h2>Three steps, settled by consensus</h2>
        <div className="grid">
          <div className="card"><div className="num">1</div><h3>Request a quote</h3><p>Pick a provider (GitHub, Cloudflare, Discord or Vercel), how long an outage must last, a coverage window and a payout. Validators read the provider's public incident history and rate the risk LOW, MODERATE or HIGH. Coverage must start at least 30 minutes from now.</p></div>
          <div className="card"><div className="num">2</div><h3>Buy cover</h3><p>The contract works out the premium from the risk rating. You pay exactly that amount into the shared pool, from the same wallet that requested the quote, within 60 minutes and before coverage starts.</p></div>
          <div className="card"><div className="num">3</div><h3>Check claim</h3><p>When the window closes, anyone can run the check. Validators compare the official status page with an independent source and agree on the longest outage in minutes. If it meets your threshold, the pool pays you automatically. If not, the policy is declined.</p></div>
        </div>
        <p className="info" style={{ marginTop: 16 }}>The model never decides a payout. It only reports minutes. The contract compares that number with your threshold, and only that comparison moves money.</p>
      </div></section>

      <section id="providers"><div className="wrap">
        <div className="eyebrow">Providers</div><h2>Cover what you depend on</h2>
        <div className="grid">
          {PROVIDERS.map((p) => (
            <div className="card" key={p}>
              <div className="ph">{NAMES[p].slice(0, 2)}</div><h3>{NAMES[p]}</h3>
              <p>Cover against a long outage of {NAMES[p]}.</p>
              <div className="tags"><span className="tag">{TAGS[p]}</span><span className="tag">Statuspage</span></div>
              <a className="btn ghost" href="#cover">Get cover</a>
            </div>
          ))}
        </div>
      </div></section>

      <section id="cover"><div className="wrap split">
        <div>
          <div className="eyebrow">Get cover</div>
          <div className="big">Price it. Buy it. Claim it.</div>
          <ul className="list">
            <li>The premium is derived by the contract from the risk band, never chosen by the buyer.</li>
            <li>Two sources are reconciled, the official status page and an independent one.</li>
            <li>The model's wording can never trigger a payout. Only the stored threshold does.</li>
          </ul>
        </div>
        <div><QuoteAndBuy /><FundPool /></div>
      </div></section>
    </>
  );
}
