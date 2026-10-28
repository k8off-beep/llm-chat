import pytest
from app.submatrix import find_submatrices, SubmatrixValidationError


def test_control_example():
    result = find_submatrices(["A1A1", "B2B2", "A1A1", "B2B2"], ["A1", "B2"])

    assert result["count"] == 4
    assert result["pattern_size"] == 2
    assert result["matches"] == [
        {"row": 0, "column": 0},
        {"row": 0, "column": 2},
        {"row": 2, "column": 0},
        {"row": 2, "column": 2},
    ]


def test_single_match():
    result = find_submatrices(["A1A", "B2B", "A1A"], ["A1", "B2"])

    assert result["count"] == 1
    assert result["pattern_size"] == 2
    assert result["matches"] == [{"row": 0, "column": 0}]


def test_overlapping_matches():
    result = find_submatrices(["AAA", "AAA", "AAA"], ["AA", "AA"])

    assert result["count"] == 4
    assert result["pattern_size"] == 2
    assert result["matches"] == [
        {"row": 0, "column": 0},
        {"row": 0, "column": 1},
        {"row": 1, "column": 0},
        {"row": 1, "column": 1},
    ]


def test_no_matches():
    result = find_submatrices(["A1A", "B2B", "A1A"], ["C3", "D4"])

    assert result["count"] == 0
    assert result["pattern_size"] == 2
    assert result["matches"] == []


def test_pattern_1x1():
    result = find_submatrices(["A1A", "B2B", "A1A"], ["A"])

    assert result["count"] == 4
    assert result["pattern_size"] == 1
    assert result["matches"] == [
        {"row": 0, "column": 0},
        {"row": 0, "column": 2},
        {"row": 2, "column": 0},
        {"row": 2, "column": 2},
    ]


def test_pattern_equals_matrix():
    result = find_submatrices(["AA", "BB"], ["AA", "BB"])

    assert result["count"] == 1
    assert result["pattern_size"] == 2
    assert result["matches"] == [{"row": 0, "column": 0}]


def test_rectangular_matrix():
    result = find_submatrices(["ABAB", "CDCD"], ["AB", "CD"])

    assert result["count"] == 2
    assert result["pattern_size"] == 2
    assert result["matches"] == [
        {"row": 0, "column": 0},
        {"row": 0, "column": 2},
    ]


def test_lowercase_is_normalized():
    result = find_submatrices(["ab", "cd"], ["AB", "CD"])

    assert result["matrix"] == ["AB", "CD"]
    assert result["count"] == 1
    assert result["pattern_size"] == 2
    assert result["matches"] == [{"row": 0, "column": 0}]


def test_result_fields():
    result = find_submatrices(["aB", "Cd", "EE"], ["cD", "ee"])

    assert result["matrix"] == ["AB", "CD", "EE"]
    assert result["pattern"] == ["CD", "EE"]
    assert result["count"] == 1
    assert result["pattern_size"] == 2
    assert result["matches"] == [{"row": 1, "column": 0}]


def test_pattern_larger_than_matrix():
    result = find_submatrices(["A1A", "B2B"], ["A1A", "B2B", "C3C"])

    assert result["count"] == 0
    assert result["matches"] == []


def test_pattern_too_tall_for_matrix():
    result = find_submatrices(["ABCDE", "12345"], ["ABA", "CDA", "EFA"])

    assert result["count"] == 0
    assert result["matches"] == []


def test_only_first_row_matches():
    result = find_submatrices(["A1", "C3"], ["A1", "B2"])

    assert result["count"] == 0
    assert result["matches"] == []


def test_matrix_is_none():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(None, ["A1", "B2"])


def test_num_in_matrix():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", 123], ["A1", "B2"])


def test_not_a_list_matrix():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices("A1A", ["A1", "B2"])


def test_not_a_list_pattern():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B"], "A1")


def test_invalid_char_in_matrix():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3G"], ["A1", "B2"])


def test_invalid_char_in_pattern():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3C"], ["A1", "Z4"])


def test_rows_different_length():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3"], ["A1", "B2"])


def test_pattern_not_square():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3C"], ["A1", "B2", "C3", "D4"])


def test_empty_matrix():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices([], ["A1", "B2"])


def test_empty_pattern():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3C"], [])


def test_matrix_too_many_rows():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A"] * 9, ["A1", "B2"])


def test_matrix_too_many_columns():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A1A1A1A1"] * 3, ["A1", "B2"])


def test_pattern_too_big():
    with pytest.raises(SubmatrixValidationError):
        find_submatrices(["A1A", "B2B", "C3C"], ["A" * 9] * 9)

