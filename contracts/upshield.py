# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

import json

import genlayer as gl
from genlayer.types import *


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


# Public status pages that expose the same keyless JSON API (/api/v2/...)
PROVIDERS = {
    "github": "https://www.githubstatus.com",
    "cloudflare": "https://www.cloudflarestatus.com",
    "discord": "https://discordstatus.com",
    "vercel": "https://www.vercel-status.com",
}

# Premium = ceil(payout / multiple). Riskier outage = lower multiple = higher premium.
BAND_MULTIPLE = {"LOW": 15, "MODERATE": 8, "HIGH": 3}

MIN_PREMIUM = 1000  # wei, avoids dust premiums
POOL_CAP_DIVISOR = 5  # one policy can never exceed 20% of the pool

# Timing rules, enforced here in the contract (not only in the frontend).
MIN_LEAD_SECONDS = 1800  # coverage must start at least 30 minutes after the quote request
QUOTE_TTL_SECONDS = 3600  # a quote can be bought for 60 minutes after it is issued
MIN_WINDOW_SECONDS = 3600  # shortest coverage window: 1 hour
MAX_WINDOW_SECONDS = 30 * 86400  # longest coverage window: 30 days


def _clean(text: str) -> str:
    return text.replace("```json", "").replace("```", "").strip()


_DIGITS = "0123456789"
_TIME_FORMAT = "time must be canonical UTC: YYYY-MM-DDTHH:MM:SSZ"


def _num(s: str, a: int, b: int) -> int:
    part = s[a:b]
    if len(part) != b - a or any(c not in _DIGITS for c in part):
        raise gl.vm.UserError(_TIME_FORMAT)
    return int(part)


def _days_in_month(y: int, m: int) -> int:
    if m == 2:
        return 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    return 30 if m in (4, 6, 9, 11) else 31


def _to_epoch(s: str) -> int:
    """Strict canonical UTC only (YYYY-MM-DDTHH:MM:SSZ) to unix seconds.
    Pure integer math: no datetime module, no offsets, no fractions, no local time."""
    if (
        len(s) != 20
        or s[4] != "-" or s[7] != "-" or s[10] != "T"
        or s[13] != ":" or s[16] != ":" or s[19] != "Z"
    ):
        raise gl.vm.UserError(_TIME_FORMAT)
    y, mo, d = _num(s, 0, 4), _num(s, 5, 7), _num(s, 8, 10)
    h, mi, se = _num(s, 11, 13), _num(s, 14, 16), _num(s, 17, 19)
    if y < 1970 or y > 2200 or mo < 1 or mo > 12:
        raise gl.vm.UserError("not a real UTC time")
    if d < 1 or d > _days_in_month(y, mo) or h > 23 or mi > 59 or se > 59:
        raise gl.vm.UserError("not a real UTC time")
    yy = y - 1 if mo <= 2 else y
    era = yy // 400
    yoe = yy - era * 400
    mp = mo + 9 if mo <= 2 else mo - 3
    doy = (153 * mp + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + h * 3600 + mi * 60 + se


def _now() -> int:
    """Trusted current time: the transaction timestamp, which is part of the transaction
    itself and therefore identical on every validator. It is never taken from the caller,
    a web page or the model. Runtimes expose it differently, so three routes are tried:
    gl.message_raw (older), gl.message.raw (newer), then the Python clock, which GenVM
    pins to the transaction timestamp."""
    try:
        raw = str(gl.message_raw["datetime"])
    except (AttributeError, KeyError, TypeError):
        try:
            raw = str(gl.message.raw["datetime"])
        except (AttributeError, KeyError, TypeError):
            import datetime

            raw = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return _to_epoch(raw[:19] + "Z")


class UpShield(gl.contract.Contract):
    admin: Address
    pool_balance: u256
    outstanding_liability: u256
    quote_count: u256
    policy_count: u256
    quotes: gl.storage.TreeMap[str, str]  # id -> JSON text
    policies: gl.storage.TreeMap[str, str]  # id -> JSON text

    def __init__(self):
        self.admin = gl.message.sender_address
        self.pool_balance = 0
        self.outstanding_liability = 0
        self.quote_count = 0
        self.policy_count = 0

    # ------------------------------------------------------------------ pool
    @gl.public.write.payable
    def fund_pool(self) -> None:
        v = gl.message.value
        if v == 0:
            raise gl.vm.UserError("send some value")
        self.pool_balance = self.pool_balance + v

    # ----------------------------------------------------------------- quote
    @gl.public.write
    def request_quote(
        self,
        provider: str,
        threshold_minutes: int,
        coverage_start: str,
        coverage_end: str,
        requested_payout: int,
    ) -> None:
        if provider not in PROVIDERS:
            raise gl.vm.UserError("unknown provider")
        if threshold_minutes < 5:
            raise gl.vm.UserError("threshold must be at least 5 minutes")
        if requested_payout <= 0:
            raise gl.vm.UserError("payout must be positive")
        start_ts = _to_epoch(coverage_start)  # rejects anything not canonical UTC
        end_ts = _to_epoch(coverage_end)
        now = _now()
        if start_ts < now + MIN_LEAD_SECONDS:
            raise gl.vm.UserError("coverage must start at least 30 minutes in the future")
        if end_ts - start_ts < MIN_WINDOW_SECONDS or end_ts - start_ts > MAX_WINDOW_SECONDS:
            raise gl.vm.UserError("coverage window must be between 1 hour and 30 days")

        url = PROVIDERS[provider] + "/api/v2/incidents.json"

        def price() -> str:
            history = gl.nondet.web.render(url, mode="text")[:12000]
            task = f"""
You are an underwriter for outage insurance.
Below is the recent public incident history of the provider "{provider}"
(Atlassian Statuspage JSON, newest incidents first).

{history}
End of incident history.

Insured condition: one single outage of at least {threshold_minutes} minutes
(measured from incident created_at to resolved_at, any impact level).

Count how many incidents in the history lasted at least {threshold_minutes} minutes,
and roughly what time span the history covers. Then choose a risk band:
- "LOW": such outages are rare in the history
- "MODERATE": they happen from time to time
- "HIGH": they happen often
- "UNPRICEABLE": history is missing, unreadable or too short to judge

Respond ONLY with this JSON, nothing else, no formatting prefix or suffix:
{{
"qualifying_incidents": int,
"history_span_days": int,
"risk_band": str,
"rationale": str
}}
"""
            return _clean(gl.nondet.exec_prompt(task))

        result = gl.eq_principle.prompt_comparative(
            price, "The value of risk_band has to match"
        )
        data = json.loads(result)
        band = str(data.get("risk_band", "UNPRICEABLE")).upper()
        if band not in BAND_MULTIPLE:
            band = "UNPRICEABLE"

        required_premium = 0
        if band != "UNPRICEABLE":
            m = BAND_MULTIPLE[band]
            required_premium = -(-requested_payout // m)  # ceiling division
            if required_premium < MIN_PREMIUM:
                required_premium = MIN_PREMIUM

        n = int(self.quote_count) + 1
        self.quote_count = n
        qid = "UPQ-" + str(n)
        self.quotes[qid] = json.dumps(
            {
                "id": qid,
                "requester": gl.message.sender_address.as_hex,
                "provider": provider,
                "threshold_minutes": threshold_minutes,
                "coverage_start": coverage_start,
                "coverage_end": coverage_end,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "quoted_at": now,
                "valid_until": now + QUOTE_TTL_SECONDS,
                "requested_payout": requested_payout,
                "risk_band": band,
                "required_premium": required_premium,
                "qualifying_incidents": data.get("qualifying_incidents", 0),
                "history_span_days": data.get("history_span_days", 0),
                "rationale": str(data.get("rationale", ""))[:600],
                "consumed": False,
            }
        )

    # ------------------------------------------------------------------- buy
    @gl.public.write.payable
    def buy_policy_from_quote(self, quote_id: str) -> None:
        if quote_id not in self.quotes:
            raise gl.vm.UserError("quote not found")
        q = json.loads(self.quotes[quote_id])
        if q["consumed"]:
            raise gl.vm.UserError("quote already used")
        if q["risk_band"] == "UNPRICEABLE":
            raise gl.vm.UserError("quote is unpriceable")
        if gl.message.sender_address.as_hex != q["requester"]:
            raise gl.vm.UserError("buyer must be the quote requester")
        now = _now()
        if now >= int(q["start_ts"]):
            raise gl.vm.UserError("coverage has already started or ended")
        if now > int(q["valid_until"]):
            raise gl.vm.UserError("quote expired")
        if gl.message.value != q["required_premium"]:
            raise gl.vm.UserError("send exactly the required premium")

        payout = int(q["requested_payout"])
        pool_after = int(self.pool_balance) + int(gl.message.value)
        if payout > pool_after // POOL_CAP_DIVISOR:
            raise gl.vm.UserError("payout exceeds 20% of pool; fund the pool first")
        if int(self.outstanding_liability) + payout > pool_after:
            raise gl.vm.UserError("pool cannot back this policy")

        self.pool_balance = pool_after
        self.outstanding_liability = int(self.outstanding_liability) + payout

        q["consumed"] = True
        self.quotes[quote_id] = json.dumps(q)

        n = int(self.policy_count) + 1
        self.policy_count = n
        pid = "UPN-" + str(n)
        self.policies[pid] = json.dumps(
            {
                "id": pid,
                "quote_id": quote_id,
                "holder": gl.message.sender_address.as_hex,
                "provider": q["provider"],
                "threshold_minutes": q["threshold_minutes"],
                "coverage_start": q["coverage_start"],
                "coverage_end": q["coverage_end"],
                "start_ts": q["start_ts"],
                "end_ts": q["end_ts"],
                "premium": q["required_premium"],
                "payout_amount": payout,
                "status": "ACTIVE",
                "resolved_outage_minutes": 0,
                "evidence_note": "",
            }
        )

    # ----------------------------------------------------------------- claim
    @gl.public.write
    def check_claim(self, policy_id: str) -> None:
        if policy_id not in self.policies:
            raise gl.vm.UserError("policy not found")
        p = json.loads(self.policies[policy_id])
        if p["status"] != "ACTIVE":
            raise gl.vm.UserError("policy is not active")
        # Settlement is only possible once the insured window has closed. This is
        # checked against the trusted transaction time before any evidence is fetched.
        if _now() < int(p["end_ts"]):
            raise gl.vm.UserError("coverage window has not ended")

        base = PROVIDERS[p["provider"]]
        provider = p["provider"]
        start = p["coverage_start"]
        end = p["coverage_end"]
        threshold = p["threshold_minutes"]

        def judge() -> str:
            incidents = gl.nondet.web.render(
                base + "/api/v2/incidents.json", mode="text"
            )[:12000]
            news = gl.nondet.web.render(
                "https://hn.algolia.com/api/v1/search_by_date?tags=story&query="
                + provider
                + "%20outage",
                mode="text",
            )[:4000]
            task = f"""
You settle outage insurance claims. Insured provider: "{provider}".
Coverage window (UTC): {start} to {end}. The window has already ended.

SOURCE A - official incident history (Statuspage JSON):
{incidents}

SOURCE C - independent Hacker News stories about outages (corroboration only):
{news}

Steps:
1. Find incidents in SOURCE A overlapping the window and compute the LONGEST single
   outage inside the window, in minutes (created_at to resolved_at, clipped to the window).
   If an incident has no resolved_at, clip it to the end of the window.
2. Use SOURCE C only to sanity-check or break ties. Do not average.
3. If the data is missing or unreadable, verdict "INSUFFICIENT_EVIDENCE".

Respond ONLY with this JSON, nothing else, no formatting prefix or suffix:
{{
"resolved_outage_minutes": int,
"verdict": str,
"evidence_note": str
}}
verdict is one of OUTAGE_CONFIRMED, NO_OUTAGE, INSUFFICIENT_EVIDENCE.
"""
            return _clean(gl.nondet.exec_prompt(task))

        result = gl.eq_principle.prompt_comparative(
            judge,
            "resolved_outage_minutes must be within 10 minutes of each other",
        )
        data = json.loads(result)
        verdict = str(data.get("verdict", "INSUFFICIENT_EVIDENCE"))
        note = str(data.get("evidence_note", ""))[:600]

        p["evidence_note"] = note
        if verdict == "INSUFFICIENT_EVIDENCE":
            self.policies[policy_id] = json.dumps(p)
            return

        minutes = int(data.get("resolved_outage_minutes", 0))
        p["resolved_outage_minutes"] = minutes
        payout = int(p["payout_amount"])
        self.outstanding_liability = int(self.outstanding_liability) - payout

        # Only this arithmetic moves money, never the model's wording.
        if minutes >= int(threshold):
            pay = min(payout, int(self.pool_balance))
            self.pool_balance = int(self.pool_balance) - pay
            p["status"] = "PAID_OUT"
            self.policies[policy_id] = json.dumps(p)
            if pay > 0:
                _Recipient(Address(p["holder"])).emit_transfer(value=u256(pay))
        else:
            p["status"] = "DECLINED"
            self.policies[policy_id] = json.dumps(p)

    # ----------------------------------------------------------------- views
    @gl.public.view
    def get_summary(self) -> dict[str, int]:
        return {
            "pool_balance": int(self.pool_balance),
            "outstanding_liability": int(self.outstanding_liability),
            "quote_count": int(self.quote_count),
            "policy_count": int(self.policy_count),
        }

    @gl.public.view
    def get_quote(self, quote_id: str) -> str:
        return self.quotes.get(quote_id, "")

    @gl.public.view
    def get_policy(self, policy_id: str) -> str:
        return self.policies.get(policy_id, "")

    @gl.public.view
    def get_providers(self) -> list[str]:
        return list(PROVIDERS.keys())
