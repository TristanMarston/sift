// Frontend shapes, following project.md. Replace with generated types once the contract exists.
// `outline` is the one addition: polygon points as fractions (0–1) of the photo's width and height.

export type Point = [number, number];

export type Garment = {
    id: string;
    category: string;
    label: string; // "Chore coat · navy"
    brand?: string | null; // read off the garment by /detect; passed back to /search
    attributes: Record<string, string>;
    bbox: { x: number; y: number; w: number; h: number }; // fractions of the photo
    crop_url?: string;
    outline?: Point[] | Point[][]; // one polygon, or several for split shapes (a pair of shoes)
};

export type Marketplace = 'Depop' | 'Poshmark' | 'Grailed' | 'Mercari' | 'eBay';

/** Placeholder artwork for sample listings (the real app uses image_url). */
export type Art = { kind: 'coat' | 'jeans' | 'sneaker' | 'tee'; color: string; bg: string };

export type Listing = {
    id: string;
    marketplace: Marketplace;
    url: string;
    title: string;
    price_cents: number;
    retail_price_cents?: number;
    size: string;
    condition: string;
    brand?: string;
    image_url?: string;
    art?: Art;
    category: string;
    materials?: string;
    seller_type?: 'individual' | 'small_shop' | 'large_reseller';
};

export type BadgeStatus = 'verified' | 'claimed' | 'inferred' | 'unknown'; // inferred = "likely"
export type Badge = { value: string; status: BadgeStatus };

export type Receipt = {
    dollars_saved?: number; // cents, only when retail is known
    co2_saved_kg_est: number;
    water_saved_l_est: number;
    materials: string;
    badges: Badge[];
};

export type Match = {
    listing: Listing;
    score: number;
    band: 'exact' | 'close' | 'similar';
    reasons: { label: string; ok: boolean }[];
    receipt?: Receipt;
};

export type FiberClass = 'plant' | 'animal' | 'regenerated' | 'synthetic' | 'unknown';
export type Fiber = { name: string; pct: number };

export type TagReading = {
    fibers: Fiber[];
    country?: string;
    care?: string[];
    footprint_est: { co2_kg: number; water_l: number };
    confidence?: number;
    uncertain?: string[]; // fiber names the model was unsure about
};

export type ValueId = 'natural_fibers' | 'low_carbon' | 'low_toxins' | 'small_seller' | 'max_price';
