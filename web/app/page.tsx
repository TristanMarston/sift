import type { Viewport } from 'next';
import { Landing } from '@/components/landing/landing';

// Safari's bars match the cobalt stage.
export const viewport: Viewport = { themeColor: '#2b4bf2' };

/** Home: the wear dial landing. Its lens opens the camera. The other prototypes live at /landing/flip and /landing/race. */
export default function Home() {
    return <Landing variant='dial' home />;
}
