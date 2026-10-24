import assert from 'node:assert/strict';
import { test } from 'node:test';
import { bigNumber, cropRect, dots, headline, marketLine, ordered, perWearText, sampleCategory } from './results.ts';

const r = (id: string, extra: Record<string, unknown> = {}) =>
    ({
        id,
        marketplace: 'poshmark',
        size: 'M',
        condition: 'good',
        cost: { total_cents: 4800 },
        match: { similarity: 0.912, band: 'exact' },
        eco: { level: 'medium', score: 0.5, facts: [] },
        wear: { cpw_cents: { at_mid: 30 } },
        ...extra,
    }) as never;

const resp = (rank: number | null) =>
    ({
        results: [r('a'), r('b'), r('c')],
        orders: { cpw: ['c', 'a', 'b'], price: ['a', 'b', 'c'], match: ['b', 'c', 'a'], eco: ['a', 'c', 'b'] },
        headline: { cheapest_id: 'a', cheapest_rank_by_cpw: rank },
    }) as never;

test('ordered shows the results in the order the backend sent for that sort', () => {
    assert.deepEqual(ordered(resp(2), 'cpw').map((x) => x.id), ['c', 'a', 'b']);
    assert.deepEqual(ordered(resp(2), 'match').map((x) => x.id), ['b', 'c', 'a']);
});

test('ordered skips ids it has no result for', () => {
    const x = resp(2) as { orders: { cpw: string[] } };
    x.orders.cpw = ['c', 'zzz', 'a', 'b'];
    assert.deepEqual(ordered(x as never, 'cpw').map((y) => y.id), ['c', 'a', 'b']);
});

test('headline says the cheapest drops only when it falls to #3 or lower', () => {
    assert.deepEqual(headline(resp(14)), { kind: 'drops', rank: 14 });
    assert.deepEqual(headline(resp(3)), { kind: 'drops', rank: 3 });
});

test('headline says so honestly when the cheapest is also the best value per wear', () => {
    assert.deepEqual(headline(resp(1)), { kind: 'best' });
});

test('headline stays quiet at #2 and with no results', () => {
    assert.equal(headline(resp(2)), null);
    assert.equal(headline(resp(null)), null);
});

test('perWearText always shows cents', () => {
    assert.equal(perWearText(30), '$0.30');
    assert.equal(perWearText(4800), '$48.00');
});

test('bigNumber follows the sort', () => {
    assert.deepEqual(bigNumber(r('a'), 'cpw'), { value: '$0.30', unit: '/wear' });
    assert.deepEqual(bigNumber(r('a'), 'price'), { value: '$48', unit: '' });
    assert.deepEqual(bigNumber(r('a'), 'match'), { value: '91%', unit: 'match' });
    assert.deepEqual(bigNumber(r('a'), 'eco'), { value: 'Medium', unit: 'eco' });
    assert.deepEqual(bigNumber(r('a', { eco: { level: 'unknown', score: null, facts: [] } }), 'eco'), { value: 'Unknown', unit: 'eco' });
});

test('dots turn a level into filled dots out of three, never a number', () => {
    assert.deepEqual(['high', 'medium', 'low', 'unknown'].map((l) => dots(l as never)), [3, 2, 1, 0]);
});

test('marketLine reads like a shop tag, and says unknown instead of hiding a missing value', () => {
    assert.equal(marketLine(r('a')), 'Poshmark · M · Good');
    assert.equal(marketLine(r('a', { marketplace: 'ebay', size: null, condition: 'new_with_tags' })), 'eBay · Size unknown · New with tags');
    assert.equal(marketLine(r('a', { condition: null })), 'Poshmark · M · Condition unknown');
});

test('cropRect pads the garment box a little and keeps it inside the photo', () => {
    assert.deepEqual(cropRect({ x: 0.1, y: 0.1, w: 0.5, h: 0.5 }, 1000, 1000), { sx: 60, sy: 60, sw: 580, sh: 580 });
    assert.deepEqual(cropRect({ x: 0, y: 0.7, w: 0.4, h: 0.3 }, 768, 1024), { sx: 0, sy: 676, sw: 338, sh: 348 });
});

test('sampleCategory uses the matching sample, else the jacket demo prop', () => {
    assert.equal(sampleCategory('sneakers'), 'sneakers');
    assert.equal(sampleCategory('sweaters_knitwear'), 'sweaters_knitwear');
    assert.equal(sampleCategory('jeans_pants'), 'jackets_outerwear');
    assert.equal(sampleCategory(''), 'jackets_outerwear');
});
