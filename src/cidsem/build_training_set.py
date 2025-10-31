"""Build a training dataset from the corpus fixtures.

Produces a JSONL-style file where each line is a JSON object with fields:
- id: factoid id
- text: factoid text
- label: the fully-qualified ontology label (or empty string if unmapped)
- predicate_fq: same as label
- predicate_cid: the predicate cid string if available
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from cidsem.nlp.mapper import map_predicate


def build_training_set(
    in_path: str | Path, out_path: str | Path, use_llm: bool = False
) -> None:
    in_path = Path(in_path)
    out_path = Path(out_path)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    lines: List[dict] = []
    for it in items:
        for exp in it.get("expected", []):
            if not isinstance(exp, dict):
                continue
            txt = exp.get("text", "")
            mp = map_predicate(txt, use_llm=use_llm)
            label = ""
            pcid = None
            if mp:
                p = mp.get("predicate", {})
                fq = p.get("content") or p.get("label") or ""
                label = fq
                pcid = p.get("cid")
                if pcid is not None and not isinstance(pcid, str):
                    pcid = str(pcid)
            lines.append({
                "id": exp.get("id"),
                "text": txt,
                "label": label,
                "predicate_fq": label,
                "predicate_cid": pcid,
            })

    out_path.write_text(
        json.dumps({"items": lines}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("--use-llm", action="store_true")
    args = parser.parse_args()
    build_training_set(args.infile, args.outfile, use_llm=args.use_llm)
