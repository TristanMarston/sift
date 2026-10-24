import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { test } from 'node:test';

const dir = new URL('../public/samples/', import.meta.url);
const files = readdirSync(dir).filter((f) => f.endsWith('.json'));

test('there is a sample for each demo prop', () => {
    assert.deepEqual(files.sort(), ['jackets_outerwear.json', 'sneakers.json', 'sweaters_knitwear.json']);
});

for (const f of files) {
    const resp = JSON.parse(readFileSync(new URL(f, dir), 'utf8'));
    const ids = resp.results.map((r: { id: string }) => r.id).sort();

    test(`${f}: every order and slider stop lists exactly the result ids`, () => {
        for (const order of [...Object.values(resp.orders), ...resp.slider]) assert.deepEqual([...(order as string[])].sort(), ids);
        assert.equal(resp.slider.length, 11);
    });

    test(`${f}: every result has what the screen reads`, () => {
        for (const r of resp.results) {
            assert.ok(r.title && r.url && r.image_urls.length, r.id);
            assert.ok(['high', 'medium', 'low', 'unknown'].includes(r.quality.level), r.id);
            assert.equal(typeof r.wear.cpw_cents.at_mid, 'number', r.id);
            assert.ok(r.wear.facts.length >= 1, r.id);
        }
    });

    test(`${f}: the headline matches the orders`, () => {
        const { cheapest_id, cheapest_rank_by_cpw } = resp.headline;
        assert.equal(cheapest_id, resp.orders.price[0]);
        assert.equal(cheapest_rank_by_cpw, resp.orders.cpw.indexOf(cheapest_id) + 1);
    });
}
