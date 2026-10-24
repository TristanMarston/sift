"""A fake Apify account for the run/ tests: actor calls, run datasets and logs, the account's run list and limits,
and named datasets. Thread-safe, and every result depends on the call's input (not its order), because lanes run in
parallel. Plus a generic mapper, so rows need no marketplace-specific fields."""
import threading
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import scrape as S
from listing import Normalized
from normalize.common import Drop


def query_of(run_input: dict) -> str:
    for key in ("query", "searchQuery"):
        if key in run_input:
            return run_input[key]
    for key in ("keywords", "searchQueries"):
        if key in run_input:
            return run_input[key][0]
    return parse_qs(urlparse(run_input["categoryUrls"][0]).query)["query"][0]   # poshmark


def items_of(run_input: dict) -> int:
    return run_input.get("maxItems") or run_input["maxResultsPerScrape"]


def full_rows(marketplace: str, query: str, n: int) -> list[dict]:
    """n distinct listings for a query, with seller identity the runner must scrub ("itemId" survives eBay's keep list)."""
    return [{"type": "listing", "itemId": f"{query}-{k}", "title": f"{query} {k}", "description": "100% cotton " + "d" * 60,
             "sellerUsername": "bob"} for k in range(n)]


class FakeApify:
    """`rows(marketplace, query, n) -> list` scripts a run's dataset (default: n full rows); `status(marketplace, query)`
    its status (default SUCCEEDED); `cost(marketplace, items) -> usd` its real bill (default: our own estimate)."""
    MP = {a.id: mp for mp, a in S.ACTORS.items()}

    def __init__(self, rows=full_rows, status=None, cost=None, max_usage=205.0, usage=0.0, active=0):
        self.rows, self.status, self.cost = rows, status or (lambda mp, q: "SUCCEEDED"), cost
        self.max_usage, self.usage, self.active = max_usage, usage, active
        self.lock, self.calls, self.jobs, self.storage, self.named = threading.Lock(), [], {}, {}, {}

    def actor(self, actor_id):
        def call(run_input, max_total_charge_usd, run_timeout, logger):
            mp, q = self.MP[actor_id], query_of(run_input)
            items = self.rows(mp, q, items_of(run_input))
            a = S.ACTORS[mp]
            usd = self.cost(mp, len(items)) if self.cost else float(len(items) * a.item_usd + a.start_usd)
            with self.lock:
                run_id = f"run{len(self.jobs)}"
                self.calls.append((mp, q))
                self.jobs[run_id] = dict(dataset=f"ds-{run_id}", usd=usd)
                self.storage[f"ds-{run_id}"] = items
                self.usage += usd
            status = self.status(mp, q)
            return SimpleNamespace(id=run_id, status=status, default_dataset_id=f"ds-{run_id}",
                                   status_message=None if status == "SUCCEEDED" else "actor crashed")
        return SimpleNamespace(call=call)

    def run(self, run_id):
        run = self.jobs.get(run_id)
        return SimpleNamespace(
            log=lambda: SimpleNamespace(get=lambda: ""),
            get=lambda: SimpleNamespace(id=run_id, usage_total_usd=run["usd"]) if run else None,
            dataset=lambda: self.dataset(run["dataset"] if run else "missing"))

    def dataset(self, dataset_id):
        def iterate_items():
            if dataset_id not in self.storage:
                raise RuntimeError(f"dataset {dataset_id} not found")   # expired, or on another account
            return iter([dict(i) for i in self.storage[dataset_id]])

        def push_items(items):
            with self.lock:
                self.storage.setdefault(dataset_id, []).extend(items if isinstance(items, list) else [items])
        return SimpleNamespace(iterate_items=iterate_items, push_items=push_items)

    def datasets(self):
        def get_or_create(name):
            with self.lock:
                self.named.setdefault(name, f"named-{name}")
                self.storage.setdefault(self.named[name], [])
            return SimpleNamespace(id=self.named[name], name=name)
        return SimpleNamespace(get_or_create=get_or_create)

    def runs(self):
        return SimpleNamespace(iterate=lambda: iter([SimpleNamespace(id=r) for r in list(self.jobs)]))

    def user(self):
        return SimpleNamespace(limits=lambda: SimpleNamespace(
            limits=SimpleNamespace(max_monthly_usage_usd=self.max_usage),
            current=SimpleNamespace(monthly_usage_usd=self.usage, active_actor_job_count=self.active)))

    def ledger(self) -> list[dict]:
        return self.storage.get(self.named.get("sift-runs"), [])


def mapper_for(mp):
    """Any record with an itemId is a listing; `junk` rows are unusable, `kids` rows filtered, `category` overrides."""
    def mapper(raw, category, scraped_at):
        if raw.get("junk"):
            raise Drop("no_price")
        if raw.get("kids"):
            raise Drop("kids")
        price = raw.get("price", 4800)
        return Normalized(id=f"{mp}:{raw['itemId']}", marketplace=mp, external_id=raw["itemId"],
                          url=f"https://{mp}.example/{raw['itemId']}", title=raw.get("title") or "tee",
                          description=raw.get("description"), status="active", scraped_at=scraped_at,
                          category=raw.get("category", category), image_urls=["https://img.example/1.jpg"],
                          cost=dict(price_cents=price, total_cents=price))
    return mapper


MAPPERS = {mp: mapper_for(mp) for mp in S.ACTORS}
EST = {mp: (a.item_usd, a.start_usd) for mp, a in S.ACTORS.items()}


def est(mp, items) -> Decimal:
    return items * EST[mp][0] + EST[mp][1]
