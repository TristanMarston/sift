import { OUTFIT_SHAPES } from '@/lib/sample-data';
import type { Point } from '@/lib/types';
import { cn } from '@/lib/utils';

const pts = (p: Point[]) => p.map((q) => q.join(',')).join(' ');
const SKIN = '#b48f73';

/** The sample outfit's shapes in a 300 × 400 box. Stands in for a camera photo. */
export function OutfitShapes() {
    return (
        <g>
            <rect width='300' height='400' fill='#d6d1c7' />
            <rect y='330' width='300' height='70' fill='#c4bdb0' />
            <ellipse cx='150' cy='372' rx='72' ry='7' fill='rgba(0,0,0,0.12)' />
            <polygon points={pts(OUTFIT_SHAPES.jeans)} fill='#56719b' />
            <path d='M150 292v-40' stroke='rgba(0,0,0,0.18)' strokeWidth='1.2' />
            {OUTFIT_SHAPES.sneakers.map((s, i) => (
                <polygon key={i} points={pts(s)} fill='#f3f2ee' stroke='#cfcdc6' strokeWidth='1' strokeLinejoin='round' />
            ))}
            <rect x='141' y='78' width='18' height='18' fill={SKIN} />
            <polygon points={pts(OUTFIT_SHAPES.coat)} fill='#34405e' />
            <polygon points='128,92 172,92 150,118' fill='#efece5' />
            <g fill='none' stroke='rgba(0,0,0,0.25)' strokeWidth='1.2'>
                <path d='M150 118v134' />
                <rect x='118' y='186' width='22' height='18' rx='2' />
                <rect x='160' y='186' width='22' height='18' rx='2' />
            </g>
            <circle cx='150' cy='58' r='24' fill={SKIN} />
            <path d='M126 56q2-30 24-30t24 30q-6-14-24-14t-24 14z' fill='#3b2f28' />
            <circle cx='91' cy='242' r='8' fill={SKIN} />
            <circle cx='209' cy='242' r='8' fill={SKIN} />
        </g>
    );
}

/** Full sample photo, cropped to fill its box like a camera frame. */
export function SampleOutfit({ className }: { className?: string }) {
    return (
        <svg viewBox='0 0 300 400' preserveAspectRatio='xMidYMid slice' role='img' aria-label='Sample outfit photo' className={cn('size-full', className)}>
            <OutfitShapes />
        </svg>
    );
}
