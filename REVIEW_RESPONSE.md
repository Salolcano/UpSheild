# Review response

**Request:** enforce the insurance timing and ownership rules in the contract, not only in the frontend: canonical UTC coverage times, a trusted current-time path, no buying after coverage starts or ends, expiring stale quotes, buyer must match the quote requester, settlement only after the window closes. Add repository tests.

## What changed in `contracts/upshield.py`

| Request | Change | Revert message |
|---|---|---|
| Canonical UTC coverage times | `_to_epoch` accepts only `YYYY-MM-DDTHH:MM:SSZ` and real calendar dates. Fractions, offsets and other formats are refused. Plain integer math, no datetime module. | `time must be canonical UTC: YYYY-MM-DDTHH:MM:SSZ` |
| Trusted current-time path | `_now()` reads the transaction timestamp (`gl.message_raw["datetime"]`, falling back to `gl.message.raw["datetime"]`). It is identical on every validator and never comes from the caller, a web page or the model. | n/a |
| No retrospective cover | `request_quote` requires the window to start at least 30 minutes after the request and last 1 hour to 30 days. `buy_policy_from_quote` refuses once the window has started or ended. | `coverage must start at least 30 minutes in the future`, `coverage has already started or ended` |
| Expire stale quotes | Each quote stores `quoted_at` and `valid_until` (60 minutes). | `quote expired` |
| Buyer must match requester | The buyer's address must equal the stored requester. | `buyer must be the quote requester` |
| Settle only after the window | `check_claim` compares the trusted time with the stored window end before fetching any evidence. The old status-page "window closed" guess was removed. | `coverage window has not ended` |

The frontend also sends canonical UTC (no milliseconds), checks the same rules before sending, and hides the claim button until the window has closed. These are conveniences only. The contract does not rely on them.

## Tests

`npm test` runs `tests/test_upshield_rules.py` (17 tests) and `tests/contract-shape.test.mjs` (5 tests), with no network.

- **Fail:** retrospective and too-soon windows, non-canonical and impossible times, purchase after coverage starts, purchase after coverage ends, a stale quote (one second past its life), a purchase from another account, a wrong premium, a claim before the window closes (no evidence is fetched), and a second settlement.
- **Pass:** a future-window quote bought by its requester, including on the last second of the quote's life, then settled as PAID_OUT or DECLINED after the window closes, with the exact transfer, pool balance and liability checked.
- **The tests themselves were checked:** removing each of the requester, started, expiry, claim-time and lead-time checks from the contract made at least one test fail.

## Limits to be clear about

- The tests run the real contract file against an offline SDK stand-in with a controllable clock, sender, value, status pages and model. They do not simulate consensus.
- `npm run e2e` is the live check on Studio Next. After the window closes, run it with `POLICY_ID=UPN-n` to settle.
- Transaction time is exposed under different names on different runtimes, which is why `_now()` tries both. Confirm on the first live run.
