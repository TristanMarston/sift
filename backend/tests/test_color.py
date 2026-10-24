"""Garment colour: one CIELAB point per photo, so a green tee is not out-ranked by a grey one of the same cut."""
import numpy as np
from PIL import Image

from backend import color as C


def flat(rgb, size=(64, 64)):
    return Image.new("RGB", size, rgb)


def test_srgb_to_lab_matches_reference_values():
    lab = C.srgb_to_lab(np.array([[255, 255, 255], [0, 0, 0], [255, 0, 0], [0, 128, 0]], np.float32))
    assert np.allclose(lab[0], [100, 0, 0], atol=0.5)
    assert np.allclose(lab[1], [0, 0, 0], atol=0.5)
    assert np.allclose(lab[2], [53.2, 80.1, 67.2], atol=1)       # sRGB red
    assert np.allclose(lab[3], [46.2, -51.7, 49.9], atol=1)      # sRGB green (0,128,0)


def test_garment_color_is_the_median_of_the_centre_not_the_background():
    im = flat((255, 255, 255), (100, 100))                        # product shot on white...
    im.paste(flat((20, 90, 40), (50, 60)), (25, 20))               # ...with a green garment in the middle
    lab = C.garment_color(im)
    assert np.allclose(lab, C.srgb_to_lab(np.array([[20, 90, 40]], np.float32))[0], atol=1)


def test_garment_color_keeps_white_garments_when_there_is_nothing_else():
    assert C.garment_color(flat((250, 250, 250)))[0] > 95


def test_delta_e_is_zero_for_the_same_colour_and_large_across_hues():
    green, grey, dark_green = (C.garment_color(flat(c)) for c in [(20, 90, 40), (128, 128, 128), (15, 70, 30)])
    assert C.delta_e(green, green) == 0
    assert C.delta_e(green, dark_green) < 15 < C.delta_e(green, grey)
    assert np.isnan(C.delta_e(green, np.array([np.nan] * 3)))      # unknown colour: no opinion
