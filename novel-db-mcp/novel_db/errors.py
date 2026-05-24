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
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFoundError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except ValidationError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except ConflictError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
