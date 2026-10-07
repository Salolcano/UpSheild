"""Contract-level timing and ownership rules for contracts/upshield.py.

Runs the real contract file against an offline SDK stand-in (tests/shim) with a
controllable transaction clock, sender, attached value, mocked status pages and a
mocked model. Run with:  python3 -m unittest discover -s tests -p "test_*.py" -v
"""
import calendar
import importlib.util
import json
import os
import sys
import time
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "shim"))
import genlayer as gl  # noqa: E402  (the offline stand-in)

CONTRACT_PATH = os.path.join(HERE, "..", "contracts", "upshield.py")
GEN = 10**18
ADMIN, ALICE, BOB = "0xAdmin000000000000000000000000000000000", "0xAlice00000000000000000000000000000000000", "0xBob0000000000000000000000000000000000000"
NOW = calendar.timegm((2026, 10, 10, 12, 0, 0))
MIN, HOUR, DAY = 60, 3600, 86400


def iso(epoch: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def clock(epoch: int) -> None:
    """Sets the trusted transaction time (the runtime gives it with microseconds)."""
    gl.message_raw["datetime"] = iso(epoch)[:-1] + ".123456Z"


def as_user(address: str, value: int = 0) -> None:
    gl.message = SimpleNamespace(sender_address=gl.Address(address), value=value)


def load_module():
    spec = importlib.util.spec_from_file_location("upshield_under_test", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def setUp(self):
        gl.transfers.clear()
        gl.llm_calls.clear()
        gl.web_pages.clear()
        gl.web_pages["githubstatus.com"] = "{\"incidents\": []}"
        gl.web_pages["hn.algolia.com"] = "{\"hits\": []}"
        self.judge = {"resolved_outage_minutes": 95, "verdict": "OUTAGE_CONFIRMED", "evidence_note": "one 95 minute incident"}

        def fake_llm(prompt):
            if "underwriter" in prompt:
                return json.dumps({"qualifying_incidents": 1, "history_span_days": 90, "risk_band": "LOW", "rationale": "rare"})
            return json.dumps(self.judge)

        gl.llm = fake_llm
        self.mod = load_module()
        clock(NOW)
        as_user(ADMIN)
        self.c = self.mod.UpShield()
        as_user(ADMIN, 1000 * GEN)
        self.c.fund_pool()

    # helpers -----------------------------------------------------------
    def quote(self, start, end, user=ALICE, payout=10 * GEN, minutes=60):
        as_user(user)
        self.c.request_quote("github", minutes, iso(start), iso(end), payout)
        return json.loads(self.c.get_quote("UPQ-%d" % self.c.get_summary()["quote_count"]))

    def buy(self, q, user=ALICE, value=None):
        as_user(user, q["required_premium"] if value is None else value)
        self.c.buy_policy_from_quote(q["id"])

    def policy(self, pid="UPN-1"):
        return json.loads(self.c.get_policy(pid))

    def rejects(self, fn, text):
        with self.assertRaises(gl.UserError) as cm:
            fn()
        self.assertIn(text, str(cm.exception))


class TestCanonicalTime(Base):
    def test_epoch_matches_the_calendar(self):
        for stamp in ["1970-01-01T00:00:00Z", "2000-02-29T23:59:59Z", "2026-10-10T12:00:00Z", "2100-03-01T00:00:00Z", "2024-12-31T23:59:59Z"]:
            expected = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
            self.assertEqual(self.mod._to_epoch(stamp), expected, stamp)

    def test_non_canonical_or_impossible_times_are_rejected(self):
        good_end = iso(NOW + 2 * DAY)
        for bad in [
            "2026-10-12T12:00:00.000Z",   # fractional seconds
            "2026-10-12T12:00:00+00:00",  # offset instead of Z
            "2026-10-12 12:00:00Z",       # space instead of T
            "2026-10-12T12:00:00",        # no zone
            "2026-02-30T12:00:00Z",       # not a real day
            "2026-13-01T12:00:00Z",       # not a real month
            "2026-10-12T24:00:00Z",       # not a real hour
            "26-10-12T12:00:00Z",         # short year
            "",
        ]:
            as_user(ALICE)
            self.rejects(lambda b=bad: self.c.request_quote("github", 60, b, good_end, 10 * GEN), "")
        self.assertEqual(self.c.get_summary()["quote_count"], 0)

    def test_the_trusted_clock_ignores_microseconds(self):
        clock(NOW)
        self.assertEqual(self.mod._now(), NOW)

    def test_the_clock_falls_back_to_the_newer_runtime_name(self):
        saved = gl.message_raw
        try:
            gl.message_raw = None  # older name missing
            gl.message = SimpleNamespace(sender_address=gl.Address(ALICE), value=0, raw={"datetime": iso(NOW + 5)[:-1] + ".000001Z"})
            self.assertEqual(self.mod._now(), NOW + 5)
        finally:
            gl.message_raw = saved


class TestQuoteTiming(Base):
    def test_retrospective_and_too_soon_windows_cannot_be_quoted(self):
        for start in [NOW - DAY, NOW - 1, NOW + 5 * MIN, NOW + 29 * MIN]:
            as_user(ALICE)
            self.rejects(lambda s=start: self.c.request_quote("github", 60, iso(s), iso(s + 2 * HOUR), 10 * GEN), "30 minutes in the future")
        self.assertEqual(self.c.get_summary()["quote_count"], 0)

    def test_window_length_is_bounded(self):
        as_user(ALICE)
        self.rejects(lambda: self.c.request_quote("github", 60, iso(NOW + HOUR), iso(NOW + HOUR + 30 * MIN), 10 * GEN), "between 1 hour and 30 days")
        self.rejects(lambda: self.c.request_quote("github", 60, iso(NOW + HOUR), iso(NOW + HOUR + 31 * DAY), 10 * GEN), "between 1 hour and 30 days")

    def test_a_future_window_quote_is_issued_with_an_expiry(self):
        q = self.quote(NOW + 2 * HOUR, NOW + 26 * HOUR)
        self.assertEqual(q["requester"], ALICE)
        self.assertEqual(q["quoted_at"], NOW)
        self.assertEqual(q["valid_until"], NOW + HOUR)
        self.assertEqual(q["start_ts"], NOW + 2 * HOUR)


class TestPurchaseRules(Base):
    def test_buying_after_coverage_has_started_fails(self):
        q = self.quote(NOW + 40 * MIN, NOW + 100 * MIN)
        clock(NOW + 50 * MIN)  # the quote is still inside its 60 minute life, but coverage began
        self.rejects(lambda: self.buy(q), "already started or ended")
        self.assertEqual(self.c.get_summary()["policy_count"], 0)

    def test_buying_after_coverage_has_ended_fails(self):
        q = self.quote(NOW + 40 * MIN, NOW + 100 * MIN)
        clock(NOW + 3 * HOUR)
        self.rejects(lambda: self.buy(q), "already started or ended")
        self.assertEqual(self.c.get_summary()["policy_count"], 0)

    def test_a_stale_quote_cannot_be_bought(self):
        q = self.quote(NOW + 2 * DAY, NOW + 3 * DAY)
        clock(NOW + HOUR + 1)  # one second past its 60 minute life; coverage is still days away
        self.rejects(lambda: self.buy(q), "quote expired")
        self.assertEqual(self.c.get_summary()["policy_count"], 0)
        self.assertFalse(json.loads(self.c.get_quote(q["id"]))["consumed"])

    def test_a_quote_is_still_valid_on_its_last_second(self):
        q = self.quote(NOW + 2 * DAY, NOW + 3 * DAY)
        clock(NOW + HOUR)
        self.buy(q)
        self.assertEqual(self.policy()["status"], "ACTIVE")

    def test_another_account_cannot_buy_my_quote(self):
        q = self.quote(NOW + 2 * HOUR, NOW + 26 * HOUR, user=ALICE)
        pool_before = self.c.get_summary()["pool_balance"]
        self.rejects(lambda: self.buy(q, user=BOB), "buyer must be the quote requester")
        summary = self.c.get_summary()
        self.assertEqual(summary["policy_count"], 0)
        self.assertEqual(summary["pool_balance"], pool_before)
        self.assertFalse(json.loads(self.c.get_quote(q["id"]))["consumed"])
        self.buy(q, user=ALICE)  # the real requester still can
        self.assertEqual(self.policy()["holder"], ALICE)

    def test_the_premium_must_match_exactly(self):
        q = self.quote(NOW + 2 * HOUR, NOW + 26 * HOUR)
        self.rejects(lambda: self.buy(q, value=q["required_premium"] - 1), "exact")


class TestSettlement(Base):
    def bought_policy(self):
        q = self.quote(NOW + 2 * HOUR, NOW + 26 * HOUR)
        clock(NOW + 10 * MIN)
        self.buy(q)
        return q

    def test_claim_before_the_window_closes_fails_and_fetches_nothing(self):
        self.bought_policy()
        as_user(BOB)
        for moment in [NOW + 3 * HOUR, NOW + 26 * HOUR - 1]:
            clock(moment)
            self.rejects(lambda: self.c.check_claim("UPN-1"), "coverage window has not ended")
        self.assertEqual([p for p in gl.llm_calls if "settle outage insurance" in p], [])
        self.assertEqual(self.policy()["status"], "ACTIVE")

    def test_intended_flow_future_quote_is_bought_then_paid_out(self):
        q = self.bought_policy()
        pool = self.c.get_summary()
        payout = 10 * GEN
        self.assertEqual(pool["outstanding_liability"], payout)
        clock(NOW + 26 * HOUR)  # exactly when the window closes
        as_user(BOB)  # anyone may trigger settlement
        self.c.check_claim("UPN-1")
        p = self.policy()
        self.assertEqual(p["status"], "PAID_OUT")
        self.assertEqual(p["resolved_outage_minutes"], 95)
        self.assertEqual(gl.transfers, [(ALICE, payout)])
        after = self.c.get_summary()
        self.assertEqual(after["outstanding_liability"], 0)
        self.assertEqual(after["pool_balance"], 1000 * GEN + q["required_premium"] - payout)

    def test_intended_flow_declined_when_the_outage_was_too_short(self):
        self.bought_policy()
        self.judge["resolved_outage_minutes"] = 20
        self.judge["verdict"] = "NO_OUTAGE"
        clock(NOW + 27 * HOUR)
        as_user(BOB)
        self.c.check_claim("UPN-1")
        self.assertEqual(self.policy()["status"], "DECLINED")
        self.assertEqual(gl.transfers, [])
        self.assertEqual(self.c.get_summary()["outstanding_liability"], 0)

    def test_insufficient_evidence_leaves_the_policy_active_for_a_retry(self):
        self.bought_policy()
        self.judge["verdict"] = "INSUFFICIENT_EVIDENCE"
        clock(NOW + 27 * HOUR)
        as_user(BOB)
        self.c.check_claim("UPN-1")
        self.assertEqual(self.policy()["status"], "ACTIVE")
        self.judge.update({"verdict": "OUTAGE_CONFIRMED", "resolved_outage_minutes": 120})
        self.c.check_claim("UPN-1")
        self.assertEqual(self.policy()["status"], "PAID_OUT")

    def test_a_settled_policy_cannot_be_settled_again(self):
        self.bought_policy()
        clock(NOW + 27 * HOUR)
        as_user(BOB)
        self.c.check_claim("UPN-1")
        self.rejects(lambda: self.c.check_claim("UPN-1"), "not active")
        self.assertEqual(len(gl.transfers), 1)


if __name__ == "__main__":
    unittest.main()
