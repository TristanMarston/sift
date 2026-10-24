// Sample listings for the landing loops. Illustrative numbers, not real listings: every
// per-wear figure on screen carries an EST. tag. Names are generic so no real brand gets a made-up number.
import type { Marketplace } from '@/lib/types';

export type Condition = 'New with tags' | 'Like new' | 'Good' | 'Fair';

export type Listing = {
    id: string;
    garment: string; // cut-out id in lib/garments.ts
    title: string;
    market: Marketplace;
    condition: Condition;
    cents: number;
    wears: number; // expected wears (the middle of the range)
};

export type FlipSet = { photo: string; label: string; listings: Listing[] };

// Each set is built so the cheapest listing drops to #4 once sorted by cost per wear (see lib/wear.test.ts).
export const flipSets: FlipSet[] = [
    {
        photo: 'tee-wall',
        label: 'Crew-neck tee · white',
        listings: [
            { id: 'basic-tee', garment: 'tee-white', title: 'Basic tee', market: 'Mercari', condition: 'New with tags', cents: 900, wears: 20 },
            { id: 'heavy-tee', garment: 'tee-grey', title: 'Heavyweight tee', market: 'Depop', condition: 'Good', cents: 1800, wears: 100 },
            { id: 'logo-tee', garment: 'tee-black', title: 'Logo tee', market: 'Poshmark', condition: 'Like new', cents: 2600, wears: 70 },
            { id: 'cotton-tee', garment: 'tee-hanger', title: 'Midweight tee', market: 'eBay', condition: 'New with tags', cents: 4000, wears: 150 },
        ],
    },
    {
        photo: 'denim',
        label: 'Trucker jacket · indigo',
        listings: [
            { id: 'washed-trucker', garment: 'denim-side', title: 'Light wash trucker', market: 'Depop', condition: 'Fair', cents: 2400, wears: 60 },
            { id: 'overshirt', garment: 'overshirt', title: 'Work overshirt', market: 'Mercari', condition: 'Like new', cents: 3000, wears: 80 },
            { id: 'trucker', garment: 'denim', title: 'Trucker jacket', market: 'Poshmark', condition: 'Good', cents: 3800, wears: 200 },
            { id: 'raw-denim', garment: 'denim-raw', title: 'Raw denim jacket', market: 'eBay', condition: 'New with tags', cents: 9800, wears: 300 },
        ],
    },
];

export type Racer = { garment: string; title: string; note: string; cents: number; lasts: number };

// Labeled by how long each lasts, never by price: price alone doesn't predict durability.
export const race = {
    wears: 150,
    fragile: { garment: 'tee-plain', title: 'Thin tee', note: 'Pills after ~25 wears', cents: 1200, lasts: 25 } satisfies Racer,
    sturdy: { garment: 'tee-heather', title: 'Heavyweight tee', note: 'Lasts 150+ wears', cents: 4000, lasts: 150 } satisfies Racer,
};

export const dialItems: Listing[] = [
    { id: 'dial-tee', garment: 'tee-hanger', title: 'Midweight tee', market: 'eBay', condition: 'New with tags', cents: 4000, wears: 150 },
    { id: 'dial-trucker', garment: 'denim', title: 'Trucker jacket', market: 'Poshmark', condition: 'Good', cents: 3800, wears: 200 },
    { id: 'dial-overshirt', garment: 'overshirt', title: 'Work overshirt', market: 'Mercari', condition: 'Like new', cents: 3000, wears: 80 },
    { id: 'dial-tweed', garment: 'tweed', title: 'Tweed jacket', market: 'Grailed', condition: 'Good', cents: 6500, wears: 200 },
];

/** `DEPOP · GOOD`, or `EBAY · NEW` for new with tags (the full phrase doesn't fit a phone card). */
export const metaLine = (l: Pick<Listing, 'market' | 'condition'>) => `${l.market} · ${l.condition === 'New with tags' ? 'New' : l.condition}`.toUpperCase();

/** "Midweight tee, new on eBay" or "Trucker jacket, used on Poshmark": where the listing is, in plain words. */
export const listingLine = (l: Pick<Listing, 'title' | 'market' | 'condition'>) => {
    const state = l.condition === 'New with tags' ? 'new' : l.condition === 'Like new' ? 'like new' : 'used';
    return `${l.title}, ${state} on ${l.market}`;
};
