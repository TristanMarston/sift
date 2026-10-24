import type { Viewport } from 'next';
import { Landing } from '@/components/landing/landing';

// Safari's bars match the forest landing.
export const viewport: Viewport = { themeColor: '#103520' };

/** Home: the receipt wall on forest. The other landing designs live at /landing/<name> for demos. */
export default function Home() {
    return <Landing variant='wall' />;
}
