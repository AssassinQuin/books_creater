import functools
import json


class NovelDBError(Exception):
    pass


class NotFoundError(NovelDBError):
    pass


class ValidationError(NovelDBError):
    pass


class ConflictError(NovelDBError):
    pass


def mcp_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NovelDBError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    return wrapper
