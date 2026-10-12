# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

import json
import typing

import genlayer as gl
from genlayer.types import *

VERSION = "1.0.0"
OWNER_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"
REPO_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789._-"
VERDICTS = ["SAFE", "CAUTION", "AVOID", "INSUFFICIENT_DATA"]


# ---------------------------------------------------------------- pure helpers
# No LLM text ever reaches the stored verdict. Every consequential value is
# computed deterministically from typed fields, bucketed, and then compared
# EXACTLY across validators (strict_eq), so the leader cannot store a value the
# validators did not derive themselves. Fetched text is never put in a prompt.

def parse_repo(text: typing.Any) -> typing.Optional[str]:
    if not isinstance(text, str):
        return None
    t = text.strip().lower()
    if len(t) == 0 or len(t) > 200:
        return None
    for prefix in ("https://", "http://"):
        if t.startswith(prefix):
            t = t[len(prefix):]
    if t.startswith("www."):
        t = t[4:]
    for sep in ("?", "#"):
        if sep in t:
            t = t.split(sep)[0]
    parts = [p for p in t.split("/") if p != ""]
    if len(parts) > 0 and parts[0] == "github.com":
        parts = parts[1:]
    elif len(parts) > 0 and "." in parts[0]:
        return None  # some other host
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if len(owner) == 0 or len(owner) > 39 or owner.startswith("-") or owner.endswith("-"):
        return None
    if not all(c in OWNER_CHARS for c in owner):
        return None
    if len(repo) == 0 or len(repo) > 100 or repo in (".", ".."):
        return None
    if not all(c in REPO_CHARS for c in repo):
        return None
    return owner + "/" + repo


def _is_int(x: typing.Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _ordinal(s: typing.Any) -> typing.Optional[int]:
    """Days count for 'YYYY-MM-DD...' or None."""
    try:
        if not isinstance(s, str) or len(s) < 10:
            return None
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        if s[4] != "-" or s[7] != "-" or m < 1 or m > 12 or d < 1 or d > 31:
            return None
        if m <= 2:
            y -= 1
            m += 12
        return 365 * y + y // 4 - y // 100 + y // 400 + (153 * (m - 3) + 2) // 5 + d
    except Exception:
        return None


def unavailable(reason: str) -> dict:
    return {
        "status": reason,
        "verdict": "INSUFFICIENT_DATA",
        "score": 0,
        "signals": [reason],
    }


def score_repo(data: typing.Any, today: str) -> dict:
    """Deterministic, bucketed risk result from GitHub repo metadata."""
    if not isinstance(data, dict):
        return unavailable("malformed")
    msg = data.get("message")
    if isinstance(msg, str):
        low = msg.lower()
        if low == "not found":
            return unavailable("not_found")
        if "rate limit" in low:
            return unavailable("rate_limited")
        if "full_name" not in data:
            return unavailable("malformed")
    # strict type checks: a string like "false" is NOT a boolean
    if not isinstance(data.get("full_name"), str):
        return unavailable("malformed")
    for key in ("archived", "disabled", "fork"):
        if not isinstance(data.get(key), bool):
            return unavailable("malformed")
    for key in ("stargazers_count", "open_issues_count"):
        if not _is_int(data.get(key)) or data.get(key) < 0:
            return unavailable("malformed")
    lic = data.get("license")
    if lic is not None and not isinstance(lic, dict):
        return unavailable("malformed")
    pushed = _ordinal(data.get("pushed_at"))
    created = _ordinal(data.get("created_at"))
    now = _ordinal(today)

    score = 100
    signals: list = []
    if data["archived"]:
        score -= 50
        signals.append("archived")
    if data["disabled"]:
        score -= 50
        signals.append("disabled")
    if data["fork"]:
        score -= 5
        signals.append("fork")
    if lic is None:
        score -= 10
        signals.append("no_license")
    if now is None or pushed is None:
        score -= 5
        signals.append("recency_unknown")
    else:
        idle = now - pushed
        if idle > 730:
            score -= 40
            signals.append("abandoned_2y")
        elif idle > 365:
            score -= 30
            signals.append("stale_1y")
        elif idle > 180:
            score -= 15
            signals.append("quiet_6m")
        elif idle > 90:
            score -= 5
            signals.append("quiet_3m")
    if now is not None and created is not None:
        age = now - created
        if age < 30:
            score -= 15
            signals.append("brand_new")
        elif age < 90:
            score -= 5
            signals.append("young")
    stars = data["stargazers_count"]
    if stars < 10:
        score -= 10
        signals.append("low_adoption")
    elif stars < 100:
        score -= 5
        signals.append("modest_adoption")
    issues = data["open_issues_count"]
    if issues >= 500:
        score -= 10
        signals.append("issue_backlog_high")
    elif issues >= 100:
        score -= 5
        signals.append("issue_backlog")

    score = max(0, min(100, score))
    score = (score // 10) * 10  # bucket so tiny drifts never split validators
    if data["archived"] or data["disabled"] or score < 40:
        verdict = "AVOID"
    elif score >= 70:
        verdict = "SAFE"
    else:
        verdict = "CAUTION"
    return {"status": "OK", "verdict": verdict, "score": score, "signals": sorted(signals)}


def canonical(result: dict) -> str:
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def fetch_canonical(slug: str, today: str) -> str:
    def run() -> str:
        try:
            raw = gl.nondet.web.render("https://api.github.com/repos/" + slug, mode="text")
            start, end = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[start:end + 1])
        except Exception:
            return canonical(unavailable("fetch_failed"))
        return canonical(score_repo(data, today))

    # Every validator recomputes the SAME canonical string; the leader's value
    # is accepted only if it matches exactly.
    return gl.eq_principle.strict_eq(run)


@gl.evm.contract_interface
class _Wallet:
    class View:
        pass

    class Write:
        pass


# -------------------------------------------------------------------- contract
class RepoTrust(gl.contract.Contract):
    owner: Address
    review_fee: u256
    fees_collected: u256
    balances: gl.storage.TreeMap[Address, u256]
    last_result: gl.storage.TreeMap[Address, str]
    latest: gl.storage.TreeMap[str, str]
    revisions: gl.storage.TreeMap[str, u256]
    history: gl.storage.TreeMap[str, str]
    index: gl.storage.TreeMap[u256, str]
    repo_count: u256
    reviews_total: u256
    verdict_counts: gl.storage.TreeMap[str, u256]

    def __init__(self, review_fee: int):
        self.owner = gl.message.sender_address
        self.review_fee = review_fee if review_fee > 0 else 0
        self.fees_collected = 0
        self.repo_count = 0
        self.reviews_total = 0

    # User mistakes never revert: they return "ERR:<CODE>" and are readable via
    # get_last_result. Any value sent is credited and stays withdrawable.
    def _done(self, msg: str) -> str:
        self.last_result[gl.message.sender_address] = msg
        return msg

    def _today(self) -> str:
        try:
            return str(gl.message_raw["datetime"])[:10]
        except Exception:
            return ""

    @gl.public.write.payable
    def deposit(self) -> str:
        v = int(gl.message.value)
        if v <= 0:
            return self._done("ERR:ZERO_DEPOSIT")
        sender = gl.message.sender_address
        self.balances[sender] = int(self.balances.get(sender, 0)) + v
        return self._done("OK:DEPOSITED")

    @gl.public.write.payable
    def review(self, repo: str) -> str:
        sender = gl.message.sender_address
        v = int(gl.message.value)
        if v > 0:
            self.balances[sender] = int(self.balances.get(sender, 0)) + v
        slug = parse_repo(repo)
        if slug is None:
            return self._done("ERR:INVALID_REPO")
        fee = int(self.review_fee)
        if fee > 0 and int(self.balances.get(sender, 0)) < fee:
            return self._done("ERR:INSUFFICIENT_CREDIT")

        result = json.loads(fetch_canonical(slug, self._today()))
        verdict = result["verdict"]
        prior_raw = self.latest.get(slug, None)

        if verdict == "INSUFFICIENT_DATA":
            if prior_raw is not None:
                return self._done("OK:EVIDENCE_UNAVAILABLE_KEPT_PREVIOUS")  # no charge
        elif fee > 0:
            self.balances[sender] = int(self.balances.get(sender, 0)) - fee
            self.fees_collected = int(self.fees_collected) + fee

        rev = int(self.revisions.get(slug, 0)) + 1
        if rev == 1:
            self.index[int(self.repo_count)] = slug
            self.repo_count = int(self.repo_count) + 1
        else:
            old = json.loads(prior_raw)["verdict"]
            self.verdict_counts[old] = max(0, int(self.verdict_counts.get(old, 0)) - 1)
        rec = {
            "repo": slug,
            "revision": rev,
            "verdict": verdict,
            "score": result["score"],
            "signals": result["signals"],
            "status": result["status"],
            "reviewer": sender.as_hex,
            "as_of": self._today(),
        }
        text = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        self.latest[slug] = text
        self.history[slug + "#" + str(rev)] = text
        self.revisions[slug] = rev
        self.verdict_counts[verdict] = int(self.verdict_counts.get(verdict, 0)) + 1
        self.reviews_total = int(self.reviews_total) + 1
        return self._done("OK:" + verdict)

    @gl.public.write
    def withdraw(self, amount: int) -> str:
        sender = gl.message.sender_address
        bal = int(self.balances.get(sender, 0))
        if bal <= 0:
            return self._done("ERR:NOTHING_TO_WITHDRAW")
        amt = bal if amount <= 0 else amount
        if amt > bal:
            return self._done("ERR:AMOUNT_EXCEEDS_BALANCE")
        self.balances[sender] = bal - amt  # effects before the transfer
        _Wallet(sender).emit_transfer(value=amt)
        return self._done("OK:WITHDRAWN")

    @gl.public.write
    def withdraw_fees(self) -> str:
        sender = gl.message.sender_address
        if sender != self.owner:
            return self._done("ERR:NOT_OWNER")
        fees = int(self.fees_collected)
        if fees <= 0:
            return self._done("ERR:NO_FEES")
        self.fees_collected = 0
        _Wallet(self.owner).emit_transfer(value=fees)
        return self._done("OK:FEES_WITHDRAWN")

    @gl.public.write
    def set_review_fee(self, fee: int) -> str:
        if gl.message.sender_address != self.owner:
            return self._done("ERR:NOT_OWNER")
        if fee < 0:
            return self._done("ERR:BAD_FEE")
        self.review_fee = fee
        return self._done("OK:FEE_SET")

    # ------------------------------------------------------------------ views
    @gl.public.view
    def get_review(self, repo: str) -> dict[str, typing.Any]:
        slug = parse_repo(repo)
        raw = self.latest.get(slug, None) if slug is not None else None
        if raw is None:
            return {"found": False}
        out = json.loads(raw)
        out["found"] = True
        return out

    @gl.public.view
    def get_history(self, repo: str, revision: int) -> dict[str, typing.Any]:
        slug = parse_repo(repo)
        raw = self.history.get(slug + "#" + str(revision), None) if slug is not None else None
        if raw is None:
            return {"found": False}
        out = json.loads(raw)
        out["found"] = True
        return out

    @gl.public.view
    def get_repos(self, offset: int, limit: int) -> list[dict[str, typing.Any]]:
        count = int(self.repo_count)
        lim = max(0, min(limit, 50))
        off = max(0, offset)
        out = []
        i = count - 1 - off  # newest first
        while i >= 0 and len(out) < lim:
            slug = self.index.get(i, None)
            raw = self.latest.get(slug, None) if slug is not None else None
            if raw is not None:
                out.append(json.loads(raw))
            i -= 1
        return out

    @gl.public.view
    def get_stats(self) -> dict[str, typing.Any]:
        counts = {}
        for name in VERDICTS:
            counts[name] = int(self.verdict_counts.get(name, 0))
        return {
            "repos": int(self.repo_count),
            "reviews": int(self.reviews_total),
            "counts": counts,
        }

    @gl.public.view
    def get_balance_of(self, address: str) -> int:
        try:
            return int(self.balances.get(Address(address), 0))
        except Exception:
            return 0

    @gl.public.view
    def get_last_result(self, address: str) -> str:
        try:
            return self.last_result.get(Address(address), "")
        except Exception:
            return ""

    @gl.public.view
    def get_config(self) -> dict[str, typing.Any]:
        return {
            "owner": self.owner.as_hex,
            "review_fee": int(self.review_fee),
            "fees_collected": int(self.fees_collected),
            "version": VERSION,
        }
