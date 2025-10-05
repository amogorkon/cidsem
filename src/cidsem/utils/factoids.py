import re
from typing import Dict, List, Tuple

from cidsem.utils.canonicalize import canonical_cid


def build_factoids(
    input_id: str, text: str, triples: List[Tuple[str, str, str]]
) -> List[Dict]:
    """Build factoid dicts from extracted triples and simple heuristics (dates).

    Factoid ids follow the pattern: <input_id>F## (e.g. X001F01).
    Returns a list of factoid dicts with keys: id, input_id, subject, predicate, object, text.
    Also produces simple secondary factoids for years mentioned in the text, referencing the first
    main factoid ID.
    """
    factoids: List[Dict] = []
    # main factoids from triples
    for i, (subj, pred, obj) in enumerate(triples, start=1):
        fid = f"{input_id}F{i:02d}"
        text_repr = " ".join(filter(None, [subj, pred, obj])).strip()
        f = {
            "id": fid,
            "input_id": input_id,
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "text": text_repr,
        }
        # compute deterministic cid for the factoid
        try:
            f["cid"] = canonical_cid({
                k: f[k] for k in ("input_id", "subject", "predicate", "object", "text")
            })
        except Exception:
            # fallback: omit cid on error
            f["cid"] = ""
        factoids.append(f)

    # secondary factoids: years mentioned in the original text
    years = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
    # de-duplicate while preserving order
    seen = set()
    years_unique = []
    for y in years:
        if y not in seen:
            seen.add(y)
            years_unique.append(y)

    if years_unique and factoids:
        # attach year facts referencing the first main factoid
        main_id = factoids[0]["id"]
        for j, y in enumerate(years_unique, start=1):
            fid = f"{input_id}F{len(factoids) + j:02d}"
            f = {
                "id": fid,
                "input_id": input_id,
                "subject": "",
                "predicate": "happened",
                "object": y,
                "text": f"{main_id} happened {y}",
            }
            try:
                f["cid"] = canonical_cid({
                    k: f[k]
                    for k in ("input_id", "subject", "predicate", "object", "text")
                })
            except Exception:
                f["cid"] = ""
            factoids.append(f)

    return factoids
