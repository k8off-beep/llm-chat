import json

from app.submatrix import find_submatrices, SubmatrixValidationError

FIND_SUBMATRICES_TOOL = {
    "type": "function",
    "function": {
        "name": "find_submatrices",
        "description": "Находит все точные вхождения квадратного образца в матрице шестнадцатеричных символов.",
        "parameters": {
            "type": "object",
            "properties": {
                "matrix":  {"type": "array", "items": {"type": "string"}, "description": "Строки основной матрицы"},
                "pattern": {"type": "array", "items": {"type": "string"}, "description": "Строки квадратного образца"}
            },
            "required": ["matrix", "pattern"]
        }
    }
}

TOOLS = [FIND_SUBMATRICES_TOOL]


def execute_tool(name: str, arguments: str) -> dict:
    if name != "find_submatrices":
        return {"error": "unknown_tool", "message": "Неизвестный инструмент."}

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError:
        return {"error": "invalid_arguments", "message": "Неверные аргументы."}

    if not isinstance(args, dict):
        return {"error": "invalid_arguments", "message": "Аргументы должны быть JSON-объектом."}

    try:
        return find_submatrices(args.get("matrix"), args.get("pattern"))
    except SubmatrixValidationError as e:
        return {
            "error": "validation_error",
            "message": str(e),
            "hint": "Не вызывай инструмент повторно и не меняй данные. Объясни пользователю ошибку и попроси прислать исправленные данные.",
        }