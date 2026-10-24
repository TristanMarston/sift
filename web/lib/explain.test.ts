import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ecoParts, wearReasons } from './explain.ts';

const fact = (kind: string, value = kind, extra: Record<string, unknown> = {}) => ({ kind, label: kind, value, status: 'claimed', source: 'listing_text', source_url: null, snippet: null, as_of: '2026-10-24', ...extra }) as never;

test('ecoParts groups facts into the four parts of the score, secondhand in none', () => {
    const parts = ecoParts({ level: 'high', score: 0.8, facts: [fact('secondhand'), fact('natural_fibers', '100% cotton'), fact('vintage'), fact('shipping'), fact('durability')] });
    assert.deepEqual(
        parts.map((p) => [p.key, p.weight, p.score, p.facts.map((f) => f.kind)]),
        [
            ['fibers', 0.35, null, ['natural_fibers']],
            ['durability', 0.3, null, ['durability']],
            ['shipping', 0.15, null, ['shipping']],
            ['circularity', 0.2, null, ['vintage']],
        ],
    );
});

test('ecoParts uses the scores and grouping the API sends when it has them', () => {
    const parts = ecoParts({
        level: 'medium',
        score: 0.6,
        parts: [{ key: 'fibers', label: 'Fabric', weight: 0.4, score: 0.5 }],
        facts: [fact('materials', 'cotton', { part: 'fibers' }), fact('secondhand', 'x', { part: null })],
    });
    assert.deepEqual(parts.map((p) => [p.key, p.weight, p.score, p.facts.length]), [['fibers', 0.4, 0.5, 1]]);
});

test('wearReasons explains expected wears from the baseline, quality and condition', () => {
    const r = {
        quality: { level: 'high', score: null, facts: [] },
        wear: { facts: [fact('baseline', '67–167 wears for jackets & outerwear, typically 100'), fact('condition', 'Good: about 80% of its life left (assumption)')] },
    } as never;
    assert.deepEqual(wearReasons(r), [
        { label: 'Typical lifespan', value: '67–167 wears for jackets & outerwear, typically 100' },
        { label: 'Quality', value: 'High: lasts longer than most' },
        { label: 'Condition', value: 'Good: about 80% of its life left (assumption)' },
    ]);
});

test('wearReasons uses the steps the API sends when it has them', () => {
    const steps = [{ label: 'Typical for jackets', value: '100 wears' }];
    assert.deepEqual(wearReasons({ quality: { level: 'low', score: null, facts: [] }, wear: { facts: [], steps } } as never), steps);
});
