from bank.complexity import normalize, equal


def test_normalize_strips_whitespace_and_lowercases():
    assert normalize(" O ( N ) ") == "o(n)"
    assert normalize("O(N LOG N)") == "o(nlogn)"
    assert normalize("O(2^n)") == "o(2^n)"


def test_equal_handles_synonyms():
    assert equal("O(n)", "O ( n )")
    assert equal("O(n log n)", "O(nlogn)")
    assert equal("O(N^2)", "o(n^2)")


def test_unequal():
    assert not equal("O(n)", "O(log n)")
    assert not equal("O(n^2)", "O(n)")


def test_accepts_two_input_forms():
    assert equal("O(m+n)", "o( m + n )")
    assert equal("O(m*n)", "O(mn)")  # m*n and mn treated same


def test_unknown_strings_compared_literally():
    """Not crashing on garbage; just doesn't match anything else."""
    assert not equal("???", "O(n)")
    assert equal("???", "???")
