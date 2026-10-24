// Sample data for the /design page and the design-system previews.
// Prices, footprints and listings are illustrative only. Real numbers come from intel/ and the footprint table.
import type { Garment, Match, Point, TagReading, ValueId } from './types';

// The sample outfit is drawn in a 300 × 400 box (see sample-outfit.tsx); outlines use the same shapes.
export const OUTFIT_BOX = { w: 300, h: 400 };
export const OUTFIT_SHAPES = {
    coat: [[128, 92], [100, 98], [88, 150], [82, 230], [100, 234], [108, 172], [108, 252], [192, 252], [192, 172], [200, 234], [218, 230], [212, 150], [200, 98], [172, 92], [150, 118]] as Point[],
    jeans: [[110, 250], [190, 250], [194, 352], [158, 354], [150, 292], [142, 354], [106, 352]] as Point[],
    sneakers: [
        [[98, 350], [146, 350], [148, 368], [90, 370], [88, 362]],
        [[154, 350], [202, 350], [212, 362], [210, 370], [152, 368]],
    ] as Point[][],
};

const norm = (pts: Point[]): Point[] => pts.map(([x, y]) => [x / OUTFIT_BOX.w, y / OUTFIT_BOX.h]);
const bboxOf = (polys: Point[][]) => {
    const xs = polys.flat().map((p) => p[0]);
    const ys = polys.flat().map((p) => p[1]);
    const [x, y] = [Math.min(...xs), Math.min(...ys)];
    return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
};
const garment = (id: string, category: string, label: string, color: string, polys: Point[][]): Garment => {
    const outline = polys.map(norm);
    return { id, category, label, attributes: { color }, outline, bbox: bboxOf(outline) };
};

export const garments: Garment[] = [
    garment('g1', 'outerwear', 'Chore coat · navy', 'navy', [OUTFIT_SHAPES.coat]),
    garment('g2', 'bottoms', 'Straight jeans · mid blue', 'mid blue', [OUTFIT_SHAPES.jeans]),
    garment('g3', 'sneakers', 'Sneakers · white', 'white', OUTFIT_SHAPES.sneakers),
];

const coat = (color: string, bg: string) => ({ kind: 'coat' as const, color, bg });

export const coatMatches: Match[] = [
    {
        band: 'exact',
        score: 0.94,
        listing: { id: 'l1', marketplace: 'Depop', url: '#', title: 'Carhartt chore coat', price_cents: 4800, retail_price_cents: 13000, size: 'M', condition: 'Good', category: 'outerwear', art: coat('#34405e', '#e6e1d8'), seller_type: 'individual' },
        reasons: [{ label: 'Same cut', ok: true }, { label: 'Same color', ok: true }, { label: 'Same design', ok: true }],
    },
    {
        band: 'exact',
        score: 0.91,
        listing: { id: 'l2', marketplace: 'Grailed', url: '#', title: 'Carhartt canvas chore coat', price_cents: 6200, size: 'L', condition: 'Very good', category: 'outerwear', art: coat('#2e3852', '#dde3e8') },
        reasons: [{ label: 'Same cut', ok: true }, { label: 'Same color', ok: true }, { label: 'Similar design', ok: true }],
    },
    {
        band: 'similar',
        score: 0.84,
        listing: { id: 'l3', marketplace: 'eBay', url: '#', title: 'French work jacket', price_cents: 5400, size: 'M', condition: 'Worn', category: 'outerwear', art: coat('#2f4a7a', '#ece6dc'), materials: '100% organic cotton' },
        reasons: [{ label: 'Same cut', ok: true }, { label: 'Similar color', ok: true }, { label: 'Organic cotton', ok: true }],
    },
    {
        band: 'similar',
        score: 0.81,
        listing: { id: 'l4', marketplace: 'Poshmark', url: '#', title: 'Dickies chore coat', price_cents: 3500, size: 'M', condition: 'Good', category: 'outerwear', art: coat('#6b4e34', '#e9e4da') },
        reasons: [{ label: 'Same cut', ok: true }, { label: 'Same color', ok: false }],
    },
    {
        band: 'similar',
        score: 0.79,
        listing: { id: 'l5', marketplace: 'Mercari', url: '#', title: 'Utility jacket', price_cents: 2800, size: 'S', condition: 'Good', category: 'outerwear', art: coat('#3a4660', '#e4e7ea') },
        reasons: [{ label: 'Similar cut', ok: true }, { label: 'Same color', ok: true }, { label: 'Same design', ok: false }],
    },
    {
        band: 'similar',
        score: 0.77,
        listing: { id: 'l6', marketplace: 'Depop', url: '#', title: 'Canvas chore coat', price_cents: 7000, size: 'M', condition: 'Like new', category: 'outerwear', art: coat('#56603f', '#e8e5dc'), materials: 'Organic cotton canvas' },
        reasons: [{ label: 'Same cut', ok: true }, { label: 'Same color', ok: false }, { label: 'Organic cotton', ok: true }],
    },
];

// After Update: l2 and l5 move up, l7 is new, l6 drops out.
export const coatMatchesAfterUpdate: Match[] = [
    coatMatches[1],
    coatMatches[0],
    coatMatches[4],
    coatMatches[2],
    {
        band: 'similar',
        score: 0.82,
        listing: { id: 'l7', marketplace: 'Depop', url: '#', title: 'Boxy work jacket', price_cents: 4200, size: 'M', condition: 'Good', category: 'outerwear', art: coat('#7a5a3a', '#ebe5da') },
        reasons: [{ label: 'Boxy fit', ok: true }, { label: 'Earth tone', ok: true }],
    },
    coatMatches[3],
];

export const learned = 'you like boxy fits and earth tones.';

export const tagReading: TagReading = {
    fibers: [
        { name: 'cotton', pct: 50 },
        { name: 'polyester', pct: 50 },
    ],
    country: 'Honduras',
    care: ['Machine wash cold', 'Tumble dry low'],
    footprint_est: { co2_kg: 2.1, water_l: 2700 },
    confidence: 0.92,
};

export const values: { id: ValueId; label: string }[] = [
    { id: 'natural_fibers', label: 'Natural fibers' },
    { id: 'low_carbon', label: 'Low carbon' },
    { id: 'low_toxins', label: 'Low toxins' },
    { id: 'small_seller', label: 'Small seller' },
    { id: 'max_price', label: 'Under $40' },
];

// What the voice parser returns for the demo line, with the words each chip came from.
export const utterance = {
    text: 'Natural fibers, low carbon, low toxins.',
    mapped: [
        { id: 'natural_fibers' as ValueId, phrase: 'Natural fibers' },
        { id: 'low_carbon' as ValueId, phrase: 'low carbon' },
        { id: 'low_toxins' as ValueId, phrase: 'low toxins' },
    ],
};

export const yourShirt = {
    title: 'Gildan tee',
    source: 'From your tag',
    materials: '50% cotton, 50% polyester',
    co2_kg_est: 2.1,
    water_l_est: 2700,
};

export const teePick: Match = {
    band: 'similar',
    score: 0.86,
    listing: { id: 't1', marketplace: 'Depop', url: '#', title: 'Organic cotton tee', price_cents: 1800, retail_price_cents: 3400, size: 'M', condition: 'Very good', category: 'tees', art: { kind: 'tee', color: '#f1eee6', bg: '#d9dfe6' }, seller_type: 'individual' },
    reasons: [{ label: 'Same cut', ok: true }, { label: 'Same color', ok: true }, { label: 'Organic cotton', ok: true }],
    receipt: {
        dollars_saved: 1600,
        co2_saved_kg_est: 2.0,
        water_saved_l_est: 2700,
        materials: '100% organic cotton',
        badges: [
            { value: 'Natural fibers', status: 'verified' },
            { value: 'Low carbon', status: 'verified' },
            { value: 'Small seller', status: 'claimed' },
            { value: 'Low toxins', status: 'unknown' },
        ],
    },
};

export const yourShirtBadges = [
    { value: 'Natural fibers', status: 'unknown' as const, note: '50%' },
    { value: 'Low toxins', status: 'unknown' as const },
];

export const marketplaces = ['Depop', 'Poshmark', 'Grailed', 'Mercari', 'eBay'] as const;
export const INDEX_SIZE = 18432;
