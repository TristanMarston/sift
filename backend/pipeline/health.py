"""Is a scrape run healthy, or were we blocked? Outcome first, logs second.

An Apify run can finish SUCCEEDED, with "0 failed" requests, and still have collected nothing: the one blocked run we
saw (a Mercari actor served a challenge page) looked exactly like that. So the primary signals are what came back:
how many rows, and whether they are usable. The log only adds evidence, and it is calibrated against real logs:
healthy runs also print "HTTP 403" (recovered by switching address) and "blockedStatusCodes" (a config note).

Verdict kinds:   ok | short (warning only) | empty | failed | degraded (hard) | blocked (hard)
`bad` = anything but ok/short. `hard` = the evidence is strong enough to stop the marketplace at once."""
import re
from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError

from normalize.common import Drop

SUCCEEDED = "SUCCEEDED"
EXPECTED_FILTERS = {"kids", "unmapped_category", "non_usd", "not_listing"}  # rows we choose not to keep: normal
BAD, HARD = {"failed", "empty", "blocked", "degraded"}, {"blocked", "degraded"}

MIN_ROWS_TO_JUDGE = 10          # below this, row quality is too noisy to call
MAX_UNUSABLE_SHARE = 0.30       # more unusable rows than this = degraded
MIN_DESCRIBED_SHARE = 0.30      # fewer rows with a real description than this = card data only (Poshmark's baseline is 75%)
SHORT_SHARE = 0.20              # fewer rows than this share of the request = a warning
MAX_FAILED_REQUEST_SHARE = 0.5  # crawler requests failing more often than this = blocked
MIN_REQUESTS_TO_JUDGE = 3

_WARNING_LINE = re.compile(r"(^|\s)(WARN|ERROR|WARNING)\b")
_HARD_HINT = re.compile(r"\b(403|429)\b|forbidden|captcha|cloudflare|challenge|access denied|too many requests|rate.?limit|"
                        r"unusual traffic|verify you are human|bot detect|datadome|perimeterx|\bbanned\b|request blocked|"
                        r"blocked by|you (?:are|have been) blocked", re.I)
_BENIGN = re.compile(r"blockedStatusCodes|retryOnBlocked")  # Poshmark prints this config note on every healthy run
_SOFT_HINT = re.compile(r"No listings extracted|No new items intercepted|Scraped 0 listing|Total listings: 0|Pushed 0 listing", re.I)
_GAVE_UP = re.compile(r"giving up|gave up|retries exhausted|max(?:imum)? retries|all (?:proxies|addresses) (?:failed|refused)", re.I)
_ROTATION = re.compile(r"refused.*\((\d+) of (\d+)\)")
_CRAWLER_STATS = re.compile(r'"requestsFinished":(\d+),"requestsFailed":(\d+)')
_STATUS_COUNTS = re.compile(r"Total (\d+) requests: (\d+) succeeded, (\d+) failed")
_EBAY_TOKENS = re.compile(r"Token pool: (\d+) usable")


@dataclass
class RowCounts:
    """What one run's saved rows turned out to be (classified with the marketplace's own mapper)."""
    good: int = 0
    duplicates: int = 0
    described: int = 0   # good + duplicate rows whose description has more than 40 characters
    filtered: Counter = field(default_factory=Counter)
    bad: Counter = field(default_factory=Counter)

    @property
    def saved(self) -> int:
        return self.good + self.duplicates + sum(self.filtered.values()) + sum(self.bad.values())

    def add(self, kind: str, reason: str | None = None, described: bool = False) -> None:
        if kind == "good":
            self.good += 1
        elif kind == "duplicate":
            self.duplicates += 1
        elif kind == "filtered":
            self.filtered[reason] += 1
        else:
            self.bad[reason] += 1
        self.described += described and kind in ("good", "duplicate")


@dataclass
class Verdict:
    kind: str
    reasons: list[str] = field(default_factory=list)   # why it is bad (or short)
    notes: list[str] = field(default_factory=list)     # worth knowing, not a problem

    @property
    def bad(self) -> bool:
        return self.kind in BAD

    @property
    def hard(self) -> bool:
        return self.kind in HARD


def classify_row(mapper, raw: dict, category: str, scraped_at):
    """-> (kind, reason, normalized). kind is good / filtered (expected, e.g. kids) / bad (unusable)."""
    try:
        return "good", None, mapper(raw, category, scraped_at)
    except Drop as why:
        return ("filtered" if str(why) in EXPECTED_FILTERS else "bad"), str(why), None
    except ValidationError:
        return "bad", "invalid", None
    except Exception as e:
        return "bad", f"error:{type(e).__name__}", None


def _log_evidence(log: str, status_message: str | None):
    """Pull block evidence out of the log. -> (blocked_reasons, hard_hints, soft_hints, recovered_note, layout_note)"""
    warnings = [l for l in log.splitlines() if _WARNING_LINE.search(l) and not _BENIGN.search(l)]
    if status_message:
        warnings.append(status_message)
    blocked, hard, soft, notes = [], [], [], []
    for line in warnings:
        if _HARD_HINT.search(line):
            hard.append(re.sub(r"\s+", " ", line).strip()[:140])
        if _SOFT_HINT.search(line):
            soft.append(_SOFT_HINT.search(line).group(0))
    rotations = [(int(a), int(b)) for l in warnings for a, b in _ROTATION.findall(l)]
    spent = [(a, b) for a, b in rotations if a >= b]
    if spent:
        blocked.append(f"ran out of fresh addresses ({spent[0][0]} of {spent[0][1]}): the site keeps refusing us")
    elif rotations:
        notes.append(f"{len(rotations)} address refusals (HTTP 403)")
    if any(_GAVE_UP.search(l) for l in warnings):
        blocked.append("the actor reports giving up")
    for text in (log, status_message or ""):
        for done, failed in _CRAWLER_STATS.findall(text):
            if int(done) + int(failed) >= MIN_REQUESTS_TO_JUDGE and int(failed) / (int(done) + int(failed)) >= MAX_FAILED_REQUEST_SHARE:
                blocked.append(f"{failed} of {int(done) + int(failed)} requests failed")
        for total, _ok, failed in _STATUS_COUNTS.findall(text):
            if int(total) >= MIN_REQUESTS_TO_JUDGE and int(failed) / int(total) >= MAX_FAILED_REQUEST_SHARE:
                blocked.append(f"{failed} of {total} requests failed")
    if any(n == "0" for n in _EBAY_TOKENS.findall(log)):
        blocked.append("no usable eBay auth token left")
    if re.search(r"site layout may have changed", log):
        notes.append("the actor warns that the site layout may have changed (it fell back to cached settings)")
    return list(dict.fromkeys(blocked)), hard, soft, notes


def assess(status: str, status_message: str | None, requested: int, rows: RowCounts, log: str = "",
           expects_description: bool = True) -> Verdict:
    if status != SUCCEEDED:
        return Verdict("failed", [f"run ended {status}" + (f": {status_message}" if status_message else "")])
    blocked, hard, soft, notes = _log_evidence(log, status_message)
    if blocked:
        return Verdict("blocked", blocked, notes)
    n = rows.saved
    if n > 0:     # refusals only "recovered" if rows actually came back
        notes = [note + " recovered by switching address" if "address refusals" in note else note for note in notes]
    else:
        notes = [note for note in notes if "address refusals" not in note]
    if n == 0:
        if hard:
            return Verdict("blocked", [f"no rows, and the log says: {hard[0]}"], notes)
        return Verdict("empty", [f"no rows returned ({'; '.join(dict.fromkeys(soft))})" if soft else "no rows returned"], notes)
    if hard:
        notes.append(f"{len(hard)} warning(s) mentioning a refusal, but rows came back")
    usable = rows.good + rows.duplicates
    unusable = sum(rows.bad.values())
    reasons = []
    if n >= MIN_ROWS_TO_JUDGE and unusable / n > MAX_UNUSABLE_SHARE:
        top = ", ".join(f"{r} {c}" for r, c in rows.bad.most_common(3))
        reasons.append(f"{unusable} of {n} rows are unusable ({top})")
    if expects_description and usable >= MIN_ROWS_TO_JUDGE and rows.described / usable < MIN_DESCRIBED_SHARE:
        reasons.append(f"only {rows.described} of {usable} rows have a description: the actor may be returning card data only")
    if reasons:
        return Verdict("degraded", reasons, notes)
    if requested >= 20 and n < SHORT_SHARE * requested:
        return Verdict("short", [f"only {n} of {requested} rows (the query may just be narrow)"], notes)
    return Verdict("ok", [], notes)
