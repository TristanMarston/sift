'use client';

import { useSyncExternalStore } from 'react';

/** True while the media query matches, e.g. useMedia('(min-width: 1024px)'). False on the server. */
export function useMedia(query: string) {
    return useSyncExternalStore(
        (cb) => {
            const mq = matchMedia(query);
            mq.addEventListener('change', cb);
            return () => mq.removeEventListener('change', cb);
        },
        () => matchMedia(query).matches,
        () => false,
    );
}
