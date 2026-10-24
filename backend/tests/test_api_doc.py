"""The JSON examples in schema/API.md must stay valid against schema/api.schema.json."""
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2] / "schema"
SCHEMA = json.loads((ROOT / "api.schema.json").read_text())
BLOCKS = [b for b in re.findall(r"```json\n(.*?)```", (ROOT / "API.md").read_text(), re.S) if "/*" not in b]


def errors(defn, obj):
    return [e.message for e in Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{defn}"}).iter_errors(obj)]


def example(marker):
    return json.loads(next(b for b in BLOCKS if marker in b))


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_detect_example():
    assert errors("DetectResponse", example('"garments"')) == []


def test_search_params_example():
    assert errors("SearchParams", example('"max_price_cents"')) == []


def test_result_example():
    assert errors("Result", example('"marketplace"')) == []
