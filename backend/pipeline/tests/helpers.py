def row(**over):
    """A minimal valid Listing/Normalized dict."""
    base = dict(
        id="poshmark:64f1a2", marketplace="poshmark", external_id="64f1a2",
        url="https://poshmark.com/listing/64f1a2", title="Carhartt Detroit Jacket",
        status="active", scraped_at="2026-10-24T01:00:00Z", category="jackets_outerwear",
        image_urls=["https://img.example/1.jpg"], cost=dict(price_cents=4800, total_cents=4800),
    )
    return {**base, **over}
