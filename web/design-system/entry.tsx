// Design-system bundle entry. Everything exported here becomes window.Sift.<Name>.
// Exports above the Helpers block are documented components (each has a card on the design-system page).
import { CameraOff, SearchX, Shirt, Tag } from 'lucide-react';

export { Button } from '@/components/ui/button';
export { ValueChip } from '@/components/sift/value-chip';
export { ReasonChip } from '@/components/sift/reason-chip';
export { StatusBadge } from '@/components/sift/status-badge';
export { HeartButton } from '@/components/sift/heart-button';
export { UpdateButton } from '@/components/sift/update-button';
export { MicButton } from '@/components/sift/mic-button';
export { ThemeToggle } from '@/components/sift/theme-toggle';
export { ListingImage } from '@/components/sift/listing-image';
export { MarketLine } from '@/components/sift/market-line';
export { MatchCard } from '@/components/sift/match-card';
export { LearnedLine } from '@/components/sift/learned-line';
export { ScanTrace } from '@/components/sift/scan-trace';
export { CameraBar } from '@/components/sift/camera-controls';
export { SearchCounter } from '@/components/sift/search-counter';
export { GarmentTabs } from '@/components/sift/garment-tabs';
export { VoiceSheet } from '@/components/sift/voice-sheet';
export { BottomDock } from '@/components/sift/bottom-dock';
export { FiberBar } from '@/components/sift/fiber-bar';
export { FootprintStat } from '@/components/sift/footprint-stat';
export { ImpactReceipt } from '@/components/sift/impact-receipt';
export { QRPanel } from '@/components/sift/qr-panel';
export { TopBar } from '@/components/sift/top-bar';
export { Notice } from '@/components/sift/notice';
export { IntroScreen } from '@/components/sift/intro-screen';

// Helpers (in the bundle, no card of their own)
export { StatusDot, EstTag } from '@/components/sift/status-badge';
export { PriceLine } from '@/components/sift/market-line';
export { GarmentArt } from '@/components/sift/listing-image';
export { MatchCardSkeleton, ReceiptSummary } from '@/components/sift/match-card';
export { Shutter, TagFrame } from '@/components/sift/camera-controls';
export { RollingNumber } from '@/components/sift/rolling-number';
export { GarmentCutout } from '@/components/sift/garment-tabs';
export { Waveform } from '@/components/sift/voice-sheet';
export { SampleOutfit, OutfitShapes } from '@/components/sift/sample-outfit';
export { Skeleton } from '@/components/ui/skeleton';
export { spring, ease, trace } from '@/lib/motion';
export * as format from '@/lib/format';
export * as samples from '@/lib/sample-data';
export const icons = { CameraOff, SearchX, Shirt, Tag };
