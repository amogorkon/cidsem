"""Convert corpus factoid snippets into triplets mapped to the ontology.

This is a tiny local 'mini-llm' that uses the existing SPO extractor and
heuristics to produce (subject, predicate, object) triplets and attach the
matched ontology predicate and cid. It writes results to
tests/fixtures/corpus_triplets.json.

Run: python scripts/convert_corpus_with_minillm.py
"""

import sys
from pathlib import Path

# ensure package dir (src) is on sys.path so we can import the package when run directly
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cidsem.nlp.spo import extract_spo

CORPUS_IN = ROOT / "tests" / "fixtures" / "corpus_texts.json"
CORPUS_OUT = ROOT / "tests" / "fixtures" / "corpus_triplets.json"


def minimal_llm_to_triplet(snippet: str):
    """Produce a single (subj, pred, obj) from a snippet using extractor + heuristics."""
    triples = extract_spo(snippet)
    if triples:
        return triples[0]

    # fallback heuristics: try simple verb pattern splitting
    s = snippet.strip()
    # try splitting on common verbs
    for verb in (" joined ", " hired ", " left ", " works ", " moved ", " located "):
        if verb in s.lower():
            parts = s.split(verb, 1)
            subj = parts[0].strip().split()[-1] if parts[0].strip() else ""
            obj = parts[1].strip().split(".")[0].strip()
            from cidsem.convert_corpus_with_minillm import convert_corpus

            CORPUS_IN = ROOT / "tests" / "fixtures" / "corpus_texts.json"
            CORPUS_OUT = ROOT / "tests" / "fixtures" / "corpus_triplets.json"

            def main():
                convert_corpus(CORPUS_IN, CORPUS_OUT)
                print(f"Wrote {CORPUS_OUT}")

            if __name__ == "__main__":
                main()
    # predicate is anything between
