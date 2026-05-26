from .db import query
from .errors import NotFoundError


class _UnsetType:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "_UNSET"

    def __bool__(self):
        return False


_UNSET = _UnsetType()


def _resolve_entity(novel_id: int, table: str, name: str, entity_label: str = "实体") -> int:
    """Resolve an entity name to its ID. Raises NotFoundError if not found."""
    row = query(
        f"SELECT id FROM {table} WHERE novel_id = ? AND name = ?",
        (novel_id, name), fetch="one"
    )
    if not row:
        raise NotFoundError(f"{entity_label} '{name}' 不存在")
    return row["id"]


def _resolve_novel_id(novel_name_or_id) -> int:
    if isinstance(novel_name_or_id, int):
        return novel_name_or_id
    try:
        nid = int(novel_name_or_id)
        return nid
    except (ValueError, TypeError):
        pass
    r = query("SELECT id FROM novels WHERE name = ?", (novel_name_or_id,), fetch="one")
    if not r:
        raise NotFoundError(f"小说 '{novel_name_or_id}' 不存在于数据库中")
    return r["id"]


def _resolve_chapter_id(novel_name: str, chapter_number: int) -> int:
    novel_id = _resolve_novel_id(novel_name)
    r = query("SELECT id FROM chapters WHERE novel_id = ? AND number = ?",
              (novel_id, chapter_number), fetch="one")
    if not r:
        raise NotFoundError(f"章节 {chapter_number} 不存在于小说 '{novel_name}' 中")
    return r["id"]


def _get_novel_name(novel_id: int) -> str:
    r = query("SELECT name FROM novels WHERE id = ?", (novel_id,), fetch="one")
    return r["name"] if r else ""
