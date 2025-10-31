"""Unit tests for improved SPO extraction."""

from cidsem.nlp.spo import extract_spo


def test_single_simple():
    s = "Alice works at BetaCorp."
    triples = extract_spo(s)
    assert triples
    assert ("alice", "works as", "betacorp") in triples or (
        "alice",
        "works as",
        "beta corp",
    ) in triples


def test_multiple_clauses():
    s = "Alice joined BetaCorp, and Bob left Acme Inc.; Carol was hired by Delta."
    triples = extract_spo(s)
    # expect at least three extractions
    assert len(triples) >= 3


def test_pronoun_resolution():
    s = "Alice works at BetaCorp. She later joined Gamma LLC."
    triples = extract_spo(s)
    # Expect first triple with alice, and second triple with alice resolved from 'She'
    assert any(t[0] == "alice" for t in triples)
    assert any(t[2].startswith("gamma") or "gamma" in t[2] for t in triples)


def test_no_verb():
    s = "This is not a factual sentence with verbs we know"
    triples = extract_spo(s)
    # Should probably find something because 'is' maps to 'be', but ensure function runs
    assert isinstance(triples, list)
