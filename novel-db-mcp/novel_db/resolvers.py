from .db import query


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
        raise ValueError(f"小说 '{novel_name_or_id}' 不存在于数据库中")
    return r["id"]


def _resolve_chapter_id(novel_name: str, chapter_number: int) -> int:
    novel_id = _resolve_novel_id(novel_name)
    r = query("SELECT id FROM chapters WHERE novel_id = ? AND number = ?",
              (novel_id, chapter_number), fetch="one")
    if not r:
        raise ValueError(f"章节 {chapter_number} 不存在于小说 '{novel_name}' 中")
    return r["id"]


def _get_novel_name(novel_id: int) -> str:
    r = query("SELECT name FROM novels WHERE id = ?", (novel_id,), fetch="one")
    return r["name"] if r else ""
