# Design decisions

## Why this needs GenLayer
Two steps are semantic, not arithmetic:
- **Pricing:** "how often does this provider have a 60+ minute outage" depends on reading messy incident history.
- **Settlement:** "did a qualifying outage happen in this window" means reconciling an official status page (which tends to understate) with independent reports.

## Two consensus rounds
- `request_quote`: 1 web fetch + 1 prompt. Validators must agree on the risk band.
- `check_claim`: 3 web fetches (incident history, status snapshot, Hacker News) + 1 prompt. Validators must agree the window closed and that resolved outage minutes are within 10 minutes of each other.

## The model never authorizes a payout
The model returns a number of minutes. The contract compares it to the stored threshold. Only that comparison pays.

## Abstention
If evidence is missing or the window has not ended, the claim returns without changing the policy. It stays ACTIVE and can be retried.

## Premium is derived, not chosen
The buyer states the payout. The contract computes the premium from the risk band, so nobody can buy large cover cheaply against a likely outage.

## Pool limits
20% single-policy cap and a total-liability cap keep one claim from draining the pool.

## Time and ownership are contract rules, not website rules
- **Trusted time.** The contract uses the transaction timestamp, identical on every validator. Not the caller, a web page, or the model.
- **Canonical UTC only.** `YYYY-MM-DDTHH:MM:SSZ`. One format means one meaning, and no timezone or rounding disputes at settlement.
- **No retrospective cover.** Coverage must start 30+ minutes ahead at quote time, and cannot be bought once it has started or ended.
- **Quotes expire** 60 minutes after issue, so a price built on old evidence cannot be used later.
- **Quotes are personal.** Only the requester can buy, so nobody can take someone else's priced quote.
- **Settlement waits for the window.** A claim check before the window closes is refused before any evidence is fetched, which also saves validator work.
- **The status-page snapshot is no longer used to decide whether the window ended.** The contract's own clock decides, so the claim needs two fetches instead of three.
