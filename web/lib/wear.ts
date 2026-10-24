// Cost-per-wear math for the landing loops. All money is in whole cents.
// Kept free of imports so `node --test` can run it directly.

/** Price divided by wears, rounded to whole cents. */
export const perWear = (cents: number, wears: number) => Math.round(cents / Math.max(1, wears));

/** Copies bought by a given wear: one before the first wear, then a new one each time it wears out. */
export const timesBought = (wear: number, lasts: number) => Math.max(1, Math.ceil(wear / lasts));

/** Total spent by a given wear. A staircase for things that wear out. */
export const spentAt = (wear: number, cents: number, lasts: number) => cents * timesBought(wear, lasts);

type Lasting = { cents: number; lasts: number };

/** First wear where the fragile item has cost more in total than the sturdy one. null if it never does within `max`. */
export function breakEven(fragile: Lasting, sturdy: Lasting, max = 1000) {
    for (let w = 1; w <= max; w++) if (spentAt(w, fragile.cents, fragile.lasts) > spentAt(w, sturdy.cents, sturdy.lasts)) return w;
    return null;
}

type Priced = { id: string; cents: number; wears: number | null };

const byId = (a: Priced, b: Priced) => a.id.localeCompare(b.id);

/** Cheapest first. Ties break by id so the order never flickers. */
export const byPrice = <T extends Priced>(items: T[]) => [...items].sort((a, b) => a.cents - b.cents || byId(a, b));

/** Lowest cost per wear first. Unknown wears go last. */
export const byPerWear = <T extends Priced>(items: T[]) =>
    [...items].sort((a, b) => {
        if (a.wears === null || b.wears === null) return (a.wears === null ? 1 : 0) - (b.wears === null ? 1 : 0) || byId(a, b);
        return perWear(a.cents, a.wears) - perWear(b.cents, b.wears) || byId(a, b);
    });

/** Where the cheapest item lands (1-based) once sorted by cost per wear: "The cheapest drops to #4". */
export const cheapestDropsTo = <T extends Priced>(items: T[]) => byPerWear(items).indexOf(byPrice(items)[0]) + 1;

/** The wear counts the dial stops at: once, a few, many, then all of them. Each stop shows a clearly lower cost per wear. */
export const wearSteps = (wears: number) => [...[1, 5, 20, 50].filter((s) => s < wears), wears];

/** How the receipt words break-even: cheaper than the typical match up front, wins within its expected life,
 *  or would need more wears than it is expected to last (then "wear it N+ times" would be a promise it can't keep). */
export function breakEvenVerdict(breakEvenWears: number | null, expectedHigh: number): 'cheaper' | 'wins' | 'never' {
    if (breakEvenWears === null) return 'cheaper';
    return breakEvenWears <= expectedHigh ? 'wins' : 'never';
}
