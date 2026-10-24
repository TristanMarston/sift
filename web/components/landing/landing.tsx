'use client';

import { HeroDial } from './hero-dial';
import { HeroFlip } from './hero-flip';
import { HeroRace } from './hero-race';
import { LandingShell } from './landing-shell';
import type { Variant } from './variants';

/** Landing prototypes: the flip, the break-even race, and the wear dial (its lens is the scan button). */
export function Landing({ variant }: { variant: Variant }) {
    if (variant === 'dial') return <LandingShell variant='dial' scanButton={false} hero={(open) => <HeroDial onOpen={(el) => open(el, 'circle')} />} />;
    const hero = { flip: <HeroFlip />, race: <HeroRace /> }[variant];
    return <LandingShell variant={variant} hero={() => hero} />;
}
