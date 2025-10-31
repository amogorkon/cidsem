def test_debug_itemX006():
    from cidsem.nlp.spo import extract_spo
    from cidsem.utils.factoids import build_factoids

    text = "Alice moved to San Francisco in 2018. She then joined BetaCorp as CTO and led the engineering team through a major reorg."
    print("\nINPUT TEXT:\n", text)
    triples = extract_spo(text)
    print("\nEXTRACTED TRIPLES:")
    for t in triples:
        print(t)
    factoids = build_factoids("X006", text, triples)
    print("\nFACTOIDS:")
    for f in factoids:
        print(f)
    # debug internal noun/verb detection
    from cidsem.nlp import spo

    print("\nDEBUG NOUNS AND VERBS")
    print("nouns (pos,token):", list(spo._find_nouns(text)))
    verbs = []
    lower = text.lower()
    for pattern, norm in spo._VERB_PATTERNS:
        for m in __import__("re").finditer(__import__("re").escape(pattern), lower):
            verbs.append((m.start(), m.end(), norm, pattern))
    print("verbs (start,end,norm,pattern):", verbs)
    # replicate selection logic for joined verb to inspect why subject became san francisco
    print("\nREPLICATION OF SELECTION LOGIC FOR JOINED:")
    # find joined verb match position
    import re as _re

    lm = _re.search("joined", text.lower())
    if lm:
        vstart = lm.start()
        vend = lm.end()
        print("vstart, vend for joined:", vstart, vend)
        # noun_matches absolute
        noun_matches_abs = list(spo._find_nouns(text))
        print("noun_matches_abs:", noun_matches_abs)
        candidates = [
            (st, g) for (st, g) in noun_matches_abs if st < vstart and len(g) > 1
        ]
        print("candidates before pronoun handling:", candidates)
        subject = ""
        subject_start = -1
        if candidates:
            subject_start, subject = sorted(candidates, key=lambda x: x[0])[-1]
        print("initial chosen subject:", subject_start, subject)
        pronouns = {"he", "she", "they", "we", "i", "you", "it", "his", "her"}
        if subject and subject.strip().lower() in pronouns:
            prior = [
                p
                for p in noun_matches_abs
                if p[0] < vstart and p[1].strip().lower() not in pronouns
            ]
            print("prior candidates for pronoun resolution:", prior)
            if prior:

                def score_candidate(p):
                    pos, tok = p
                    is_single = 0 if " " not in tok.strip() else 1
                    return (is_single, vstart - pos)

                chosen = min(prior, key=score_candidate)
                print("chosen after scoring:", chosen)
            else:
                print("no prior, fallback to last context noun", noun_matches_abs[-1])
    assert True
