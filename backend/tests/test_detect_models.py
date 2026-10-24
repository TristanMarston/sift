"""The real ONNX detectors end to end. Skipped until the weights are in the Hugging Face cache."""
import json
from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache
from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw

from backend import detect as D

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schema" / "api.schema.json").read_text())


def person():
    """A crude figure: blue top, dark pants, white shoes on grey."""
    im = Image.new("RGB", (384, 512), (200, 200, 200))
    d = ImageDraw.Draw(im)
    d.ellipse((162, 40, 222, 110), fill=(224, 172, 140))
    d.rectangle((130, 110, 254, 280), fill=(40, 70, 160))
    d.rectangle((140, 280, 244, 450), fill=(30, 30, 40))
    d.rectangle((130, 450, 190, 480), fill="white")
    d.rectangle((194, 450, 254, 480), fill="white")
    return im


@pytest.mark.parametrize("backend,weights", [("segformer", D.SEGFORMER), ("yolos", D.YOLOS)])
def test_detect_returns_a_valid_response(backend, weights):
    if not isinstance(try_to_load_from_cache(*weights), str):
        pytest.skip(f"{weights[0]} weights not downloaded yet")
    resp = D.detect(person(), backend=backend, llm=None)
    errors = list(Draft202012Validator({**SCHEMA, "$ref": "#/$defs/DetectResponse"}).iter_errors(resp))
    assert not errors, [e.message for e in errors[:5]]
    assert resp["image"] == {"width": 384, "height": 512}
