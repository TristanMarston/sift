'use client';

import { MotionConfig } from 'motion/react';

// reducedMotion="user": with Reduce Motion on, Motion drops movement and keeps fades.
export function Providers({ children }: { children: React.ReactNode }) {
    return <MotionConfig reducedMotion='user'>{children}</MotionConfig>;
}
