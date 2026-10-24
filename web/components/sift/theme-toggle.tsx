'use client';

import { Moon, Sun } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useSyncExternalStore } from 'react';
import { flushSync } from 'react-dom';
import { Button } from '@/components/ui/button';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

const isDark = () => document.documentElement.classList.contains('dark') || document.documentElement.dataset.theme === 'dark';
const subscribe = (cb: () => void) => {
    const o = new MutationObserver(cb);
    o.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] });
    return () => o.disconnect();
};

/** Light by default. The new theme grows out of the button as a circle; Reduce Motion skips it. */
export function ThemeToggle({ className, onStage }: { className?: string; onStage?: boolean }) {
    const dark = useSyncExternalStore(subscribe, isDark, () => false);

    const toggle = (e: React.MouseEvent<HTMLButtonElement>) => {
        const next = !isDark();
        const apply = () => {
            const root = document.documentElement;
            root.classList.toggle('dark', next);
            root.dataset.theme = next ? 'dark' : 'light';
            try {
                localStorage.setItem('sift-theme', next ? 'dark' : 'light');
            } catch {}
        };
        if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) return apply();

        const r = e.currentTarget.getBoundingClientRect();
        const [x, y] = [r.left + r.width / 2, r.top + r.height / 2];
        const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
        document.startViewTransition(() => flushSync(apply)).ready.then(() =>
            document.documentElement.animate(
                { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
                { duration: 500, easing: 'cubic-bezier(0.2, 0, 0, 1)', pseudoElement: '::view-transition-new(root)' },
            ),
        );
    };

    return (
        <Button variant={onStage ? 'stage-ghost' : 'ghost'} size='icon' onClick={toggle} aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'} className={cn('overflow-hidden', className)}>
            <AnimatePresence mode='wait' initial={false}>
                <motion.span
                    key={dark ? 'moon' : 'sun'}
                    initial={{ rotate: -90, scale: 0.5, opacity: 0 }}
                    animate={{ rotate: 0, scale: 1, opacity: 1 }}
                    exit={{ rotate: 90, scale: 0.5, opacity: 0 }}
                    transition={spring.snappy}
                >
                    {dark ? <Moon strokeWidth={1.75} /> : <Sun strokeWidth={1.75} />}
                </motion.span>
            </AnimatePresence>
        </Button>
    );
}
