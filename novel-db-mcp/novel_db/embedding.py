"""
Embedding 模块 — 语义搜索支持（v2 增强版）

增强功能:
  1. 持久化向量存储（embedding_vectors 表），增量更新
  2. 全实体类型覆盖（7种: world/character/foreshadow/chapter_summary/volume/echo/timeline）
  3. 补全查找引擎（字段缺失检测 + 向量匹配推荐）
  4. 搜索→定位→修改闭环

方案：sentence-transformers 本地模型（paraphrase-multilingual-MiniLM-L12-v2）
模型可通过环境变量 EMBEDDING_MODEL 覆盖。

硬依赖：sentence-transformers + numpy。未安装时自动 pip install。

使用方式：
  from .embedding import get_engine_for_novel, invalidate_cache, VectorStore
"""
import hashlib
import json
import logging
import os
import subprocess
import struct
import sys

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)

_np = None
_st_model = None


def _pip_install(package: str):
    logger.info(f"自动安装 {package} ...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package, "-q"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _ensure_deps():
    global _np, _st_model

    if _np is not None and _st_model is not None:
        return

    try:
        import numpy as np
        _np = np
    except ImportError:
        _pip_install("numpy")
        import numpy as np
        _np = np

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        _pip_install("sentence-transformers")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            _pip_install("huggingface-hub")
            _pip_install("sentence-transformers")
            from sentence_transformers import SentenceTransformer

    if _st_model is None:
        logger.info(f"加载嵌入模型: {_DEFAULT_MODEL}")
        _st_model = SentenceTransformer(_DEFAULT_MODEL)


def _compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _encode_vector_to_blob(vector) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _decode_blob_to_vector(blob: bytes):
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


_ENTITY_FIELD_SPECS = {
    "world_setting": {
        "table": "world_settings",
        "name_col": "name",
        "text_fn": lambda r: _build_world_text(r),
        "completeness_fields": {
            "data": {"label": "设定内容", "check": lambda v: bool(v and v != "{}")},
            "keys": {"label": "主键", "check": lambda v: bool(v and v != "[]")},
            "region": {"label": "地区", "check": lambda v: bool(v and v != "全域")},
            "volume_range": {"label": "卷范围", "check": lambda v: bool(v)},
            "writing_guide": {"label": "写作指导", "check": lambda v: bool(v)},
        },
    },
    "character": {
        "table": "characters",
        "name_col": "name",
        "text_fn": lambda r: _build_character_text(r),
        "completeness_fields": {
            "personality": {"label": "性格", "check": lambda v: bool(v)},
            "speech_style": {"label": "说话风格", "check": lambda v: bool(v)},
            "goals": {"label": "目标", "check": lambda v: bool(v)},
            "background": {"label": "背景", "check": lambda v: bool(v)},
            "appearance_detail": {"label": "外观细节", "check": lambda v: bool(v and v != "{}")},
            "decision_engine": {"label": "决策引擎", "check": lambda v: bool(v and v != "{}")},
            "voice_fingerprint": {"label": "声音指纹", "check": lambda v: bool(v and v != "{}")},
            "ability_system": {"label": "能力体系", "check": lambda v: bool(v and v != "{}")},
            "behavior_pattern": {"label": "行为模式", "check": lambda v: bool(v and v != "{}")},
        },
    },
    "foreshadow": {
        "table": "foreshadows",
        "name_col": "id",
        "text_fn": lambda r: _build_foreshadow_text(r),
        "completeness_fields": {
            "description": {"label": "描述", "check": lambda v: bool(v)},
            "planned_recall_chapter": {"label": "计划回收章节", "check": lambda v: v is not None},
            "tags": {"label": "标签", "check": lambda v: bool(v and v != "[]")},
            "reveal_strategy": {"label": "揭示策略", "check": lambda v: bool(v and v != "gradual")},
        },
    },
    "chapter_summary": {
        "table": "chapter_summaries",
        "name_col": "chapter_id",
        "text_fn": lambda r: _build_chapter_summary_text(r),
        "completeness_fields": {
            "summary": {"label": "摘要", "check": lambda v: bool(v)},
            "key_events": {"label": "关键事件", "check": lambda v: bool(v and v != "[]")},
            "characters_involved": {"label": "涉及角色", "check": lambda v: bool(v and v != "[]")},
        },
    },
    "volume": {
        "table": "volumes",
        "name_col": "number",
        "text_fn": lambda r: _build_volume_text(r),
        "completeness_fields": {
            "title": {"label": "标题", "check": lambda v: bool(v)},
            "core_emotion": {"label": "核心情绪", "check": lambda v: bool(v)},
            "causal_chain": {"label": "因果链", "check": lambda v: bool(v)},
            "character_arcs": {"label": "人物弧光", "check": lambda v: bool(v and v != "[]")},
            "act_intro": {"label": "起段", "check": lambda v: bool(v and v != "{}")},
            "act_rise": {"label": "承段", "check": lambda v: bool(v and v != "{}")},
            "act_twist": {"label": "转段", "check": lambda v: bool(v and v != "{}")},
            "act_resolution": {"label": "合段", "check": lambda v: bool(v and v != "{}")},
        },
    },
    "echo": {
        "table": "echoes",
        "name_col": "id",
        "text_fn": lambda r: _build_echo_text(r),
        "completeness_fields": {
            "source_event": {"label": "源事件", "check": lambda v: bool(v)},
            "echo_description": {"label": "回响描述", "check": lambda v: bool(v)},
        },
    },
    "timeline": {
        "table": "timeline_events",
        "name_col": "id",
        "text_fn": lambda r: _build_timeline_text(r),
        "completeness_fields": {
            "event_description": {"label": "事件描述", "check": lambda v: bool(v)},
            "event_time": {"label": "事件时间", "check": lambda v: bool(v)},
            "characters_involved": {"label": "涉及角色", "check": lambda v: bool(v and v != "[]")},
        },
    },
}


def _safe_json_parse(val):
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _join_list(val):
    parsed = _safe_json_parse(val)
    if isinstance(parsed, list):
        return " ".join(str(k) for k in parsed)
    return str(parsed) if parsed else ""


def _build_world_text(r: dict) -> str:
    data = _safe_json_parse(r.get("data", {}))
    content = data.get("content", "") if isinstance(data, dict) else ""
    keys_str = _join_list(r.get("keys", ""))
    tags_str = _join_list(r.get("tags", ""))
    writing_guide = r.get("writing_guide", "")
    return f"{r.get('name', '')} {r.get('category', '')} {keys_str} {tags_str} {content} {writing_guide}"


def _build_character_text(r: dict) -> str:
    parts = [
        r.get("name", ""),
        r.get("role", ""),
        r.get("personality", ""),
        r.get("speech_style", ""),
        r.get("goals", ""),
        r.get("background", ""),
        r.get("weaknesses", ""),
        r.get("catchphrase", ""),
    ]
    for json_field in ("appearance_detail", "decision_engine", "voice_fingerprint",
                        "ability_system", "behavior_pattern", "current_snapshot"):
        val = _safe_json_parse(r.get(json_field, "{}"))
        if isinstance(val, dict):
            parts.append(" ".join(str(v) for v in val.values() if v))
    return " ".join(p for p in parts if p)


def _build_foreshadow_text(r: dict) -> str:
    tags_str = _join_list(r.get("tags", ""))
    return f"{r.get('description', '')} {tags_str} {r.get('clue_type', '')} {r.get('reveal_strategy', '')}"


def _build_chapter_summary_text(r: dict) -> str:
    events = _join_list(r.get("key_events", "[]"))
    chars = _join_list(r.get("characters_involved", "[]"))
    return f"{r.get('summary', '')} {events} {chars}"


def _build_volume_text(r: dict) -> str:
    parts = [
        r.get("title", ""),
        r.get("core_emotion", ""),
        r.get("causal_chain", ""),
    ]
    for act_field in ("act_intro", "act_rise", "act_twist", "act_resolution"):
        val = _safe_json_parse(r.get(act_field, "{}"))
        if isinstance(val, dict):
            parts.append(val.get("prose", ""))
            parts.append(" ".join(str(e) for e in val.get("events", []) if e))
    arcs = _safe_json_parse(r.get("character_arcs", "[]"))
    if isinstance(arcs, list):
        for arc in arcs:
            if isinstance(arc, dict):
                parts.append(arc.get("角色", ""))
                parts.append(arc.get("卷末状态", ""))
    return " ".join(p for p in parts if p)


def _build_echo_text(r: dict) -> str:
    return f"{r.get('source_event', '')} {r.get('echo_description', '')} {r.get('echo_type', '')}"


def _build_timeline_text(r: dict) -> str:
    chars = _join_list(r.get("characters_involved", "[]"))
    return f"{r.get('event_description', '')} {r.get('event_time', '')} {chars}"


class EmbeddingEngine:
    def __init__(self):
        self._documents: list[dict] = []
        self._embeddings = None
        self._model = None

    def index_documents(self, documents: list[dict]):
        _ensure_deps()
        self._documents = documents
        if not documents:
            self._embeddings = None
            return
        self._model = _st_model
        texts = [doc.get("text", "") for doc in documents]
        self._embeddings = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

    def search(self, query_text: str, top_k: int = 10) -> list[dict]:
        _ensure_deps()
        if self._embeddings is None or self._model is None:
            return []
        query_emb = self._model.encode(
            [query_text], normalize_embeddings=True, show_progress_bar=False
        )
        scores = _np.dot(self._embeddings, query_emb.T).flatten()
        top_indices = _np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.01:
                result = dict(self._documents[idx])
                result["score"] = round(score, 4)
                results.append(result)
        return results


_engine_cache: dict[int, EmbeddingEngine] = {}


def get_engine_for_novel(novel_id: int, query_fn) -> EmbeddingEngine:
    if novel_id in _engine_cache:
        return _engine_cache[novel_id]

    _ensure_deps()
    engine = EmbeddingEngine()
    documents = _load_all_documents(novel_id, query_fn)
    engine.index_documents(documents)
    _engine_cache[novel_id] = engine
    return engine


def _load_all_documents(novel_id: int, query_fn) -> list[dict]:
    documents = []

    world_rows = query_fn(
        "SELECT id, category, name, data, keys, tags, writing_guide FROM world_settings "
        "WHERE novel_id = ? AND status = 'active'",
        (novel_id,)
    )
    for r in (world_rows or []):
        text = _build_world_text(r)
        documents.append({
            "type": "world_setting",
            "id": r["id"],
            "category": r["category"],
            "name": r["name"],
            "text": text,
        })

    char_rows = query_fn(
        "SELECT id, name, role, personality, speech_style, goals, background, "
        "weaknesses, catchphrase, appearance_detail, decision_engine, "
        "voice_fingerprint, ability_system, behavior_pattern, current_snapshot "
        "FROM characters WHERE novel_id = ? AND is_active = 1",
        (novel_id,)
    )
    for r in (char_rows or []):
        text = _build_character_text(r)
        documents.append({
            "type": "character",
            "id": r["id"],
            "category": r.get("role", ""),
            "name": r["name"],
            "text": text,
        })

    fs_rows = query_fn(
        "SELECT id, description, tags, clue_type, reveal_strategy FROM foreshadows WHERE novel_id = ?",
        (novel_id,)
    )
    for r in (fs_rows or []):
        text = _build_foreshadow_text(r)
        documents.append({
            "type": "foreshadow",
            "id": r["id"],
            "category": r.get("clue_type", ""),
            "name": f"伏笔#{r['id']}",
            "text": text,
        })

    cs_rows = query_fn(
        "SELECT cs.chapter_id, cs.summary, cs.key_events, cs.characters_involved, "
        "c.number, c.title FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = ?",
        (novel_id,)
    )
    for r in (cs_rows or []):
        text = _build_chapter_summary_text(r)
        documents.append({
            "type": "chapter_summary",
            "id": r["chapter_id"],
            "category": f"Ch{r.get('number', '?')}",
            "name": r.get("title") or f"第{r.get('number', '?')}章",
            "text": text,
        })

    vol_rows = query_fn(
        "SELECT id, number, title, core_emotion, causal_chain, character_arcs, "
        "act_intro, act_rise, act_twist, act_resolution FROM volumes "
        "WHERE novel_id = ?",
        (novel_id,)
    )
    for r in (vol_rows or []):
        text = _build_volume_text(r)
        documents.append({
            "type": "volume",
            "id": r["id"],
            "category": f"V{r.get('number', '?')}",
            "name": r.get("title") or f"第{r.get('number', '?')}卷",
            "text": text,
        })

    echo_rows = query_fn(
        "SELECT id, source_event, echo_description, echo_type FROM echoes WHERE novel_id = ?",
        (novel_id,)
    )
    for r in (echo_rows or []):
        text = _build_echo_text(r)
        documents.append({
            "type": "echo",
            "id": r["id"],
            "category": r.get("echo_type", ""),
            "name": f"回响#{r['id']}",
            "text": text,
        })

    tl_rows = query_fn(
        "SELECT id, event_description, event_time, characters_involved FROM timeline_events "
        "WHERE novel_id = ?",
        (novel_id,)
    )
    for r in (tl_rows or []):
        text = _build_timeline_text(r)
        documents.append({
            "type": "timeline",
            "id": r["id"],
            "category": "timeline",
            "name": f"时间线#{r['id']}",
            "text": text,
        })

    return documents


class VectorStore:
    def __init__(self, query_fn):
        self._query_fn = query_fn

    def _ensure_table(self):
        self._query_fn(
            "CREATE TABLE IF NOT EXISTS embedding_vectors ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "novel_id INTEGER NOT NULL, "
            "entity_type TEXT NOT NULL, "
            "entity_id INTEGER NOT NULL, "
            "text_hash TEXT NOT NULL, "
            "vector BLOB NOT NULL, "
            "source_text TEXT DEFAULT '', "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE(novel_id, entity_type, entity_id))"
        )

    def rebuild_index(self, novel_id: int, entity_types: list[str] = None):
        _ensure_deps()
        self._ensure_table()
        types_to_index = entity_types or list(_ENTITY_FIELD_SPECS.keys())

        for entity_type in types_to_index:
            spec = _ENTITY_FIELD_SPECS.get(entity_type)
            if not spec:
                continue

            table = spec["table"]
            if entity_type == "chapter_summary":
                rows = self._query_fn(
                    f"SELECT cs.chapter_id as id, cs.summary, cs.key_events, "
                    f"cs.characters_involved, c.number, c.title "
                    f"FROM {table} cs JOIN chapters c ON cs.chapter_id = c.id "
                    f"WHERE c.novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "foreshadow":
                rows = self._query_fn(
                    f"SELECT id, description, tags, clue_type, reveal_strategy "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "echo":
                rows = self._query_fn(
                    f"SELECT id, source_event, echo_description, echo_type "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "timeline":
                rows = self._query_fn(
                    f"SELECT id, event_description, event_time, characters_involved "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "world_setting":
                rows = self._query_fn(
                    f"SELECT id, category, name, data, keys, tags, writing_guide "
                    f"FROM {table} WHERE novel_id = ? AND status = 'active'",
                    (novel_id,)
                )
            elif entity_type == "character":
                rows = self._query_fn(
                    f"SELECT id, name, role, personality, speech_style, goals, background, "
                    f"weaknesses, catchphrase, appearance_detail, decision_engine, "
                    f"voice_fingerprint, ability_system, behavior_pattern, current_snapshot "
                    f"FROM {table} WHERE novel_id = ? AND is_active = 1",
                    (novel_id,)
                )
            elif entity_type == "volume":
                rows = self._query_fn(
                    f"SELECT id, number, title, core_emotion, causal_chain, character_arcs, "
                    f"act_intro, act_rise, act_twist, act_resolution "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            else:
                continue

            if not rows:
                continue

            texts = []
            entity_ids = []
            for r in rows:
                text = spec["text_fn"](r)
                texts.append(text)
                entity_ids.append(r["id"])

            embeddings = _st_model.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            )

            for i, (eid, text) in enumerate(zip(entity_ids, texts)):
                text_hash = _compute_text_hash(text)
                vector_blob = _encode_vector_to_blob(embeddings[i])

                existing = self._query_fn(
                    "SELECT text_hash FROM embedding_vectors "
                    "WHERE novel_id = ? AND entity_type = ? AND entity_id = ?",
                    (novel_id, entity_type, eid), fetch="one"
                )

                if existing and existing.get("text_hash") == text_hash:
                    continue

                if existing:
                    self._query_fn(
                        "UPDATE embedding_vectors SET vector = ?, text_hash = ?, "
                        "source_text = ?, updated_at = datetime('now') "
                        "WHERE novel_id = ? AND entity_type = ? AND entity_id = ?",
                        (vector_blob, text_hash, text[:500],
                         novel_id, entity_type, eid),
                        fetch="none"
                    )
                else:
                    self._query_fn(
                        "INSERT INTO embedding_vectors "
                        "(novel_id, entity_type, entity_id, text_hash, vector, source_text) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (novel_id, entity_type, eid, text_hash, vector_blob, text[:500]),
                        fetch="none"
                    )

    def search(self, novel_id: int, query_text: str, top_k: int = 10,
               entity_types: list[str] = None, min_score: float = 0.1) -> list[dict]:
        _ensure_deps()
        self._ensure_table()

        query_emb = _st_model.encode(
            [query_text], normalize_embeddings=True, show_progress_bar=False
        )
        query_vec = query_emb[0]

        conditions = ["novel_id = ?"]
        params: list = [novel_id]

        if entity_types:
            ph = ",".join(["?"] * len(entity_types))
            conditions.append(f"entity_type IN ({ph})")
            params.extend(entity_types)

        where = " AND ".join(conditions)
        rows = self._query_fn(
            f"SELECT entity_type, entity_id, vector, source_text FROM embedding_vectors WHERE {where}",
            tuple(params)
        )

        if not rows:
            return []

        scored = []
        for r in rows:
            vec = _decode_blob_to_vector(r["vector"])
            score = float(_np.dot(vec, query_vec))
            if score >= min_score:
                scored.append({
                    "type": r["entity_type"],
                    "id": r["entity_id"],
                    "score": round(score, 4),
                    "source_text": (r.get("source_text") or "")[:200],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def find_incomplete(self, novel_id: int, entity_types: list[str] = None,
                        min_missing: int = 1) -> list[dict]:
        types_to_check = entity_types or list(_ENTITY_FIELD_SPECS.keys())
        results = []

        for entity_type in types_to_check:
            spec = _ENTITY_FIELD_SPECS.get(entity_type)
            if not spec:
                continue

            table = spec["table"]
            comp_fields = spec["completeness_fields"]

            if entity_type == "chapter_summary":
                rows = self._query_fn(
                    f"SELECT cs.chapter_id as id, cs.summary, cs.key_events, "
                    f"cs.characters_involved, c.number, c.title "
                    f"FROM {table} cs JOIN chapters c ON cs.chapter_id = c.id "
                    f"WHERE c.novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "foreshadow":
                rows = self._query_fn(
                    f"SELECT id, description, planned_recall_chapter, tags, reveal_strategy "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "echo":
                rows = self._query_fn(
                    f"SELECT id, source_event, echo_description "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "timeline":
                rows = self._query_fn(
                    f"SELECT id, event_description, event_time, characters_involved "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            elif entity_type == "world_setting":
                rows = self._query_fn(
                    f"SELECT id, category, name, data, keys, region, volume_range, writing_guide "
                    f"FROM {table} WHERE novel_id = ? AND status = 'active'",
                    (novel_id,)
                )
            elif entity_type == "character":
                rows = self._query_fn(
                    f"SELECT id, name, role, personality, speech_style, goals, background, "
                    f"appearance_detail, decision_engine, voice_fingerprint, "
                    f"ability_system, behavior_pattern "
                    f"FROM {table} WHERE novel_id = ? AND is_active = 1",
                    (novel_id,)
                )
            elif entity_type == "volume":
                rows = self._query_fn(
                    f"SELECT id, number, title, core_emotion, causal_chain, "
                    f"character_arcs, act_intro, act_rise, act_twist, act_resolution "
                    f"FROM {table} WHERE novel_id = ?",
                    (novel_id,)
                )
            else:
                continue

            for r in (rows or []):
                missing = []
                for field_name, field_spec in comp_fields.items():
                    val = r.get(field_name)
                    if not field_spec["check"](val):
                        missing.append({
                            "field": field_name,
                            "label": field_spec["label"],
                        })

                if len(missing) >= min_missing:
                    name = r.get("name") or r.get("title") or f"#{r.get('id', '?')}"
                    if entity_type == "volume":
                        name = f"V{r.get('number', '?')}"
                    elif entity_type == "chapter_summary":
                        name = r.get("title") or f"第{r.get('number', '?')}章"
                    elif entity_type in ("foreshadow", "echo", "timeline"):
                        name = f"{entity_type}#{r.get('id', '?')}"

                    results.append({
                        "type": entity_type,
                        "id": r.get("id") or r.get("chapter_id"),
                        "name": name,
                        "category": r.get("category") or r.get("role", ""),
                        "missing_count": len(missing),
                        "missing_fields": missing,
                    })

        results.sort(key=lambda x: x["missing_count"], reverse=True)
        return results

    def vector_match_suggestions(self, novel_id: int, entity_type: str,
                                  entity_id: int, missing_field: str,
                                  top_k: int = 5) -> list[dict]:
        _ensure_deps()
        self._ensure_table()

        source = self._query_fn(
            "SELECT source_text FROM embedding_vectors "
            "WHERE novel_id = ? AND entity_type = ? AND entity_id = ?",
            (novel_id, entity_type, entity_id), fetch="one"
        )
        if not source or not source.get("source_text"):
            return []

        query_text = f"{entity_type}的{missing_field}设定"
        query_emb = _st_model.encode(
            [query_text], normalize_embeddings=True, show_progress_bar=False
        )

        same_type_rows = self._query_fn(
            "SELECT entity_id, vector, source_text FROM embedding_vectors "
            "WHERE novel_id = ? AND entity_type = ? AND entity_id != ?",
            (novel_id, entity_type, entity_id)
        )

        if not same_type_rows:
            return []

        scored = []
        for r in same_type_rows:
            vec = _decode_blob_to_vector(r["vector"])
            score = float(_np.dot(vec, query_emb[0]))
            scored.append({
                "id": r["entity_id"],
                "score": round(score, 4),
                "source_text": (r.get("source_text") or "")[:200],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


def invalidate_cache(novel_id: int = None):
    if novel_id and novel_id in _engine_cache:
        del _engine_cache[novel_id]
    elif novel_id is None:
        _engine_cache.clear()
