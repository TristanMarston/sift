'use client';

import { HeroBillboard } from './hero-billboard';
import { HeroDial } from './hero-dial';
import { HeroEquation } from './hero-equation';
import { HeroFlip } from './hero-flip';
import { HeroRace } from './hero-race';
import { HeroWall } from './hero-wall';
import { LandingShell } from './landing-shell';
import type { Variant } from './variants';

/** Landing designs. The receipt wall is the home page; the rest stay at /landing/<name> for demos (`compare`). */
export function Landing({ variant, compare = false }: { variant: Variant; compare?: boolean }) {
    if (variant === 'dial') return <LandingShell variant='dial' compare={compare} scanButton={false} hero={(open) => <HeroDial onOpen={(el) => open(el, 'circle')} />} />;
    const hero = { flip: <HeroFlip />, race: <HeroRace />, billboard: <HeroBillboard />, equation: <HeroEquation />, wall: <HeroWall /> }[variant];
    return <LandingShell variant={variant} compare={compare} hero={() => hero} />;
}
