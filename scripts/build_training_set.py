from pathlib import Path

from cidsem.build_training_set import build_training_set

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "tests" / "fixtures" / "corpus_texts.json"
OUT = ROOT / "tests" / "fixtures" / "corpus_training.json"

if __name__ == "__main__":
    build_training_set(IN, OUT, use_llm=False)
    print(f"Wrote {OUT}")
