import assert from 'node:assert/strict';
import { test } from 'node:test';
import { toGarments, WHOLE_PHOTO } from './detect.ts';

test('no backend answer means the whole photo is one garment', () => {
    assert.deepEqual(toGarments(null), [WHOLE_PHOTO]);
});

test('an empty detection also falls back to the whole photo', () => {
    assert.deepEqual(toGarments({ image: { width: 768, height: 1024 }, garments: [] }), [WHOLE_PHOTO]);
});

test('detected garments map to traceable boxes, most confident first, labels in sentence case', () => {
    const res = {
        image: { width: 768, height: 1024 },
        garments: [
            { id: 'g1', category: 'jeans_pants', label: 'jeans', box: { x: 0.2, y: 0.5, w: 0.5, h: 0.45 }, confidence: 0.7 },
            { id: 'g0', category: 'jackets_outerwear', label: 'jacket', box: { x: 0.12, y: 0.08, w: 0.55, h: 0.7 }, confidence: 0.91 },
        ],
    };
    assert.deepEqual(toGarments(res), [
        { id: 'g0', category: 'jackets_outerwear', label: 'Jacket', attributes: {}, bbox: { x: 0.12, y: 0.08, w: 0.55, h: 0.7 } },
        { id: 'g1', category: 'jeans_pants', label: 'Jeans', attributes: {}, bbox: { x: 0.2, y: 0.5, w: 0.5, h: 0.45 } },
    ]);
});

test('boxes that spill past the photo are clamped to its edges', () => {
    const res = { image: { width: 768, height: 1024 }, garments: [{ id: 'g0', category: 'tshirts', label: 'tee', box: { x: -0.1, y: 0.9, w: 0.5, h: 0.3 }, confidence: 0.8 }] };
    assert.deepEqual(toGarments(res)[0].bbox, { x: 0, y: 0.9, w: 0.4, h: 0.1 });
});

test('a garment the backend could not categorize (null) searches with no category, like the whole photo', () => {
    const res = { image: { width: 768, height: 1024 }, garments: [{ id: 'g0', category: null, label: 'jumpsuit', box: { x: 0.1, y: 0.1, w: 0.5, h: 0.8 }, confidence: 0.9 }] };
    assert.equal(toGarments(res)[0].category, '');
});
