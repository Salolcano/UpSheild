import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { generatePrivateKey } from "viem/accounts";
import { connectInjected, fundStudioAccount, injectedSigner, localSigner, type Signer } from "@/lib/genlayer";
import { KEYS, store } from "@/lib/storage";

type Ctx = {
  signer: Signer | null;
  useLocalWallet: () => void;
  connectExternal: () => Promise<void>;
  exportKey: () => string | null;
  importKey: (pk: string) => void;
  fund: () => Promise<void>;
  disconnect: () => void;
};
const WalletCtx = createContext<Ctx | null>(null);

const isKey = (s: string): s is `0x${string}` => /^0x[0-9a-fA-F]{64}$/.test(s);

function initial(): Signer | null {
  const key = store.get(KEYS.localKey);
  return store.get(KEYS.mode) === "local" && key && isKey(key) ? localSigner(key) : null;
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const [signer, setSigner] = useState<Signer | null>(initial);

  const useLocalWallet = useCallback(() => {
    const saved = store.get(KEYS.localKey);
    const key: `0x${string}` = saved && isKey(saved) ? saved : generatePrivateKey();
    store.set(KEYS.localKey, key);
    store.set(KEYS.mode, "local");
    setSigner(localSigner(key));
  }, []);

  const connectExternal = useCallback(async () => {
    const addr = await connectInjected();
    store.set(KEYS.mode, "injected");
    setSigner(injectedSigner(addr));
  }, []);

  const importKey = useCallback((pk: string) => {
    const k = pk.trim();
    if (!isKey(k)) throw new Error("A private key is 0x followed by 64 hex characters.");
    store.set(KEYS.localKey, k); store.set(KEYS.mode, "local"); setSigner(localSigner(k));
  }, []);

  const value = useMemo<Ctx>(() => ({
    signer, useLocalWallet, connectExternal, importKey,
    exportKey: () => (signer?.kind === "local" ? store.get(KEYS.localKey) : null),
    fund: async () => { if (signer) await fundStudioAccount(signer.address); },
    disconnect: () => { store.del(KEYS.mode); setSigner(null); },
  }), [signer, useLocalWallet, connectExternal, importKey]);

  return <WalletCtx.Provider value={value}>{children}</WalletCtx.Provider>;
}

export function useWallet(): Ctx {
  const c = useContext(WalletCtx);
  if (!c) throw new Error("useWallet must be used inside WalletProvider");
  return c;
}
