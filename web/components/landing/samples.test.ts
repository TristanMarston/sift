import assert from 'node:assert/strict';
import { test } from 'node:test';
import { breakEven, byPerWear, cheapestDropsTo, timesBought } from '../../lib/wear.ts';
import { flipSets, race } from './samples.ts';

const priced = (set: (typeof flipSets)[number]) => set.listings.map((l) => ({ id: l.id, cents: l.cents, wears: l.wears }));

test('every flip set drops its cheapest listing to #4', () => {
    for (const set of flipSets) assert.equal(cheapestDropsTo(priced(set)), 4, set.label);
});

test('a secondhand listing wins every flip set', () => {
    for (const set of flipSets) {
        const best = set.listings.find((l) => l.id === byPerWear(priced(set))[0].id)!;
        assert.notEqual(best.condition, 'New with tags', set.label);
    }
});

test('the race breaks even at 76 wears, with 6 tees bought vs 1', () => {
    assert.equal(breakEven(race.fragile, race.sturdy, race.wears), 76);
    assert.equal(timesBought(race.wears, race.fragile.lasts), 6);
    assert.equal(timesBought(race.wears, race.sturdy.lasts), 1);
});
