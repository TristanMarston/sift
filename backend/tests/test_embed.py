import numpy as np
import pytest
from huggingface_hub import try_to_load_from_cache
from PIL import Image, ImageDraw

from backend.embed import DIM, embed_image, embed_images

if not isinstance(try_to_load_from_cache("Marqo/marqo-fashionSigLIP", "open_clip_model.safetensors"), str):
    pytest.skip("FashionSigLIP weights not downloaded yet", allow_module_level=True)


def shirt(color="navy", bg="white", size=384):
    """A crude T-shirt silhouette, so the test needs no binary fixtures."""
    img = Image.new("RGB", (size, size), bg)
    s = size / 100
    ImageDraw.Draw(img).polygon(
        [(30 * s, 15 * s), (70 * s, 15 * s), (95 * s, 35 * s), (80 * s, 45 * s), (72 * s, 38 * s),
         (72 * s, 90 * s), (28 * s, 90 * s), (28 * s, 38 * s), (20 * s, 45 * s), (5 * s, 35 * s)],
        fill=color,
    )
    return img


def noise(seed=0, size=384):
    return Image.fromarray(np.random.default_rng(seed).integers(0, 256, (size, size, 3), dtype=np.uint8))


def test_shape_dtype_unit_norm():
    v = embed_image(shirt())
    assert v.shape == (DIM,) and DIM == 768
    assert v.dtype == np.float32
    assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-4)


def test_batch_matches_singles():
    a, b = shirt(), noise()
    batch = embed_images([a, b], batch_size=1)
    assert batch.shape == (2, DIM)
    np.testing.assert_allclose(batch, np.stack([embed_image(a), embed_image(b)]), atol=1e-4)


def test_deterministic():
    np.testing.assert_array_equal(embed_image(shirt()), embed_image(shirt()))


@pytest.mark.parametrize("mode", ["RGBA", "L"])
def test_accepts_non_rgb(mode):
    assert embed_image(shirt().convert(mode)).shape == (DIM,)


def test_similar_images_are_closer():
    orig = shirt()
    near = orig.crop((10, 10, 374, 374)).resize((300, 300))
    far = noise()
    v, n, f = embed_images([orig, near, far])
    assert v @ n > v @ f


def test_empty():
    assert embed_images([]).shape == (0, DIM)
