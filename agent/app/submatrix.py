HEX_CHARS = "ABCDEF0123456789"


class SubmatrixValidationError(ValueError):
    pass


def _check_chars(rows: list[str], name: str) -> None:  
    """Проверяет, что все символы — шестнадцатеричные."""
    for row in rows:
        for char in row:
            if char not in HEX_CHARS:
                raise SubmatrixValidationError(
                    f"Недопустимый символ '{char}' в {name}.")


def _check_rows(value: list, name: str) -> None:
    """Проверяет, что значение — список строк."""
    if not isinstance(value, list):
        raise SubmatrixValidationError(f"{name} должна быть списком строк.")
    for row in value:
        if not isinstance(row, str):
            raise SubmatrixValidationError(f"{name} должна быть списком строк.")


def find_submatrices(matrix: list[str], pattern: list[str]) -> dict:

    _check_rows(matrix, "матрице")
    _check_rows(pattern, "образце")

    matrix = [row.upper() for row in matrix]
    pattern = [row.upper() for row in pattern]

    _check_chars(matrix, "матрице")
    _check_chars(pattern, "образце")

    rows, columns, n = len(matrix), len(matrix[0]) if matrix else 0, len(pattern)

    if rows == 0 or rows > 8:
        raise SubmatrixValidationError("Матрица должна иметь от 1 до 8 строк.")

    if columns == 0 or columns > 8:
        raise SubmatrixValidationError(
            "Матрица должна иметь от 1 до 8 столбцов.")

    for row in matrix:
        if len(row) != columns:
            raise SubmatrixValidationError(
                "Все строки матрицы должны быть одинаковой длины.")

    if n == 0 or n > 8:
        raise SubmatrixValidationError("Образец должен иметь от 1 до 8 строк.")

    for row in pattern:
        if len(row) != n:
            raise SubmatrixValidationError(
                "Образец должен быть квадратной матрицей.")

    matches = []
    for row in range(rows - n + 1):
        for column in range(columns - n + 1):
            for i in range(n):
                if matrix[row+i][column:column+n] != pattern[i]:
                    break
            else:
                matches.append({"row": row, "column": column})

    return {"matrix": matrix, 
            "pattern": pattern, 
            "pattern_size": n, 
            "count": len(matches), 
            "matches": matches}