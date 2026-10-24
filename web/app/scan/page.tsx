import type { Metadata, Viewport } from 'next';
import { ScanPage } from './scan-page';

export const metadata: Metadata = { title: 'Sift: scan' };

// The camera is always dark, and so are Safari's bars.
export const viewport: Viewport = { themeColor: '#000000' };

/** Opening /scan directly (a refresh, a shared link, the demo) goes straight to the camera. */
export default function Scan() {
    return <ScanPage />;
}
