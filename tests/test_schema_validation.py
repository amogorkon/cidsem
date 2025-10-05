import json
import os

import pytest

# Skip these tests if jsonschema is not installed
jsonschema = pytest.importorskip("jsonschema")

HERE = os.path.dirname(__file__)
SCHEMAS = os.path.join(HERE, "..", "docs", "spec", "schemas")
FIXTURES = os.path.join(HERE, "fixtures")


def load(name):
    path = os.path.join(SCHEMAS, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_chunk_validates():
    schema = load("chunk.v1.json")
    fixture = json.load(open(os.path.join(FIXTURES, "sample_chunk.json")))
    jsonschema.validate(instance=fixture, schema=schema)


def test_candidate_factoid_validates():
    schema = load("candidate_factoid.v1.json")
    fixture = json.load(open(os.path.join(FIXTURES, "sample_candidate_factoid.json")))
    jsonschema.validate(instance=fixture, schema=schema)
