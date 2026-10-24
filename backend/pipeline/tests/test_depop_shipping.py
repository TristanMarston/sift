"""Step 03c: Depop shipping fetched per listing (Apify parsebird/depop-scraper, URL mode), cached by listing id."""
import jsonl
import depop_shipping as D
from listing import Listing


def depop(i, price=2000, **over):
    base = dict(id=f"depop:{i}", marketplace="depop", external_id=str(i), url=f"https://www.depop.com/products/s-{i}/",
                title="tee", status="active", scraped_at="2026-10-24T01:00:00Z", category="tshirts",
                image_urls=["https://media-photos.depop.com/b1/1/1/P0.jpg"], cost=dict(price_cents=price, total_cents=price))
    return Listing(**{**base, **over}).model_dump(mode="json")


def answer(i, ship=1.99, free=False, national=None):
    return {"id": str(i), "shippingCost": ship, "nationalShippingCost": ship if national is None else national,
            "hasFreeShipping": free, "sellerUsername": "someone", "sellerUrl": "https://depop.com/someone"}


def run(tmp_path, rows, fetch, **kw):
    (tmp_path / "listings.jsonl").write_text("".join(jsonl.dumps(r) + "\n" for r in rows))
    stats = D.ship_file(tmp_path / "listings.jsonl", tmp_path / "depop_shipping.jsonl", fetch=fetch, **kw)
    return stats, jsonl.load(tmp_path / "listings.jsonl")


def test_shipping_is_added_and_the_total_follows(tmp_path):
    stats, out = run(tmp_path, [depop(1), depop(2)], lambda urls: [answer(1, 1.99), answer(2, 0, free=True)])
    assert [(r["cost"]["shipping_cents"], r["cost"]["free_shipping"], r["cost"]["total_cents"]) for r in out] == [
        (199, False, 2199), (0, True, 2000)]
    assert stats["fetched"] == 2
    Listing.model_validate(out[0])


def test_the_us_national_rate_is_used_when_it_differs(tmp_path):
    _, out = run(tmp_path, [depop(1)], lambda urls: [answer(1, ship=12.5, national=4.0)])
    assert out[0]["cost"]["shipping_cents"] == 400


def test_answers_are_cached_with_no_seller_identity_and_never_paid_twice(tmp_path):
    calls = []
    def fetch(urls):
        calls.append(len(urls))
        return [answer(1)]
    run(tmp_path, [depop(1)], fetch)
    cached = jsonl.load(tmp_path / "depop_shipping.jsonl")
    assert set(cached[0]) == {"id", "as_of", "shipping_cents", "free_shipping"}
    stats, out = run(tmp_path, [depop(1)], fetch)
    assert calls == [1] and stats["cached"] == 1 and out[0]["cost"]["shipping_cents"] == 199


def test_listings_the_actor_no_longer_finds_are_remembered_as_unknown(tmp_path):
    rows = [depop(i) for i in range(4)]
    found = lambda urls: [answer(i) for i in range(3)]                  # noqa: E731  listing 3 sold since the scrape
    stats, out = run(tmp_path, rows, found)
    assert stats["not_found"] == 1 and out[3]["cost"]["shipping_cents"] is None
    assert run(tmp_path, rows, lambda urls: 1 / 0)[0]["cached"] == 4     # none asked again


def test_only_depop_listings_without_shipping_are_asked_and_chunks_are_capped(tmp_path):
    seen = []
    def fetch(urls):
        seen.append(len(urls))
        return [answer(u.rstrip("/").split("-")[-1]) for u in urls]
    other = depop(9, marketplace="ebay", external_id="9", id="ebay:9", url="https://www.ebay.com/itm/9")
    known = depop(8, cost=dict(price_cents=1000, shipping_cents=500, total_cents=1500))
    stats, _ = run(tmp_path, [depop(i) for i in range(5)] + [other, known], fetch, chunk=2)
    assert seen == [2, 2, 1] and stats["fetched"] == 5 and stats["skipped"] == 2


def test_a_failed_chunk_is_retried_next_run(tmp_path):
    def broken(urls):
        raise RuntimeError("actor failed")
    stats, out = run(tmp_path, [depop(1)], broken)
    assert stats["error"] == 1 and out[0]["cost"]["shipping_cents"] is None
    stats, out = run(tmp_path, [depop(1)], lambda urls: [answer(1)])
    assert stats["fetched"] == 1


def test_chunks_can_run_side_by_side(tmp_path):
    import threading
    import time
    live, peak, lock = [0], [0], threading.Lock()

    def fetch(urls):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.05)
        with lock:
            live[0] -= 1
        return [answer(u.rstrip("/").split("-")[-1]) for u in urls]
    stats, out = run(tmp_path, [depop(i) for i in range(8)], fetch, chunk=2, workers=4)
    assert stats["fetched"] == 8 and peak[0] > 1 and all(r["cost"]["shipping_cents"] == 199 for r in out)
    assert len(jsonl.load(tmp_path / "depop_shipping.jsonl")) == 8


def test_the_actor_is_told_to_return_every_url_it_was_given(monkeypatch):
    # in URL mode the actor stops at maxListings (default 20): 18 chunks of 500 once returned 360 listings in total
    import sys
    import types
    sent = {}

    class Client:
        def __init__(self, token): pass
        def actor(self, name):
            return types.SimpleNamespace(call=lambda run_input, max_total_charge_usd: sent.update(run_input) or
                                         {"status": "SUCCEEDED", "defaultDatasetId": "ds"})
        def dataset(self, ds):
            return types.SimpleNamespace(list_items=lambda: types.SimpleNamespace(items=[]))

    monkeypatch.setitem(sys.modules, "apify_client", types.SimpleNamespace(ApifyClient=Client))
    monkeypatch.setenv("APIFY_TOKEN", "test")
    D.fetch_apify([f"https://www.depop.com/products/s-{i}/" for i in range(500)])
    assert sent["mode"] == "url" and sent["maxListings"] >= 500


def test_a_run_that_returns_under_half_its_urls_is_retried_not_remembered_as_sold(tmp_path):
    stats, _ = run(tmp_path, [depop(i) for i in range(4)], lambda urls: [answer(0)], chunk=4)
    assert stats["error"] == 4 and stats.get("not_found", 0) == 0
    assert not (tmp_path / "depop_shipping.jsonl").exists()
