"""A tiny local 'LLM' adapter.

This module provides a stable API used by the mapper when `use_llm=True`.
The default implementation below is deterministic and uses fuzzy matching to
select the best candidate index. It can later be replaced by a wrapper around
an actual local model.
"""

from difflib import SequenceMatcher
from typing import Iterable, Optional

_EMBED_CACHE: dict = {}
_CLASSIFIER_CACHE: dict = {}


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _human_label(p: dict) -> str:
    full_label = p.get("label") or p.get("content") or ""
    parts = full_label.split(":", 2)
    return parts[2] if len(parts) == 3 else full_label


def choose_predicate(phrase: str, predicates: Iterable[dict]) -> Optional[int | dict]:
    """Choose the best predicate from a list.

    Preferred strategy: use a sentence-transformers embedding model (PyTorch)
    to embed ontology human labels and the phrase, then pick the highest
    cosine-similarity candidate. If required libraries are missing, fall
    back to a deterministic fuzzy-matching approach.

    Returns either the selected predicate index or None.
    """
    # Try to use sentence-transformers (PyTorch) for embeddings if available.
    try:
        # Prefer a PyTorch linear classifier trained on top of sentence-transformers
        import numpy as np
        from sentence_transformers import SentenceTransformer

        try:
            import torch
            import torch.nn as nn
        except Exception:
            torch = None

        model_name = "all-MiniLM-L6-v2"
        labels = [_human_label(p) for p in predicates]
        key = (model_name, tuple(labels))

        # If a classifier exists in cache for these labels, use it
        if key in _CLASSIFIER_CACHE and torch is not None:
            clf, lab_emb, model = _CLASSIFIER_CACHE[key]
            # embed phrase
            ph_emb = model.encode([phrase], convert_to_numpy=True)
            ph_emb = ph_emb / (np.linalg.norm(ph_emb, axis=1, keepdims=True) + 1e-12)
            ph = torch.from_numpy(ph_emb).float()
            logits = clf(ph).detach().numpy()[0]
            best_i = int(int(np.argmax(logits)))
            best_score = float(np.max(logits))
            # convert logits to a softmax-like confidence roughly
            probs = np.exp(logits) / np.sum(np.exp(logits))
            if probs[best_i] >= 0.3:
                return best_i
            return None

        # otherwise form embeddings and either train classifier or fall back to kNN
        model = SentenceTransformer(model_name)
        lab_emb = model.encode(labels, convert_to_numpy=True)
        # normalize rows
        norms = np.linalg.norm(lab_emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        lab_emb = lab_emb / norms
        _EMBED_CACHE[key] = lab_emb

        # If torch is available, train a tiny linear classifier on the label embeddings
        if "torch" in globals() and torch is not None:
            X = torch.from_numpy(lab_emb).float()
            y = torch.arange(0, X.shape[0], dtype=torch.long)

            class LinearClf(nn.Module):
                def __init__(self, in_dim, out_dim):
                    super().__init__()
                    self.linear = nn.Linear(in_dim, out_dim)

                def forward(self, x):
                    return self.linear(x)

            clf = LinearClf(X.shape[1], X.shape[0])
            opt = torch.optim.Adam(clf.parameters(), lr=0.05)
            loss_fn = nn.CrossEntropyLoss()
            # train for a small number of epochs; this is cheap for <100 classes
            for epoch in range(200):
                opt.zero_grad()
                logits = clf(X)
                loss = loss_fn(logits, y)
                loss.backward()
                opt.step()

            # cache classifier
            _CLASSIFIER_CACHE[key] = (clf, lab_emb, model)

            # embed phrase and predict
            ph_emb = model.encode([phrase], convert_to_numpy=True)
            ph_emb = ph_emb / (np.linalg.norm(ph_emb, axis=1, keepdims=True) + 1e-12)
            ph = torch.from_numpy(ph_emb).float()
            logits = clf(ph).detach().numpy()[0]
            import numpy as _np

            best_i = int(int(_np.argmax(logits)))
            probs = _np.exp(logits) / _np.sum(_np.exp(logits))
            if probs[best_i] >= 0.3:
                return best_i
            return None

        # fallback kNN via cosine similarity
        ph_emb = model.encode([phrase], convert_to_numpy=True)
        ph_emb = ph_emb / (np.linalg.norm(ph_emb, axis=1, keepdims=True) + 1e-12)
        sims = (lab_emb @ ph_emb[0]).tolist()
        best_i = int(max(range(len(sims)), key=lambda i: sims[i])) if sims else None
        best_score = float(sims[best_i]) if best_i is not None else 0.0
        if best_score >= 0.5:
            return best_i
        return None
    except Exception:
        # fallback to fuzzy matching (deterministic)
        best_i = None
        best_score = 0.0
        phrase_norm = phrase.lower()
        for i, p in enumerate(predicates):
            human = _human_label(p)
            sc = _score(phrase_norm, human.lower())
            if sc > best_score:
                best_score = sc
                best_i = i
        if best_score >= 0.55:
            return best_i
        return None
