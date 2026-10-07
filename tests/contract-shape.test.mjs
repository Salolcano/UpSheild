// Offline checks that need no network: run with `npm test`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../contracts/upshield.py", import.meta.url), "utf8");
const lines = src.split("\n");

test("contract starts with the required GenLayer header", () => {
  assert.equal(lines[0].trim(), "# v0.3.0");
  assert.match(lines[1], /"Depends": "py-genlayer:/);
});

test("contract exposes every method the frontend calls", () => {
  for (const m of ["fund_pool", "request_quote", "buy_policy_from_quote", "check_claim", "get_summary", "get_quote", "get_policy"]) {
    assert.match(src, new RegExp(`def ${m}\\(`), `missing ${m}`);
  }
});

test("payable methods use the payable decorator", () => {
  assert.match(src, /@gl\.public\.write\.payable\s+def fund_pool/);
  assert.match(src, /@gl\.public\.write\.payable\s+def buy_policy_from_quote/);
});

test("only arithmetic pays: payout is gated on the minutes comparison", () => {
  assert.match(src, /if minutes >= int\(threshold\)/);
});

test("timing and ownership rules live in the contract", () => {
  assert.match(src, /buyer must be the quote requester/);
  assert.match(src, /quote expired/);
  assert.match(src, /coverage has already started or ended/);
  assert.match(src, /coverage window has not ended/);
  assert.match(src, /gl\.message_raw\["datetime"\]/);
});
