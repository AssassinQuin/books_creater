"""统一的 MCP 工具参数类型转换。

解决的核心问题:
  LLM 通过 MCP/JSON Schema 传参数时，list/dict 类型可能收到:
  1. Python list/dict（LLM 发了 JSON 数组/对象）— 正常
  2. 逗号分隔 str "a,b,c"（LLM 把 list 当 str 写了）— 需 split
  3. JSON str '["a","b"]' / '{"k":"v"}'（LLM 序列化了两遍）— 需 json.loads
  4. None / "" / "[]" / "{}" — 空值

  统一用 coerce_list / coerce_dict 处理，所有 tools_*.py 共享。
"""
import json


def coerce_list(value) -> list | None:
    """将任意输入统一转换为 list 或 None。

    返回 None = 空值/未传，调用方跳过即可。
    返回 list = 有内容，调用方直接用。
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value if value else None
    if isinstance(value, str):
        s = value.strip()
        if not s or s in ("[]", "{}"):
            return None
        # 尝试 JSON 解析
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return parsed if parsed else None
        except (json.JSONDecodeError, TypeError):
            pass
        # 逗号分隔回退
        items = [item.strip() for item in s.split(",") if item.strip()]
        return items if items else None
    return None


def coerce_dict(value) -> dict | None:
    """将任意输入统一转换为 dict 或 None。

    返回 None = 空值/未传，调用方跳过即可。
    返回 dict = 有内容，调用方直接用。
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value if value else None
    if isinstance(value, str):
        s = value.strip()
        if not s or s == "{}":
            return None
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                return parsed if parsed else None
        except (json.JSONDecodeError, TypeError):
            pass
    return None
