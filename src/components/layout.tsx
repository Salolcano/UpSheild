import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useWallet } from "./wallet-provider";
import { CONTRACT, EXPLORER, hasInjected } from "@/lib/genlayer";
import { KEYS, store } from "@/lib/storage";

function WalletMenu() {
  const w = useWallet();
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const addr = w.signer?.address;
  const guard = (fn: () => void | Promise<void>) => async () => {
    try { await fn(); setMsg(""); } catch (e: any) { setMsg(e?.message ?? String(e)); }
  };
  return (
    <div className="rel">
      <button className="btn" onClick={() => setOpen(!open)}>{addr ? addr.slice(0, 6) + "..." + addr.slice(-4) : "Connect wallet"}</button>
      {open && (
        <div className="dd">
          {!addr && <>
            <button onClick={guard(() => { w.useLocalWallet(); setOpen(false); })}>Browser wallet (generated for you)</button>
            <button disabled={!hasInjected()} onClick={guard(async () => { await w.connectExternal(); setOpen(false); })}>
              {hasInjected() ? "Injected wallet (MetaMask etc.)" : "Injected wallet (none found)"}</button>
            <button onClick={guard(() => { const k = prompt("Paste a private key (0x...)"); if (k) { w.importKey(k); setOpen(false); } })}>Import a private key</button>
          </>}
          {addr && <>
            <small>{addr}</small>
            {w.signer?.kind === "local" && <>
              <button onClick={guard(async () => { await w.fund(); setMsg("Funded from the Studio faucet."); })}>Get test GEN (Studio faucet)</button>
              <button onClick={guard(() => { const k = w.exportKey(); if (k) prompt("Your private key. Keep it secret:", k); })}>Export private key</button>
            </>}
            <button onClick={() => { w.disconnect(); setOpen(false); }}>Disconnect</button>
          </>}
          {msg && <small>{msg}</small>}
        </div>
      )}
    </div>
  );
}

/** React Router does not scroll to #sections by itself, so the nav links need this. */
function ScrollToHash() {
  const { hash, pathname, key } = useLocation();
  useEffect(() => {
    if (!hash) { window.scrollTo(0, 0); return; }
    const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    return () => clearTimeout(t);
  }, [hash, pathname, key]);
  return null;
}

export default function Layout() {
  const toggle = () => {
    const r = document.documentElement;
    const next = getComputedStyle(r).colorScheme === "light" ? "dark" : "light";
    r.setAttribute("data-theme", next);
    store.set(KEYS.theme, next);
  };
  return (
    <>
      <nav><div className="wrap">
        <Link className="logo" to="/"><i></i>UpShield</Link>
        <div className="links">
          <Link to="/#providers">Providers</Link><Link to="/#cover">Get cover</Link><Link to="/policies">Ledger</Link><Link to="/#how">How it works</Link>
        </div>
        <div className="sp"></div>
        <button className="btn ghost icon" onClick={toggle} aria-label="Toggle theme">&#9680;</button>
        <WalletMenu />
      </div></nav>
      <ScrollToHash />
      <Outlet />
      <footer><div className="wrap">
        <span>&copy; 2026 UpShield &middot; GenLayer Studio Next</span>
        <span>Contract: {CONTRACT ? <a href={`${EXPLORER}address/${CONTRACT}`} target="_blank" rel="noreferrer">{CONTRACT.slice(0, 10)}...</a> : "not set"}</span>
      </div></footer>
    </>
  );
}
