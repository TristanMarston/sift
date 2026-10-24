// The /search response (schema/API.md §2, the ranker branch's version). Money is integer cents.
// Nullable fields mean "unknown": show them as unknown, never hide them and never show 0.

export type Level = 'high' | 'medium' | 'low' | 'unknown';
export type FactStatus = 'verified' | 'claimed' | 'inferred' | 'unknown';
export type Marketplace = 'depop' | 'poshmark' | 'grailed' | 'mercari' | 'ebay';
export type Condition = 'new_with_tags' | 'like_new' | 'good' | 'fair';
export type Sort = 'cpw' | 'price' | 'match' | 'eco';

export type Fact = {
    kind: string; // open-ended: render any kind with label + value
    label: string;
    value: string;
    status: FactStatus;
    source: string;
    source_url: string | null;
    snippet: string | null;
    as_of: string;
};

export type Marker = { level: Level; score: number | null; facts: Fact[] }; // score is for sorting only, never shown

export type Result = {
    id: string; // "<marketplace>:<external_id>", stable: the React and animation key
    marketplace: Marketplace;
    url: string;
    title: string;
    brand: string | null;
    category: string;
    subcategory: string | null;
    size: string | null;
    color: string | null;
    condition: Condition | null;
    condition_raw: string | null;
    thumb_url: string | null;
    image_urls: string[];
    flags: { is_vintage: boolean; is_deadstock: boolean; is_upcycled: boolean };
    match: { similarity: number; band: 'exact' | 'close' | 'similar' };
    cost: {
        price_cents: number;
        currency: 'USD';
        shipping_cents: number | null;
        free_shipping: boolean | null;
        fee_cents: number; // the marketplace's buyer fee at checkout; Depop's is its stated maximum ("up to")
        total_cents: number;
        original_price_cents: number | null; // the seller's own markdown
        retail_price_cents: number | null; // new retail: show "vs retail" only when known
    };
    materials: {
        fibers: { fiber: string; pct: number | null; organic: boolean | null; recycled: boolean | null }[];
        synthetic_share: number | null;
        certifications: string[];
        composition_suspect: boolean;
    };
    quality: Marker;
    eco: Marker & { percentile: number }; // greener than N% of these matches
    wear: {
        expected_wears: { low: number; high: number; mid: number };
        basis: 'category_baseline' | 'evidence_adjusted';
        cpw_cents: { at_30: number; at_60: number; at_100: number; at_mid: number };
        break_even_wears: number | null; // set only when it costs more than the typical match
        facts: Fact[]; // the assumptions behind expected wears
    };
    confidence: Level;
    seller: { type: 'individual' | 'small_shop' | 'large_reseller' | null; rating: number | null; region: string | null };
};

export type SearchResponse = {
    query: { category?: string | null; filters?: Record<string, unknown> };
    typical: { price_cents: number; expected_wears_mid: number; cpw_cents: number } | null;
    results: Result[];
    orders: Record<Sort, string[]>;
    slider: string[][];
    headline: { cheapest_id: string | null; cheapest_rank_by_cpw: number | null };
    sample?: { prop: string; note: string }; // only on the bundled sample files
};
