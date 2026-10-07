# Submission answers

## One-liner
UpShield is parametric outage insurance on GenLayer: validators price the risk, a shared pool backs the cover, and consensus settles claims from real status-page evidence.

## Project overview (888 characters)
UpShield is parametric outage insurance for small online businesses, built on GenLayer. A buyer picks a provider (GitHub, Cloudflare, Discord or Vercel), an outage length (for example 60+ minutes) and a coverage window. An Intelligent Contract has validators read the provider's public status-page history and put the risk in a band (LOW, MODERATE, HIGH), and the contract itself derives the exact premium. The buyer pays that premium into a shared pool. After the window ends, anyone can trigger a claim: validators reconcile the official status page with an independent source (Hacker News) into one number of outage minutes. Plain contract arithmetic compares that number to the stored threshold and pays out from the pool, so the AI never decides a payout by wording alone. GenLayer is central twice: pricing risk and judging whether the outage happened, where sources often disagree.

## How-to
1. Open [your Vercel link] and click Connect wallet (Studio Next, chain ID 61997).
2. In Get cover, open the Request quote tab. Choose a provider, an outage threshold in minutes, a payout, and a coverage window that starts at least 40 minutes from now. Submit and wait for the transaction to be accepted.
3. Within 60 minutes, and before coverage starts, buy cover from the same wallet: click Step 2 and pay the exact premium shown.
4. Open The Ledger and find your policy (UPN-1). Its status is ACTIVE.
5. After the coverage window closes, open the policy (UPN-1) and click Check claim. The contract refuses it before then.

Tip: if the pool is empty, fund it first, because one policy can't exceed 20% of the pool. Contract: [your contract address].

## Expected verification outcome (399 characters)
A future-window quote finalizes with a risk band, premium and expiry. Bought by its requester before coverage starts, it creates policy UPN-1 as ACTIVE. Buying after the window starts, after the quote expires, or from another wallet reverts. Check claim reverts until the window closes; after that it finalizes as PAID_OUT (pool drops by the payout) or DECLINED. Visible on the Studio Next explorer.
