# Current state

Verified here: contract logic via 26 offline tests against a stand-in for the SDK (scoring, parsing, strict types, injection attempt, fees, withdrawals, owner functions, paging, failure paths).

Not verified here (no network access in the build environment):
- Deployment and live behaviour on Studio Next, including how `gl.nondet.web.render` returns the GitHub API page and whether `gl.message_raw["datetime"]` is available. If the clock is unavailable the contract falls back to a neutral, deterministic "recency_unknown" signal instead of failing.
- `npm install`, type-check and build of `web/`, and the genlayer-js write/read calls on the rc.1 SDK.
- Studio Next fee handling for writes.
