import { useState } from "react";
import { useRevalidator } from "react-router-dom";
import { useWallet } from "./wallet-provider";
import { useTx } from "./transaction-provider";
import * as gl from "@/lib/genlayer";
import { NAMES, PROVIDERS, fromWei, toWei, type Quote } from "@/lib/format";

/** Every condition the contract would reject is checked here first, so a doomed request is never sent. */
export function preflightQuoteError(minutes: number, payout: string, start: string, end: string): string | null {
  if (!Number.isFinite(minutes) || minutes < 5) return "The outage threshold must be at least 5 minutes.";
  if (!/^\d+(\.\d+)?$/.test(payout.trim()) || toWei(payout) <= 0n) return "Enter a payout greater than 0.";
  if (!start || !end) return "Choose a coverage start and end.";
  if (new Date(end) <= new Date(start)) return "Coverage must end after it starts.";
  if (new Date(start).getTime() < Date.now() + 40 * 60 * 1000) return "Start coverage at least 40 minutes from now. The contract needs 30 minutes of lead time, plus a margin for the quote to confirm.";
  const hours = (new Date(end).getTime() - new Date(start).getTime()) / 3600000;
  if (hours < 1 || hours > 30 * 24) return "Coverage must last between 1 hour and 30 days.";
  return null;
}

/** The contract only accepts canonical UTC: YYYY-MM-DDTHH:MM:SSZ (no milliseconds, no offsets). */
const iso = (v: string) => new Date(v).toISOString().replace(/\.\d{3}Z$/, "Z");

export function QuoteAndBuy({ initialProvider = "github" }: { initialProvider?: string }) {
  const { signer } = useWallet();
  const { track } = useTx();
  const rev = useRevalidator();
  const [provider, setProvider] = useState(initialProvider);
  const [minutes, setMinutes] = useState("60");
  const [payout, setPayout] = useState("10");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [note, setNote] = useState("");
  const [bought, setBought] = useState("");

  const requestQuote = async () => {
    if (!signer) return setNote("Connect a wallet first.");
    const err = preflightQuoteError(Number(minutes), payout, start, end);
    if (err) return setNote(err);
    setNote(""); setQuote(null); setBought("");
    const before = (await gl.getSummary()).quote_count;
    const ok = await track("Request quote", () => gl.sendQuote(signer, provider, Number(minutes), iso(start), iso(end), toWei(payout)));
    if (!ok) return;
    const q = await gl.findNewQuote(before, signer.address, provider, Number(minutes));
    if (!q) return setNote("Quote finished but was not found. Open the Ledger and try again.");
    setQuote(q); rev.revalidate();
  };

  const buy = async () => {
    if (!signer || !quote) return;
    if (Date.now() / 1000 > quote.valid_until) return setNote("This quote has expired. Request a new one.");
    if (signer.address.toLowerCase() !== quote.requester.toLowerCase()) return setNote("Only the wallet that requested this quote can buy it.");
    const ok = await track("Buy cover", () => gl.sendBuy(signer, quote.id, quote.required_premium));
    if (ok) { setBought(quote.id); setQuote(null); rev.revalidate(); setNote("Policy created. Open the Ledger to see it."); }
  };

  return (
    <div className="widget">
      <label>Provider</label>
      <select value={provider} onChange={(e) => setProvider(e.target.value)}>
        {PROVIDERS.map((p) => <option key={p} value={p}>{NAMES[p]}</option>)}
      </select>
      <div className="row">
        <div><label>Outage threshold (minutes)</label><input type="number" min="5" value={minutes} onChange={(e) => setMinutes(e.target.value)} /></div>
        <div><label>Payout (GEN)</label><input value={payout} onChange={(e) => setPayout(e.target.value)} /></div>
      </div>
      <div className="row">
        <div><label>Coverage start</label><input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} /></div>
        <div><label>Coverage end</label><input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
      </div>
      <button className="btn" onClick={requestQuote}>Step 1: Request quote</button>

      {quote && (
        <div className="msg">
          <b>{quote.id}</b> &middot; risk band <b>{quote.risk_band}</b><br />
          {quote.risk_band === "UNPRICEABLE"
            ? "The history was too thin to price this honestly. Try another provider or threshold."
            : <>Premium to pay: <b>{fromWei(quote.required_premium)} GEN</b> for a payout of {fromWei(quote.requested_payout)} GEN.</>}
          <div className="info">{quote.rationale}</div>
          <div className="info">Buy within 60 minutes of the quote (until {new Date(quote.valid_until * 1000).toLocaleTimeString()}), and before coverage starts, from the same wallet that requested it.</div>
          {quote.risk_band !== "UNPRICEABLE" && <button className="btn" onClick={buy}>Step 2: Buy cover for exactly {fromWei(quote.required_premium)} GEN</button>}
        </div>
      )}
      {bought && <div className="info">Bought from {bought}.</div>}
      {note && <div className="msg">{note}</div>}
      {!gl.CONTRACT && <div className="msg">Contract address is not set. Add VITE_UPSHIELD_CONTRACT.</div>}
    </div>
  );
}

export function FundPool() {
  const { signer } = useWallet();
  const { track } = useTx();
  const rev = useRevalidator();
  const [amount, setAmount] = useState("100");
  return (
    <div className="widget" style={{ marginTop: 16 }}>
      <label>Fund the shared pool (GEN)</label>
      <input value={amount} onChange={(e) => setAmount(e.target.value)} />
      <button className="btn ghost" onClick={async () => {
        if (!signer) return;
        if (await track("Fund pool", () => gl.sendFund(signer, toWei(amount)))) rev.revalidate();
      }}>Fund pool</button>
      <div className="info">A policy can never exceed 20% of the pool, so an empty pool cannot back any cover.</div>
    </div>
  );
}

export function CheckClaimButton({ policyId }: { policyId: string }) {
  const { signer } = useWallet();
  const { track } = useTx();
  const rev = useRevalidator();
  return (
    <button className="btn" onClick={async () => {
      if (!signer) return;
      if (await track("Check claim", () => gl.sendClaim(signer, policyId))) rev.revalidate();
    }}>Check claim</button>
  );
}
