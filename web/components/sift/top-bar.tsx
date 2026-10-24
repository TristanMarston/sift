'use client';

import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ThemeToggle } from './theme-toggle';

/** Content-screen header: back (or the name), and the theme toggle. Never on camera screens. */
export function TopBar({ onBack, title = 'Sift', className }: { onBack?: () => void; title?: string; className?: string }) {
    return (
        <header className={cn('sticky top-0 z-10 flex h-14 items-center justify-between bg-background/80 px-2 backdrop-blur-md', className)}>
            {onBack ? (
                <Button variant='ghost' size='sm' onClick={onBack} className='pl-2'>
                    <ChevronLeft data-icon='inline-start' strokeWidth={1.75} />
                    Back
                </Button>
            ) : (
                <span className='px-3 type-wordmark'>{title}</span>
            )}
            <ThemeToggle />
        </header>
    );
}
