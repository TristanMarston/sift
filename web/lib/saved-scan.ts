// The latest scan in this browser's IndexedDB, so a refresh keeps the results. Nothing leaves the device.
// Every call fails quietly: private windows and blocked storage just mean no restore.
import type { SavedScan } from './resume';

const DB = 'sift';
const STORE = 'scan';
const KEY = 'latest';

function open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(STORE);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function run<T>(mode: IDBTransactionMode, act: (s: IDBObjectStore) => IDBRequest<T>): Promise<T | null> {
    try {
        const db = await open();
        return await new Promise<T>((resolve, reject) => {
            const req = act(db.transaction(STORE, mode).objectStore(STORE));
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        }).finally(() => db.close());
    } catch {
        return null;
    }
}

export const saveScan = (scan: SavedScan) => run('readwrite', (s) => s.put(scan, KEY));
export const loadScan = () => run<SavedScan | undefined>('readonly', (s) => s.get(KEY)).then((v) => v ?? null);
export const clearScan = () => run('readwrite', (s) => s.delete(KEY));

/** True when this page load is a refresh, not a fresh visit or a shared link. */
export const isReload = () => (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.type === 'reload';
