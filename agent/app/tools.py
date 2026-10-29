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
                "matrix": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Основная матрица, В КОТОРОЙ ищем. Обычно больше образца. "
                                "В запросе «Найди X в Y» это Y.",
                },
                "pattern": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Квадратный образец — то, ЧТО ищем. Обычно меньше матрицы. "
                                "В запросе «Найди X в Y» это X.",
                },
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
            "hint": "Служебная подсказка, не цитируй её: не вызывай инструмент повторно, не меняй данные. "
                    "Ответь ровно в формате: «Ошибка: <текст message>. Пришлите, пожалуйста, исправленные данные.» "
                    "Больше ничего не добавляй.",
        }