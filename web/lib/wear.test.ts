import assert from 'node:assert/strict';
import { test } from 'node:test';
import { breakEven, breakEvenVerdict, byPerWear, byPrice, cheapestDropsTo, perWear, spentAt, timesBought, wearSteps } from './wear.ts';

test('perWear divides price by wears, in whole cents', () => {
    assert.equal(perWear(4000, 100), 40);
    assert.equal(perWear(6500, 200), 33); // 32.5 rounds up
    assert.equal(perWear(900, 20), 45);
});

test('perWear treats zero wears as one, so it never divides by zero', () => {
    assert.equal(perWear(4800, 0), 4800);
});

test('timesBought counts the first purchase before any wear, then one per worn-out copy', () => {
    assert.equal(timesBought(0, 25), 1);
    assert.equal(timesBought(25, 25), 1);
    assert.equal(timesBought(26, 25), 2);
    assert.equal(timesBought(150, 25), 6);
});

test('spentAt is a staircase: price times copies bought', () => {
    assert.equal(spentAt(0, 1200, 25), 1200);
    assert.equal(spentAt(76, 1200, 25), 4800);
    assert.equal(spentAt(150, 4000, 150), 4000);
});

test('breakEven is the first wear where the fragile one has cost more in total', () => {
    assert.equal(breakEven({ cents: 1200, lasts: 25 }, { cents: 4000, lasts: 150 }), 76);
});

test('breakEven is 1 when the fragile one already costs more', () => {
    assert.equal(breakEven({ cents: 5000, lasts: 10 }, { cents: 4000, lasts: 100 }), 1);
});

test('breakEven is null when the sturdy one never wins within the limit', () => {
    assert.equal(breakEven({ cents: 500, lasts: 1000 }, { cents: 4000, lasts: 100 }, 150), null);
});

const tees = [
    { id: 'basic', cents: 900, wears: 20 }, // $0.45
    { id: 'used', cents: 1800, wears: 100 }, // $0.18
    { id: 'crew', cents: 2600, wears: 70 }, // $0.37
    { id: 'heavy', cents: 4000, wears: 150 }, // $0.27
];

test('byPrice sorts cheapest first and leaves the input alone', () => {
    const copy = [...tees];
    assert.deepEqual(byPrice(tees).map((t) => t.id), ['basic', 'used', 'crew', 'heavy']);
    assert.deepEqual(tees, copy);
});

test('byPerWear sorts by cost per wear, unknown wears last', () => {
    const withUnknown = [...tees, { id: 'mystery', cents: 100, wears: null }];
    assert.deepEqual(byPerWear(withUnknown).map((t) => t.id), ['used', 'heavy', 'crew', 'basic', 'mystery']);
});

test('ties break by id so the order never flickers', () => {
    const tied = [
        { id: 'b', cents: 1000, wears: 10 },
        { id: 'a', cents: 1000, wears: 10 },
    ];
    assert.deepEqual(byPrice(tied).map((t) => t.id), ['a', 'b']);
    assert.deepEqual(byPerWear(tied).map((t) => t.id), ['a', 'b']);
});

test('cheapestDropsTo gives the cheapest item’s rank once sorted by cost per wear', () => {
    assert.equal(cheapestDropsTo(tees), 4);
});

test('wearSteps walks from one wear to all of them in readable jumps', () => {
    assert.deepEqual(wearSteps(200), [1, 5, 20, 50, 200]);
    assert.deepEqual(wearSteps(80), [1, 5, 20, 50, 80]);
    assert.deepEqual(wearSteps(50), [1, 5, 20, 50]);
    assert.deepEqual(wearSteps(12), [1, 5, 12]);
    assert.deepEqual(wearSteps(1), [1]);
});

test('breakEvenVerdict: cheaper up front, wins within its expected life, or would need more wears than it lasts', () => {
    assert.equal(breakEvenVerdict(null, 167), 'cheaper');
    assert.equal(breakEvenVerdict(72, 167), 'wins');
    assert.equal(breakEvenVerdict(167, 167), 'wins');
    assert.equal(breakEvenVerdict(2105, 167), 'never');   // a $1,999 jacket vs a typical $45 one
});
