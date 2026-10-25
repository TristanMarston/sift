"""Garment colour as one CIELAB point per photo. FashionSigLIP ranks cut and texture above hue, so a green tee's best
matches came back grey: the index keeps a colour per listing (colors.npy, from the same photo the embedding used), and
search takes the query crop's colour to re-rank the shortlist. The reported similarity stays SigLIP's."""
import numpy as np
from PIL import Image

COLOR_WEIGHT = 0.2    # a colour FAR or more away costs this much similarity: a grey tee at 0.83 drops below a green at 0.78
FAR = 40.0            # CIE76 distance that counts as a different colour altogether
# Tuned on 13 phone photos against the 76k index (Oct 24). At 0.12 over 60: 83% of the top 10 shared the query's colour
# and the cheapest pick (what the slider's value end shows first) did in 77% of searches; a black hoodie's value pick was
# light blue. At 0.2 over 40: 95% and 92%, for 0.015 of mean top similarity. Steeper settings gained nothing more.
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_D65 = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lab(rgb) -> np.ndarray:
    """(n, 3) sRGB 0-255 -> (n, 3) CIELAB, D65."""
    c = np.asarray(rgb, np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = c @ _M.T / _D65
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    lab = np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)
    return lab.astype(np.float32)


def garment_color(im: Image.Image) -> np.ndarray:
    """Median Lab of the photo's centre half. White background pixels are dropped unless the centre is mostly white
    (a white garment). NaN when there are no pixels."""
    im = im.convert("RGB")
    w, h = im.size
    px = np.asarray(im.crop((w // 4, h // 4, max(w // 4 + 1, 3 * w // 4), max(h // 4 + 1, 3 * h // 4))), np.float32)
    px = px.reshape(-1, 3)
    if not len(px):
        return np.full(3, np.nan, np.float32)
    lab = srgb_to_lab(px)
    background = (lab[:, 0] > 93) & (np.hypot(lab[:, 1], lab[:, 2]) < 8)
    if background.mean() < 0.8:
        lab = lab[~background]
    return np.median(lab, axis=0).astype(np.float32)


def delta_e(a, b) -> float:
    """CIE76 distance; NaN when either colour is unknown."""
    return float(np.linalg.norm(np.asarray(a, np.float64) - np.asarray(b, np.float64)))


def penalty(colors: np.ndarray, query) -> np.ndarray:
    """Similarity to subtract per row: 0 for the query's colour or an unknown one, COLOR_WEIGHT from FAR away."""
    d = np.linalg.norm(colors.astype(np.float64) - np.asarray(query, np.float64), axis=1)
    return np.where(np.isnan(d), 0.0, COLOR_WEIGHT * np.clip(d / FAR, 0, 1)).astype(np.float32)
