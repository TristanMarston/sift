import assert from 'node:assert/strict';
import { test } from 'node:test';
import { boxFrom, coverCrop, fitLongEdge } from './photo.ts';

test('coverCrop takes the centered 3:4 slice of a landscape webcam frame', () => {
    assert.deepEqual(coverCrop(1920, 1080, 3 / 4), { sx: 555, sy: 0, sw: 810, sh: 1080 });
});

test('coverCrop takes the centered 3:4 slice of a portrait phone frame', () => {
    assert.deepEqual(coverCrop(1080, 1920, 3 / 4), { sx: 0, sy: 240, sw: 1080, sh: 1440 });
});

test('coverCrop keeps a frame that is already 3:4', () => {
    assert.deepEqual(coverCrop(768, 1024, 3 / 4), { sx: 0, sy: 0, sw: 768, sh: 1024 });
});

test('fitLongEdge scales the long edge down to 1024', () => {
    assert.deepEqual(fitLongEdge(810, 1080), { w: 768, h: 1024 });
    assert.deepEqual(fitLongEdge(4032, 3024), { w: 1024, h: 768 });
});

test('fitLongEdge never scales a small photo up', () => {
    assert.deepEqual(fitLongEdge(600, 400), { w: 600, h: 400 });
});

test('boxFrom turns a drag into a box whichever way it went', () => {
    assert.deepEqual(boxFrom({ x: 0.2, y: 0.3 }, { x: 0.6, y: 0.8 }), { x: 0.2, y: 0.3, w: 0.4, h: 0.5 });
    assert.deepEqual(boxFrom({ x: 0.6, y: 0.8 }, { x: 0.2, y: 0.3 }), { x: 0.2, y: 0.3, w: 0.4, h: 0.5 });
});

test('boxFrom keeps the box inside the photo', () => {
    assert.deepEqual(boxFrom({ x: -0.2, y: 0.5 }, { x: 0.3, y: 1.4 }), { x: 0, y: 0.5, w: 0.3, h: 0.5 });
});
