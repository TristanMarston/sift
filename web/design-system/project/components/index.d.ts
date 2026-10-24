// Sift component props. Documentation only; the source lives in /web/components.
import type * as React from 'react';

export type BadgeStatus = 'verified' | 'claimed' | 'unknown';
export type Point = [number, number];

export interface Garment {
    id: string;
    category: string;
    /** "Chore coat · navy" */
    label: string;
    attributes: Record<string, string>;
    /** Fractions (0–1) of the photo. */
    bbox: { x: number; y: number; w: number; h: number };
    crop_url?: string;
    /** Outline points as fractions of the photo; several polygons for split shapes. */
    outline?: Point[] | Point[][];
}

export interface Listing {
    id: string;
    marketplace: 'Depop' | 'Poshmark' | 'Grailed' | 'Mercari' | 'eBay';
    url: string;
    title: string;
    price_cents: number;
    /** Only when the retail price is actually known. */
    retail_price_cents?: number;
    size: string;
    condition: string;
    image_url?: string;
    category: string;
}

export interface Receipt {
    dollars_saved?: number;
    co2_saved_kg_est: number;
    water_saved_l_est: number;
    materials: string;
    badges: { value: string; status: BadgeStatus }[];
}

export interface Match {
    listing: Listing;
    score: number;
    band: 'exact' | 'similar';
    reasons: { label: string; ok: boolean }[];
    receipt?: Receipt;
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link' | 'camera';
    /** sm 36px · default 44px · lg 52px (wraps long labels) · icon 44px · icon-sm 36px */
    size?: 'default' | 'sm' | 'lg' | 'icon' | 'icon-sm' | 'icon-lg';
}

export interface ValueChipProps {
    label: string;
    selected?: boolean;
    /** Added by speech: shows a small mic mark. */
    fromVoice?: boolean;
    /** Shared id so the chip can fly in from the transcript. */
    layoutId?: string;
    onToggle?: () => void;
}

export interface ReasonChipProps {
    label: string;
    ok: boolean;
}

export interface StatusBadgeProps {
    value: string;
    status: BadgeStatus;
    note?: string;
}

export interface HeartButtonProps {
    liked: boolean;
    onToggle?: () => void;
}

export interface UpdateButtonProps {
    count: number;
    onClick?: () => void;
    size?: 'default' | 'sm';
}

export interface MicButtonProps {
    state?: 'idle' | 'listening' | 'processing';
    onPressStart?: () => void;
    /** Under ~250ms is a tap: show "Hold to talk". */
    onPressEnd?: (heldMs: number) => void;
}

export interface ThemeToggleProps {
    className?: string;
}

export interface ListingImageProps {
    src?: string;
    alt: string;
    children?: React.ReactNode;
}

export interface MarketLineProps {
    /** ["Depop", "Size M", "Good"] */
    parts: (string | undefined)[];
}

export interface MatchCardProps {
    match: Match;
    size?: 'large' | 'compact';
    liked?: boolean;
    onLike?: () => void;
    /** Places moved up after Update; the marker fades on its own. */
    moved?: number;
    isNew?: boolean;
}

export interface LearnedLineProps {
    text: string;
}

export interface ScanTraceProps {
    garments: Garment[];
    phase: 'scanning' | 'tracing' | 'done';
    photo?: string;
    children?: React.ReactNode;
    /** Width / height. Default 3:4. */
    aspect?: number;
    selectedId?: string;
    onSelect?: (id: string) => void;
    /** A tap on no garment, as fractions of the photo. */
    onTapEmpty?: (x: number, y: number) => void;
    onTraced?: () => void;
}

export interface CameraBarProps {
    mode?: 'outfit' | 'tag';
    hint?: string;
    /** Leave undefined when the phone can't control the flash. */
    flash?: boolean;
    onFlash?: () => void;
    onClose?: () => void;
    onShutter?: () => void;
    onUpload?: () => void;
    onTypeInstead?: () => void;
}

export interface SearchCounterProps {
    total: number;
    marketplaces: readonly string[];
    /** Set when the search returns; until then the timer runs. */
    elapsedMs?: number;
}

export interface GarmentTabsProps {
    garments: Garment[];
    selectedId: string;
    onSelect?: (id: string) => void;
    photo?: string;
}

export interface VoiceSheetProps {
    phase: 'listening' | 'transcript' | 'mapped';
    transcript?: string;
    mapped?: { id: string; phrase: string; label: string }[];
    onTypeInstead?: () => void;
}

export interface BottomDockProps {
    likedCount: number;
    micState?: 'idle' | 'listening' | 'processing';
    onScanTag?: () => void;
    onMicStart?: () => void;
    onMicEnd?: (heldMs: number) => void;
    onUpdate?: () => void;
}

export interface FiberBarProps {
    fibers: { name: string; pct: number }[];
    uncertain?: string[];
    onFix?: (name: string) => void;
}

export interface FootprintStatProps {
    value: number;
    unit: string;
    label: string;
    size?: 'lg' | 'md';
}

export interface ReceiptSide {
    title: string;
    source: string;
    /** "Owned" when it's yours. */
    price?: string;
    priceNote?: string;
    materials: string;
    co2: number;
    water: number;
    badges: { value: string; status: BadgeStatus; note?: string }[];
}

export interface ImpactReceiptProps {
    yours: ReceiptSide;
    pick: ReceiptSide;
    stamp?: string;
}

export interface QRPanelProps {
    code: string;
}

export interface TopBarProps {
    onBack?: () => void;
    title?: string;
}

export interface NoticeProps {
    icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
    title: string;
    body?: string;
    tone?: 'neutral' | 'error';
    surface?: 'content' | 'camera';
    actions?: React.ReactNode;
}

export interface IntroScreenProps {
    onScan?: () => void;
    onDescribe?: (text: string) => void;
    onUpload?: () => void;
    /** 1s press on the name: load cached results. */
    onSecretHold?: () => void;
}
