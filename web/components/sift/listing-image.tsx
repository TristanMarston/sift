import type { Art } from '@/lib/types';
import { cn } from '@/lib/utils';

const SHAPES: Record<Art['kind'], string> = {
    coat: '40,22 28,25 23,50 19,88 28,90 33,58 33,102 67,102 67,58 72,90 81,88 77,50 72,25 60,22 50,32',
    tee: '30,30 42,26 50,31 58,26 70,30 84,44 75,53 68,48 68,100 32,100 32,48 25,53 16,44',
    jeans: '33,18 67,18 71,108 54,109 50,52 46,109 29,108',
    sneaker: '12,80 18,64 36,60 50,52 62,54 72,66 88,72 90,84 12,86',
};

/** Flat placeholder art for sample listings. The real app shows listing photos. */
export function GarmentArt({ art, className }: { art: Art; className?: string }) {
    return (
        <svg viewBox='0 0 100 125' className={cn('size-full', className)} aria-hidden>
            <rect width='100' height='125' fill={art.bg} />
            <ellipse cx='50' cy='113' rx='28' ry='3' fill='rgba(0,0,0,0.08)' />
            <polygon points={SHAPES[art.kind]} fill={art.color} stroke='rgba(0,0,0,0.14)' strokeWidth='0.6' strokeLinejoin='round' />
            {art.kind === 'coat' && (
                <g fill='none' stroke='rgba(0,0,0,0.2)' strokeWidth='0.8'>
                    <path d='M50 32v70' />
                    <rect x='37' y='68' width='9' height='8' rx='1' />
                    <rect x='54' y='68' width='9' height='8' rx='1' />
                </g>
            )}
            {art.kind === 'jeans' && <path d='M33 25h34' stroke='rgba(0,0,0,0.2)' strokeWidth='0.8' />}
            {art.kind === 'sneaker' && <path d='M12 80h78' stroke='rgba(0,0,0,0.15)' strokeWidth='4' />}
            {art.kind === 'tee' && <path d='M42 26q8 8 16 0' fill='none' stroke='rgba(0,0,0,0.15)' strokeWidth='0.8' />}
        </svg>
    );
}

/** 4:5 listing photo with a faint inner edge so white photos don't melt into white cards. */
export function ListingImage({ src, art, alt, className, children }: { src?: string; art?: Art; alt: string; className?: string; children?: React.ReactNode }) {
    return (
        <div className={cn('relative aspect-[4/5] overflow-hidden rounded-image bg-muted', className)}>
            {src ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={src} alt={alt} className='size-full object-cover' loading='lazy' />
            ) : art ? (
                <GarmentArt art={art} />
            ) : null}
            <div className='pointer-events-none absolute inset-0 rounded-image ring-1 ring-black/5 ring-inset' />
            {children}
        </div>
    );
}
