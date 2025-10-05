import os

HERE = os.path.dirname(__file__)
SPECDIR = os.path.join(HERE, "..", "docs", "specs")

SPEC_FILES = [
    "spec00-intro.md",
    "spec01-data-structures-and-types.md",
    "spec03-system-architecture.md",
    "spec04-components-and-functionality.md",
    "spec05-api-design-and-interfaces.md",
    "spec06-error-handling-and-logging.md",
    "spec07-future-extensions.md",
    "spec08-conclusion.md",
    "spec23-Ontology.md",
]


def test_spec_files_exist():
    missing = []
    for f in SPEC_FILES:
        path = os.path.join(SPECDIR, f)
        if not os.path.isfile(path):
            missing.append(f)
    assert missing == [], f"Missing spec files: {missing}"


def test_spec_headings_present():
    # Check a simple heuristic: each file contains a top-level title (#)
    for f in SPEC_FILES:
        path = os.path.join(SPECDIR, f)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        assert "#" in content, f"Spec {f} seems empty or missing headings"
