import type { Metadata, Viewport } from 'next';
import { DM_Mono, Figtree, Fraunces } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import { Providers } from '@/components/providers';
import { cn } from '@/lib/utils';

// Serif for big moments, sans for UI, mono for data and receipts.
const fraunces = Fraunces({ subsets: ['latin'], variable: '--font-fraunces', axes: ['opsz', 'SOFT'], style: ['normal', 'italic'] });
const figtree = Figtree({ subsets: ['latin'], variable: '--font-figtree' });
const dmMono = DM_Mono({ subsets: ['latin'], variable: '--font-dm-mono', weight: ['300', '400', '500'] });

export const metadata: Metadata = {
    title: 'Sift: just buy once',
    description: 'Find look-alikes for the clothes you like, ranked by cost per wear.',
};

export const viewport: Viewport = { viewportFit: 'cover', themeColor: '#f5f5f7' };

export default function RootLayout({ children }: LayoutProps<'/'>) {
    return (
        <html lang='en' suppressHydrationWarning className={cn('h-full antialiased', fraunces.variable, figtree.variable, dmMono.variable)}>
            <body className='flex min-h-full flex-col'>
                <Providers>{children}</Providers>
                {/* Saved theme + iOS press states, before hydration. */}
                <Script src='/theme-boot.js' strategy='beforeInteractive' />
            </body>
        </html>
    );
}
