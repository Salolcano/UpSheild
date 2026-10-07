import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { EXPLORER, txFailed, txStatus } from "@/lib/genlayer";

const OK = ["ACCEPTED", "FINALIZED"];
const RETRY = ["UNDETERMINED", "VALIDATORS_TIMEOUT", "LEADER_TIMEOUT"];
const FAIL = ["CANCELED", "REVERTED"];

type Tx = { label: string; stage: string; hash?: string; error?: string; done?: boolean };
type Ctx = { track: (label: string, send: () => Promise<string>) => Promise<boolean> };
const TxCtx = createContext<Ctx | null>(null);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function TransactionProvider({ children }: { children: ReactNode }) {
  const [tx, setTx] = useState<Tx | null>(null);

  const track = useCallback(async (label: string, send: () => Promise<string>) => {
    setTx({ label, stage: "SIGNING" });
    try {
      const hash = await send();
      setTx({ label, stage: "PENDING", hash });
      for (let i = 0; i < 300; i++) {
        await sleep(3000);
        let stage = "PENDING";
        try { stage = await txStatus(hash); } catch { /* keep polling */ }
        setTx({ label, stage, hash });
        if (OK.includes(stage)) {
          const failed = await txFailed(hash).catch(() => false);
          if (failed) { setTx({ label, stage, hash, done: true, error: "Validators agreed, but the contract refused this call (a rule was not met). Open the explorer for the reason." }); return false; }
          setTx({ label, stage, hash, done: true });
          return true;
        }
        if (RETRY.includes(stage)) { setTx({ label, stage, hash, done: true, error: "Validators could not agree. This is retryable: submit again." }); return false; }
        if (FAIL.includes(stage)) { setTx({ label, stage, hash, done: true, error: "The transaction failed." }); return false; }
      }
      setTx({ label, stage: "TIMEOUT", hash, done: true, error: "Still pending after 15 minutes. Check the explorer." });
      return false;
    } catch (e: any) {
      setTx({ label, stage: "ERROR", done: true, error: e?.shortMessage ?? e?.message ?? String(e) });
      return false;
    }
  }, []);

  const value = useMemo(() => ({ track }), [track]);
  return (
    <TxCtx.Provider value={value}>
      {children}
      {tx && (
        <div className="txbar" role="status">
          {tx.done && <button onClick={() => setTx(null)} aria-label="Dismiss">&times;</button>}
          <b>{tx.label}</b> &middot; {tx.stage}
          {!tx.done && <span> (validators are working, this can take a minute)</span>}
          {tx.error && <div style={{ color: "var(--muted)", marginTop: 6 }}>{tx.error}</div>}
          {tx.hash && <div style={{ marginTop: 6, fontSize: 12, wordBreak: "break-all" }}>
            <a href={`${EXPLORER}transactions/${tx.hash}`} target="_blank" rel="noreferrer" style={{ color: "var(--accent2)" }}>{tx.hash}</a></div>}
        </div>
      )}
    </TxCtx.Provider>
  );
}

export function useTx(): Ctx {
  const c = useContext(TxCtx);
  if (!c) throw new Error("useTx must be used inside TransactionProvider");
  return c;
}
