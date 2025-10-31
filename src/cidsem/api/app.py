import json
import os

import jsonschema
from fastapi import FastAPI, HTTPException, Request

from cidsem.nlp.mapper import map_predicate
from cidsem.nlp.spo import extract_spo
from cidsem.wal import WAL

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Allow override via env var for tests or deployments
SCHEMA_DIR = os.environ.get(
    "CIDSEM_SCHEMA_DIR", os.path.join(ROOT, "docs", "spec", "schemas")
)
CAND_SCHEMA = json.load(open(os.path.join(SCHEMA_DIR, "candidate_factoid.v1.json")))

app = FastAPI(title="cidsem-api", version="0.1")


def get_wal():
    path = os.environ.get("CIDSEM_WAL", os.path.join(os.getcwd(), "data", "wal.log"))
    return WAL(path)


@app.post("/candidate_factoids")
async def post_candidate_factoid(request: Request):
    body = await request.json()
    # idempotency key optional
    key = request.headers.get("Idempotency-Key")
    w = get_wal()
    if key and (found := w.find_by_idempotency_key(key)):
        return {"status": "duplicate", "factoid_id": found.get("factoid_id")}

    # If predicate_candidates missing or empty, attempt to infer from factoid_text
    if not body.get("predicate_candidates"):
        text = body.get("factoid_text", "")
        inferred = []
        for subj, pred, obj in extract_spo(text):
            mapped = map_predicate(pred)
            if mapped:
                p = mapped["predicate"]
                # The ontology may use different field names for the predicate id
                # older versions used 'cid', newer spec uses an 'entity' dict with
                # high/low fields. Normalize to a string predicate_cid for the
                # CandidateFactoid schema (which expects a string).
                # The ontology entry may store the fully-qualified id in 'cid'
                # and the human label in either 'label' or 'content'. Normalize
                # to a string predicate_cid and a human 'label' string.
                pcid = p.get("cid")
                if pcid is None and isinstance(p.get("entity"), dict):
                    try:
                        pcid = json.dumps(p.get("entity"), sort_keys=True)
                    except Exception:
                        pcid = str(p.get("entity"))

                # ensure predicate_cid is a string (schemas expect strings)
                if not isinstance(pcid, str):
                    pcid = str(pcid)

                human_label = p.get("label") or p.get("content") or ""
                # If content is fully-qualified like kind:ns:label, extract human label
                if human_label and ":" in human_label:
                    parts = human_label.split(":", 2)
                    human_label = parts[2] if len(parts) >= 3 else human_label

                inferred.append({
                    "predicate_cid": pcid,
                    "score": mapped.get("score", 1.0),
                    "label": human_label,
                })
        if inferred:
            body["predicate_candidates"] = inferred

    try:
        jsonschema.validate(instance=body, schema=CAND_SCHEMA)
    except jsonschema.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # persist to WAL
    record = {
        "type": "candidate_factoid",
        "factoid_id": body.get("factoid_id"),
        "idempotency_key": key,
        "payload": body,
    }
    w.append(record)

    return {"status": "accepted", "factoid_id": body.get("factoid_id")}


@app.post("/validation_events")
async def post_validation_event(request: Request):
    body = await request.json()
    key = request.headers.get("Idempotency-Key")
    w = get_wal()
    if key and (found := w.find_by_idempotency_key(key)):
        return {"status": "duplicate", "event_id": found.get("event_id")}

    # lazy-load schema for validation events
    try:
        vald_schema = json.load(
            open(os.path.join(SCHEMA_DIR, "validation_event.v1.json"))
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="validation_event schema not found")

    try:
        jsonschema.validate(instance=body, schema=vald_schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = {
        "type": "validation_event",
        "event_id": body.get("event_id"),
        "idempotency_key": key,
        "payload": body,
    }
    w.append(record)

    return {"status": "accepted", "event_id": body.get("event_id")}


@app.post("/backlog_items")
async def post_backlog_item(request: Request):
    body = await request.json()
    key = request.headers.get("Idempotency-Key")
    w = get_wal()
    if key and (found := w.find_by_idempotency_key(key)):
        return {"status": "duplicate", "item_id": found.get("item_id")}

    try:
        backlog_schema = json.load(
            open(os.path.join(SCHEMA_DIR, "backlog_item.v1.json"))
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="backlog_item schema not found")

    try:
        jsonschema.validate(instance=body, schema=backlog_schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = {
        "type": "backlog_item",
        "item_id": body.get("item_id"),
        "idempotency_key": key,
        "payload": body,
    }
    w.append(record)

    return {"status": "accepted", "item_id": body.get("item_id")}
