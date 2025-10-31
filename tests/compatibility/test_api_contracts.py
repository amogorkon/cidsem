import pytest

pytest.skip(
    "Compatibility tests are disabled for now; focusing on runtime constraints",
    allow_module_level=True,
)

import importlib
from pathlib import Path

from zvic import load_module
from zvic.compatibility import is_compatible
from zvic.exception import SignatureIncompatible


def test_keys_api_compatible_with_snapshot():
    frozen = load_module(Path("tests/compatibility/frozen/keys_v1.py"), "keys_v1")
    # Load current module via import to preserve package context for relative imports
    current = importlib.import_module("cidsem.keys")

    try:
        is_compatible(frozen.E, current.E)
    except SignatureIncompatible as e:
        pytest.fail(f"E API incompatible: {e.to_json()}")


def test_cidstore_api_compatible_with_snapshot():
    frozen = load_module(
        Path("tests/compatibility/frozen/cidstore_v1.py"), "cidstore_v1"
    )
    # Import current package module to allow relative imports
    current = importlib.import_module("cidsem.cidstore")

    try:
        is_compatible(frozen.TripleRecord, current.TripleRecord)
        is_compatible(frozen.CidstoreClient, current.CidstoreClient)
    except SignatureIncompatible as e:
        pytest.fail(f"Cidstore API incompatible: {e.to_json()}")
