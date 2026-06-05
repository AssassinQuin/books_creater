import functools
import json
import time
from collections import defaultdict


class NovelDBError(Exception):
    pass


class NotFoundError(NovelDBError):
    pass


class ValidationError(NovelDBError):
    pass


class ConflictError(NovelDBError):
    pass


# ── Tool call statistics ─────────────────────────────────────
_call_stats = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0.0})


def get_call_stats() -> dict:
    """Return a snapshot of tool call statistics."""
    return {
        "tools": dict(_call_stats),
        "total_calls": sum(s["count"] for s in _call_stats.values()),
        "total_errors": sum(s["errors"] for s in _call_stats.values()),
    }


def reset_call_stats():
    """Reset all statistics."""
    _call_stats.clear()


def mcp_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.monotonic()
        try:
            result = func(*args, **kwargs)
            elapsed = time.monotonic() - t0
            stat = _call_stats[func.__name__]
            stat["count"] += 1
            stat["total_ms"] += elapsed * 1000
            return result
        except NovelDBError as e:
            elapsed = time.monotonic() - t0
            stat = _call_stats[func.__name__]
            stat["count"] += 1
            stat["errors"] += 1
            stat["total_ms"] += elapsed * 1000
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            elapsed = time.monotonic() - t0
            stat = _call_stats[func.__name__]
            stat["count"] += 1
            stat["errors"] += 1
            stat["total_ms"] += elapsed * 1000
            return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    return wrapper
