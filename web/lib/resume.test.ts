import assert from 'node:assert/strict';
import { test } from 'node:test';
import { finished, resumed } from './resume.ts';

const resp = (id: string) => ({ results: [{ id }] }) as never;
const g = (id: string) => ({ id, category: '', label: id, attributes: {}, bbox: { x: 0, y: 0, w: 1, h: 1 } });

test('finished keeps only searches that came back', () => {
    const out = finished({ a: { status: 'done', resp: resp('1') }, b: { status: 'loading' }, c: { status: 'error' } });
    assert.deepEqual(Object.keys(out), ['a']);
});

test('resumed shows saved results and searches the rest again', () => {
    const { searches, rerun } = resumed([g('a'), g('b')], { a: resp('1') });
    assert.deepEqual(searches, { a: { status: 'done', resp: resp('1') }, b: { status: 'loading' } });
    assert.deepEqual(rerun, ['b']);
});

test('resumed ignores saved results for garments that are gone', () => {
    const { searches, rerun } = resumed([g('a')], { a: resp('1'), z: resp('9') });
    assert.deepEqual(Object.keys(searches), ['a']);
    assert.deepEqual(rerun, []);
});
