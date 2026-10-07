# UpShield

Parametric outage insurance for small online businesses, settled by GenLayer consensus instead of a single insurer's status feed.

## Reviewer summary

A buyer requests a **quote** for a structured condition (provider, an outage length in minutes, a coverage window, a payout). GenLayer consensus reads the provider's public incident history and prices the risk as `LOW`, `MODERATE`, `HIGH` or `UNPRICEABLE`. Only then can the buyer **buy** cover, for the exact premium the band requires, into a shared pool. After the window closes, anyone can trigger a **claim check**: validators reconcile the official status page with an independent source into one number of outage minutes, and the contract's own arithmetic decides the payout.

GenLayer is central at two separate points: pricing likelihood before a policy exists, and judging occurrence after coverage ends. Both are semantic, because status pages and independent reports disagree.

- **Contract:** `ADD_ADDRESS_AFTER_DEPLOY` on Studio Next
- **Main workflow:** request quote -> buy cover from that quote -> window ends -> `check_claim` -> validators agree on outage minutes -> contract compares them with the stored threshold and pays.

## Problem and counterfactual

A conventional insurer reads one status page, and providers tend to understate their own outages. Buyers distrust that single point, and so do the other pool members if the feed is gamed. GenLayer removes the single point of trust: independent validators each fetch the evidence and must agree before value moves. See [`DECISION.md`](DECISION.md).

## Quote-band underwriting

`premium = ceil(payout / multiple)` with multiples LOW 15x, MODERATE 8x, HIGH 3x. `UNPRICEABLE` is refused. The buyer only chooses how much cover to request, never the price. Pool gates: one policy can never exceed 20% of the pool, and total open liability can never exceed the pool.

## Timing and ownership rules (enforced in the contract)

Every rule below is checked by `contracts/upshield.py`, so a script that skips the website gets the same refusals.

| Rule | Where | Revert message |
|---|---|---|
| Coverage times must be canonical UTC `YYYY-MM-DDTHH:MM:SSZ` (no fractions, no offsets, real calendar dates only) | `request_quote` | `time must be canonical UTC...` |
| Coverage must start at least 30 minutes after the request, and last 1 hour to 30 days | `request_quote` | `coverage must start at least 30 minutes in the future` |
| A quote is issued with `valid_until = quoted_at + 60 minutes` and expires after that | `buy_policy_from_quote` | `quote expired` |
| Cover cannot be bought once its window has started or ended | `buy_policy_from_quote` | `coverage has already started or ended` |
| Only the wallet that requested a quote can buy it | `buy_policy_from_quote` | `buyer must be the quote requester` |
| A claim check is refused until the window has closed, before any evidence is fetched | `check_claim` | `coverage window has not ended` |

**Trusted current time.** The contract reads the transaction timestamp (`gl.message_raw["datetime"]`, with a fallback to `gl.message.raw["datetime"]` for newer runtimes). It is part of the transaction, so it is identical on every validator. It is never taken from the caller, a web page or the model. Time is parsed with plain integer math in the contract itself.

## Architecture

- **Contract:** `contracts/upshield.py`. One `gl.Contract` storing quotes and policies (JSON text in a `TreeMap`), a shared pool and a liability counter. `request_quote` and `check_claim` are the two consensus rounds. `fund_pool` and `buy_policy_from_quote` are deterministic payable writes.
- **Frontend:** Vite + React 19 + React Router v7 + TypeScript strict + Tailwind v4.
  - `src/routes.tsx` declares routes. Page data is fetched by route loaders.
  - `src/pages` holds one module per route: `/` (home and get cover), `/policies` (The Ledger), `/policy/:policyId`.
  - `src/components` holds the two-wallet system (`wallet-provider.tsx`), the transaction lifecycle UI (`transaction-provider.tsx`) and the quote-then-buy flow (`write-actions.tsx`).
  - `src/lib` holds the GenLayer client and contract calls, and formatting helpers.
- **Two wallets:** a browser wallet generated and stored in `localStorage` with export and import, or an injected wallet (MetaMask etc.). Both use the same `genlayer-js` client.
- **Reads need no wallet.** The Ledger is public.
- **Fees:** Studio Next charges fees on every write. Before each write the app asks `genlayer-js` for a fee estimate (`estimateTransactionFeesForWrite`) and attaches it, because a write without a fee deposit is refused (`FeeValueMustBeNonZero`). The wallet therefore needs GEN for the fee on top of any amount it sends.
- **Success check:** `ACCEPTED` or `FINALIZED` only means validators agreed. The app then checks the transaction's execution result, so a call the contract refused (for example, a rule revert) is never shown as a success.
- **Quote discovery:** the app snapshots `quote_count` before the write, waits for the transaction, then reads every new `UPQ-n` and matches requester and terms.

## Run it

```
npm ci
cp .env.example .env     # set VITE_UPSHIELD_CONTRACT
npm run dev
```

Checks: `npm run lint`, `npm run build`, `npm test`, `npm run e2e`.

`npm test` runs two suites with no network:
- `tests/contract-shape.test.mjs`: the contract keeps its header and the methods and rules the app depends on.
- `tests/test_upshield_rules.py`: the real contract file run against a small offline SDK stand-in (`tests/shim`) with a controllable transaction clock, sender, attached value, mocked status pages and a mocked model. It shows that retrospective windows, stale quotes, buying after coverage starts or ends, and cross-account purchases all fail, that a claim before the window closes fails without fetching evidence, and that a future-window quote bought by its requester settles through the intended flow (paid out or declined). It does not simulate consensus, so `npm run e2e` is the live check on Studio Next (set `POLICY_ID=UPN-n` to run the claim once the window has closed).

## Honest limitations

- Not yet run end to end on Studio Next. Record real transaction hashes here after the first run.
- The Studio Next chain definition is `genlayer-js`'s Studio dev chain (chain ID 61997) pointed at the Studio Next RPC. The fee flow was written from the `genlayer-js` 2.0.0-rc.1 documentation and has not yet been run end to end here.
- The injected-wallet path and the Studio faucet button (`sim_fundAccount`) were not tested.
- Timing depends on the runtime exposing the transaction timestamp under one of the two names above. The tests simulate it; confirm it on the first live run.
- Risk bands come from recent incident history only, not a fitted actuarial model.
- A reverted payable write may not refund the value sent, so the app checks every condition before sending (`preflightQuoteError`).
- Studio balances are simulated, not real value.
