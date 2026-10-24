import assert from 'node:assert/strict';
import { test } from 'node:test';
import { apiBases, PROXY } from './endpoints.ts';

test('no backend address means no backend', () => {
    assert.deepEqual(apiBases(undefined, false), []);
    assert.deepEqual(apiBases('', true), []);
});

test('development always goes through the dev server, so phones on wifi and https dev are never blocked', () => {
    assert.deepEqual(apiBases('https://api.example.com', true), [PROXY]);
});

test('production calls the API directly first, then our own site if the browser blocks it', () => {
    assert.deepEqual(apiBases('https://api.example.com/', false), ['https://api.example.com', PROXY]);
});
