import assert from 'node:assert/strict';
import { test } from 'node:test';
import { shake } from './shake.ts';

const r = (id: string, total: number, mid: number) =>
    ({ id, cost: { total_cents: total }, wear: { expected_wears: { low: mid - 10, high: mid + 10, mid }, cpw_cents: { at_30: 0, at_60: 0, at_100: 0, at_mid: Math.round(total / mid) } } }) as never;

// The cheapest ("a") is also the best value per wear, the case that hides the slider.
const resp = () =>
    ({
        results: [r('a', 1000, 60), r('b', 3000, 60), r('c', 5000, 60), r('d', 8000, 60)],
        orders: { cpw: ['a', 'b', 'c', 'd'], price: ['a', 'b', 'c', 'd'], match: ['d', 'c', 'b', 'a'], eco: ['b', 'a', 'd', 'c'] },
        slider: [],
        headline: { cheapest_id: 'a', cheapest_rank_by_cpw: 1 },
    }) as never;

type R = { id: string; cost: { total_cents: number }; wear: { expected_wears: { mid: number }; cpw_cents: { at_mid: number } } };
type S = { results: R[]; orders: Record<string, string[]>; slider: string[][]; headline: { cheapest_id: string; cheapest_rank_by_cpw: number } };

test('shake knocks the cheapest off #1 by cost per wear, and the headline agrees', () => {
    const s = shake(resp()) as unknown as S;
    assert.ok(s.headline.cheapest_rank_by_cpw > 1);
    assert.equal(s.orders.cpw.indexOf('a') + 1, s.headline.cheapest_rank_by_cpw);
});

test('cost per wear is price over the new wears, and orders.cpw sorts by it', () => {
    const s = shake(resp()) as unknown as S;
    for (const x of s.results) assert.equal(x.wear.cpw_cents.at_mid, Math.round(x.cost.total_cents / x.wear.expected_wears.mid));
    const byId = new Map(s.results.map((x) => [x.id, x.wear.cpw_cents.at_mid]));
    const cpws = s.orders.cpw.map((id) => byId.get(id)!);
    assert.deepEqual(cpws, [...cpws].sort((p, q) => p - q));
});

test('slider runs from the cpw order to the match order, every stop a full list', () => {
    const s = shake(resp()) as unknown as S;
    assert.equal(s.slider.length, 11);
    assert.deepEqual(s.slider[0], s.orders.cpw);
    assert.deepEqual(s.slider[10], s.orders.match);
    for (const stop of s.slider) assert.deepEqual([...stop].sort(), ['a', 'b', 'c', 'd']);
});

test('shake leaves price, match and eco orders alone and does not touch the input', () => {
    const before = resp();
    const copy = structuredClone(before);
    const s = shake(before) as unknown as S;
    assert.deepEqual(before, copy);
    assert.deepEqual(s.orders.price, ['a', 'b', 'c', 'd']);
    assert.deepEqual(s.orders.match, ['d', 'c', 'b', 'a']);
    assert.deepEqual(s.orders.eco, ['b', 'a', 'd', 'c']);
});
