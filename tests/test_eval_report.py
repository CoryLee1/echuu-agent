from echuu.eval.pairwise import wilson_interval, win_rate


def test_wilson_basic():
    low, high = wilson_interval(8, 10)
    assert 0.4 < low < 0.8 and 0.6 < high < 1.0
    lo0, hi0 = wilson_interval(0, 0)
    assert lo0 == 0.0 and hi0 == 1.0


def test_win_rate_counts_ties_as_half_win():
    judgments = [
        {"variant_a": "with_dossier", "variant_b": "no_dossier", "winner": "a"},
        {"variant_a": "no_dossier", "variant_b": "with_dossier", "winner": "b"},  # b=with
        {"variant_a": "with_dossier", "variant_b": "no_dossier", "winner": "tie"},
    ]
    r = win_rate(judgments, "with_dossier", "no_dossier")
    assert r["n"] == 3
    assert r["wins_a"] == 2.5
    assert r["ties"] == 1
    assert r["rate"] == 2.5 / 3


def test_win_rate_ignores_malformed_winner():
    judgments = [
        {"variant_a": "with_dossier", "variant_b": "no_dossier", "winner": "a"},
        {"variant_a": "with_dossier", "variant_b": "no_dossier", "winner": "x"},  # malformed, skip
    ]
    r = win_rate(judgments, "with_dossier", "no_dossier")
    assert r["n"] == 1          # malformed row not counted
    assert r["wins_a"] == 1
