import { createClient, createAccount } from "genlayer-js";
import * as chains from "genlayer-js/chains";
import { parsePolicy, parseQuote, type Policy, type Quote } from "./format";

export const RPC: string = import.meta.env.VITE_GENLAYER_RPC ?? "https://studio-next.genlayer.com/api";
export const CONTRACT = (import.meta.env.VITE_UPSHIELD_CONTRACT ?? "") as `0x${string}`;
export const CHAIN_ID = 61997;
export const EXPLORER = "https://explorer-studio-dev.genlayer.com/";

// Studio Next (chain 61997) uses genlayer-js's Studio dev chain definition, pointed at the Studio Next RPC.
const baseChain: any = (chains as any).studioDevnet ?? (chains as any).studionet;
export const chain: any = {
  ...baseChain,
  id: CHAIN_ID,
  name: "GenLayer Studio Next",
  rpcUrls: { default: { http: [RPC] } },
};

export type Signer = { address: `0x${string}`; account: any; client: any; kind: "local" | "injected" };

export const readClient = (): any => createClient({ chain });
export const localSigner = (privateKey: `0x${string}`): Signer => {
  const account = createAccount(privateKey);
  return { address: account.address as `0x${string}`, account, client: createClient({ chain, account }), kind: "local" };
};
export const injectedSigner = (address: `0x${string}`): Signer => ({
  address, account: address, client: createClient({ chain, account: address }), kind: "injected",
});

const eth = (): any => (window as any).ethereum;
export const hasInjected = () => Boolean(eth());

/** Connects an injected wallet (MetaMask etc.) and switches it to Studio Next. */
export async function connectInjected(): Promise<`0x${string}`> {
  if (!eth()) throw new Error("No injected wallet found. Use the browser wallet instead.");
  const [addr] = await eth().request({ method: "eth_requestAccounts" });
  const chainId = "0x" + CHAIN_ID.toString(16);
  try {
    await eth().request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  } catch {
    await eth().request({
      method: "wallet_addEthereumChain",
      params: [{ chainId, chainName: "GenLayer Studio Next", nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
        rpcUrls: [RPC], blockExplorerUrls: [EXPLORER] }],
    });
  }
  return addr as `0x${string}`;
}

/** Studio-only helper: asks the Studio RPC to credit a test account. */
export async function fundStudioAccount(address: string, gen = 1000): Promise<void> {
  const wei = (BigInt(gen) * 10n ** 18n).toString();
  // Built as text so the 21-digit amount is sent exactly, not as a rounded JS number.
  const body = `{"jsonrpc":"2.0","id":1,"method":"sim_fundAccount","params":["${address}",${wei}]}`;
  const res = await fetch(RPC, { method: "POST", headers: { "Content-Type": "application/json" }, body });
  const j = await res.json();
  if (j.error) throw new Error(j.error.message ?? "Funding failed");
}

async function read(functionName: string, args: unknown[] = []): Promise<any> {
  return readClient().readContract({ address: CONTRACT, functionName, args });
}

export type Summary = { pool_balance: bigint; outstanding_liability: bigint; quote_count: number; policy_count: number };
export async function getSummary(): Promise<Summary> {
  if (!CONTRACT) return { pool_balance: 0n, outstanding_liability: 0n, quote_count: 0, policy_count: 0 };
  const r = await read("get_summary");
  const o: Record<string, unknown> = r instanceof Map ? Object.fromEntries(r) : r;
  return {
    pool_balance: BigInt(o.pool_balance as any), outstanding_liability: BigInt(o.outstanding_liability as any),
    quote_count: Number(o.quote_count), policy_count: Number(o.policy_count),
  };
}
export const getQuote = async (id: string): Promise<Quote | null> => parseQuote(String(await read("get_quote", [id])));
export const getPolicy = async (id: string): Promise<Policy | null> => parsePolicy(String(await read("get_policy", [id])));
export async function listPolicies(limit = 30): Promise<Policy[]> {
  const { policy_count } = await getSummary();
  const ids = Array.from({ length: Math.min(policy_count, limit) }, (_, i) => `UPN-${policy_count - i}`);
  return (await Promise.all(ids.map(getPolicy))).filter((p): p is Policy => p !== null);
}

/** Production quote discovery: snapshot quote_count, then read every new UPQ-n and match requester + terms. */
export async function findNewQuote(before: number, requester: string, provider: string, minutes: number): Promise<Quote | null> {
  const { quote_count } = await getSummary();
  for (let i = quote_count; i > before; i--) {
    const q = await getQuote(`UPQ-${i}`);
    if (q && q.requester.toLowerCase() === requester.toLowerCase() && q.provider === provider && q.threshold_minutes === minutes) return q;
  }
  return null;
}

/**
 * Studio Next charges fees on every write. A write sent without a fee deposit is refused with
 * FeeValueMustBeNonZero, so each write first asks the SDK for a fee estimate and attaches it.
 * (The estimate is cached per function for the page's lifetime. Failures are not cached.)
 */
const feeCache = new Map<string, Record<string, unknown>>();
async function feesFor(s: Signer, functionName: string, args: unknown[], value: bigint) {
  const cached = feeCache.get(functionName);
  if (cached) return cached;
  if (typeof s.client.estimateTransactionFeesForWrite !== "function")
    throw new Error("This genlayer-js version cannot estimate fees. Use genlayer-js 2.0.0-rc.1.");
  const rec = await s.client.estimateTransactionFeesForWrite({ account: s.account, address: CONTRACT, functionName, args, value });
  const fees: Record<string, unknown> = { distribution: rec.distribution };
  if (rec.messageAllocations !== undefined) fees.messageAllocations = rec.messageAllocations;
  feeCache.set(functionName, fees);
  return fees;
}

export const send = async (s: Signer, functionName: string, args: unknown[], value = 0n): Promise<string> => {
  const fees = await feesFor(s, functionName, args, value);
  return s.client.writeContract({ address: CONTRACT, functionName, args, value, fees });
};
export const sendFund = (s: Signer, wei: bigint) => send(s, "fund_pool", [], wei);
export const sendQuote = (s: Signer, provider: string, minutes: number, start: string, end: string, payoutWei: bigint) =>
  send(s, "request_quote", [provider, minutes, start, end, payoutWei]);
export const sendBuy = (s: Signer, quoteId: string, premiumWei: bigint) => send(s, "buy_policy_from_quote", [quoteId], premiumWei);
export const sendClaim = (s: Signer, policyId: string) => send(s, "check_claim", [policyId]);

export async function txStatus(hash: string): Promise<string> {
  const tx: any = await readClient().getTransaction({ hash });
  return String(tx?.statusName ?? tx?.status ?? "PENDING");
}

/** ACCEPTED or FINALIZED only means validators agreed. The contract call itself can still have failed (a rule revert). */
export async function txFailed(hash: string): Promise<boolean> {
  const tx: any = await readClient().getTransaction({ hash });
  const result = [tx?.txExecutionResultName, tx?.resultName, tx?.txExecutionResult, tx?.executionResult].map(String).join(" ");
  return /ERROR|REVERT/i.test(result);
}
