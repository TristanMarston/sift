// Which look the quality and eco markers use. Picked on /design/markers and kept in this browser, so the team can
// compare the variations in a real scan before one becomes the default.
import { useSyncExternalStore } from 'react';

export const MARKER_STYLES = ['dots', 'meter', 'chips', 'rings'] as const;
export type MarkerStyle = (typeof MARKER_STYLES)[number];

export const DEFAULT_MARKER_STYLE: MarkerStyle = 'rings'; // picked by the team on /design/markers
const KEY = 'sift-markers';
const EVENT = 'sift-markers';

function read(): MarkerStyle {
    try {
        const v = localStorage.getItem(KEY);
        return MARKER_STYLES.includes(v as MarkerStyle) ? (v as MarkerStyle) : DEFAULT_MARKER_STYLE;
    } catch {
        return DEFAULT_MARKER_STYLE;
    }
}

function subscribe(cb: () => void) {
    window.addEventListener('storage', cb);
    window.addEventListener(EVENT, cb);
    return () => {
        window.removeEventListener('storage', cb);
        window.removeEventListener(EVENT, cb);
    };
}

export const useMarkerStyle = () => useSyncExternalStore(subscribe, read, () => DEFAULT_MARKER_STYLE);

export function setMarkerStyle(style: MarkerStyle) {
    try {
        localStorage.setItem(KEY, style);
    } catch {}
    window.dispatchEvent(new Event(EVENT));
}
