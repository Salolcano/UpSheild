// On-chain end-to-end run: fund -> quote -> buy. Usage: PRIVATE_KEY=0x... VITE_UPSHIELD_CONTRACT=0x... npm run e2e
import { createClient, createAccount } from "genlayer-js";
import * as chains from "genlayer-js/chains";

const RPC = process.env.VITE_GENLAYER_RPC ?? "https://studio-next.genlayer.com/api";
const address = process.env.VITE_UPSHIELD_CONTRACT;
if (!address || !process.env.PRIVATE_KEY) throw new Error("Set PRIVATE_KEY and VITE_UPSHIELD_CONTRACT");

const chain = { ...(chains.studioDevnet ?? chains.studionet), id: 61997, name: "GenLayer Studio Next", rpcUrls: { default: { http: [RPC] } } };
const client = createClient({ chain, account: createAccount(process.env.PRIVATE_KEY) });
const GEN = 10n ** 18n;

// Studio Next charges fees: estimate them first and attach them to every write.
async function send(functionName, args, value = 0n) {
  const rec = await client.estimateTransactionFeesForWrite({ account: client.account, address, functionName, args, value });
  const fees = { distribution: rec.distribution, ...(rec.messageAllocations !== undefined && { messageAllocations: rec.messageAllocations }) };
  const hash = await client.writeContract({ address, functionName, args, value, fees });
  await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", retries: 120, interval: 3000 });
  console.log(functionName, "accepted", hash);
}

const hour = 3600 * 1000;
// Contract accepts canonical UTC only: no milliseconds.
const iso = (ms) => new Date(Date.now() + ms).toISOString().replace(/\.\d{3}Z$/, "Z");

if (process.env.POLICY_ID) {
  await send("check_claim", [process.env.POLICY_ID]);
  console.log(await client.readContract({ address, functionName: "get_policy", args: [process.env.POLICY_ID] }));
  process.exit(0);
}

await send("fund_pool", [], 1000n * GEN);
await send("request_quote", ["github", 60, iso(45 * 60 * 1000), iso(45 * 60 * 1000 + 2 * hour), 10n * GEN]);
const summary = await client.readContract({ address, functionName: "get_summary", args: [] });
const s = summary instanceof Map ? Object.fromEntries(summary) : summary;
const quoteId = "UPQ-" + s.quote_count;
const raw = await client.readContract({ address, functionName: "get_quote", args: [quoteId] });
const premium = BigInt(/"required_premium":\s*(\d+)/.exec(raw)[1]);
await send("buy_policy_from_quote", [quoteId], premium);
console.log("Done. Quote", quoteId, "premium", premium.toString());
console.log("Settlement opens when the window closes (about 2h45m from now). Then run: POLICY_ID=UPN-<n> npm run e2e");
