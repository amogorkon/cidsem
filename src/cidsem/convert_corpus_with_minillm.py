"""Minimal corpus converter that maps factoid snippets to ontology triplets.

Provides a programmatic API `convert_corpus(in_path, out_path)` and a small
CLI entrypoint. Reuses existing extractor and mapper from the package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from cidsem.nlp.mapper import map_predicate
from cidsem.nlp.spo import extract_spo


def minimal_llm_to_triplet(snippet: str) -> Tuple[str, str, str]:
    """Produce a single (subj, pred, obj) from a snippet using extractor + heuristics.

    This mirrors the logic used in the scripts converter but is packaged for tests.
    """
    triples = extract_spo(snippet)
    if triples:
        return triples[0]

    s = snippet.strip()
    for verb in (" joined ", " hired ", " left ", " works ", " moved ", " located "):
        if verb in s.lower():
            parts = s.split(verb, 1)
            subj = parts[0].strip().split()[-1] if parts[0].strip() else ""
            obj = parts[1].strip().split(".")[0].strip()
            pred = verb.strip()
            return (subj.lower(), pred.lower(), obj.lower())

    words = s.split()
    caps = [w for w in words if w and w[0].isupper()]
    subj = caps[0].lower() if caps else words[0].lower() if words else ""
    obj = (
        caps[-1].lower()
        if len(caps) > 1
        else (words[-1].strip(".").lower() if words else "")
    )
    try:
        start = words.index(caps[0]) + 1 if caps else 1
        end = words.index(caps[-1]) if len(caps) > 1 else len(words) - 1
        pred = " ".join(words[start:end]).strip().lower()
    except Exception:
        pred = ""
    return (subj, pred, obj)


def map_to_ontology(
    pred_phrase: str, use_llm: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    mapped = map_predicate(pred_phrase, use_llm=use_llm)
    if not mapped:
        return None, None
    p = mapped["predicate"]
    fq = p.get("content") or p.get("label") or ""
    pcid = p.get("cid")
    if pcid is None and isinstance(p.get("entity"), dict):
        try:
            pcid = json.dumps(p.get("entity"), sort_keys=True)
        except Exception:
            pcid = str(p.get("entity"))
    if pcid is not None and not isinstance(pcid, str):
        pcid = str(pcid)
    return fq, pcid


def convert_corpus(
    in_path: str | Path, out_path: str | Path, use_llm: bool = False
) -> None:
    in_path = Path(in_path)
    out_path = Path(out_path)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    out = {"items": []}
    for it in items:
        new_it = dict(it)
        exps = it.get("expected", [])
        triplets = []
        for exp in exps:
            if isinstance(exp, dict):
                txt = exp.get("text", "")
                subj, pred, obj = minimal_llm_to_triplet(txt)
                # request the mapper to use the local LLM when enabled
                fq, pcid = map_to_ontology(pred, use_llm=use_llm)
                trip = {
                    "id": exp.get("id"),
                    "text": txt,
                    "subject": subj,
                    "predicate_phrase": pred,
                    "predicate_fq": fq,
                    "predicate_cid": pcid,
                    "object": obj,
                }
                triplets.append(trip)
        new_it["triplets"] = triplets
        out["items"].append(new_it)

    out_path.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="Input corpus JSON")
    parser.add_argument("outfile", help="Output triplet JSON")
    args = parser.parse_args()
    convert_corpus(args.infile, args.outfile)


if __name__ == "__main__":
    main()
