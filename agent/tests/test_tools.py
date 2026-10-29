import json

from app.tools import execute_tool


def test_success():
    args = json.dumps({"matrix": ["A1A1", "B2B2"], "pattern": ["A1", "B2"]})
    result = execute_tool("find_submatrices", args)

    assert result["count"] == 2


def test_unknown_tool():
    args = json.dumps({"matrix": ["A1A1", "B2B2"], "pattern": ["A1", "B2"]})
    result = execute_tool("drop_database", args)

    assert result["error"] == "unknown_tool"


def test_invalid_json():
    result = execute_tool("find_submatrices", '{"matrix": ["A1A')

    assert result["error"] == "invalid_arguments"


def test_arguments_not_objects():
    result = execute_tool("find_submatrices", "[1, 2, 3]")

    assert result["error"] == "invalid_arguments"


def test_validation_error():
    args = json.dumps({"matrix": ["A1G1", "B2B2"], "pattern": ["A1", "B2"]})
    result = execute_tool("find_submatrices", args)

    assert result["error"] == "validation_error"
    assert "G" in result["message"]


def test_missing_pattern():
    args = json.dumps({"matrix": ["A1"]})
    result = execute_tool("find_submatrices", args)

    assert result["error"] == "validation_error"


def test_error_has_no_exception():
    result = execute_tool("find_submatrices", "это не json")

    assert isinstance(result, dict)
    assert "error" in result