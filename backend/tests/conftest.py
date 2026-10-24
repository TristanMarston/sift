import pytest

from listing import Listing


def make_row(i="1", **over):
    """A listing exactly as step 05 stores it in rows.jsonl (Listing.model_dump(mode="json"))."""
    base = dict(
        id=f"depop:{i}", marketplace="depop", external_id=str(i), url=f"https://www.depop.com/products/{i}/",
        title=f"Item {i}", status="active", scraped_at="2026-10-24T01:00:00Z", category="jackets_outerwear",
        image_urls=[f"https://media-photos.depop.com/b1/1/{i}/P0.jpg"],
        cost=dict(price_cents=4000, total_cents=4000), condition="good",
    )
    base.update(over)
    if "id" not in over and "marketplace" in over:
        base["id"] = f"{over['marketplace']}:{base['external_id']}"
    return Listing(**base).model_dump(mode="json")


@pytest.fixture
def row():
    return make_row


def ev(field, source="listing_text", status="claimed", snippet="", as_of="2026-10-24"):
    return dict(field=field, status=status, source=source, snippet=snippet, as_of=as_of)
