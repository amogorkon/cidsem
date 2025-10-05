import json
import sys
from pathlib import Path

# Ensure package imports work (src layout)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cidsem.nlp.spo import extract_spo
from cidsem.utils.factoids import build_factoids

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "tests" / "fixtures" / "corpus_texts.json"


def main():
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    items = data.get("items", [])
    changed = False
    for it in items:
        text = it.get("text", "")
        triples = extract_spo(text)
        factoids = build_factoids(it.get("id"), text, triples)
        # for each expected dict, attempt to find matching factoid and attach cid
        exps = it.get("expected", [])
        for exp in exps:
            if isinstance(exp, dict):
                exp_text = exp.get("text", "")
                # find first factoid whose text contains exp_text
                match = None
                for f in factoids:
                    if exp_text and exp_text in (f.get("text") or ""):
                        match = f
                        break
                if match:
                    if exp.get("cid") != match.get("cid"):
                        exp["cid"] = match.get("cid")
                        changed = True

    if changed:
        CORPUS_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("Updated corpus with CIDs.")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
