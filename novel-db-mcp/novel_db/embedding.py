"""
Embedding 模块 — 语义搜索支持

方案：sentence-transformers 本地模型（paraphrase-multilingual-MiniLM-L12-v2）
模型可通过环境变量 EMBEDDING_MODEL 覆盖。

延迟导入：numpy/sentence-transformers 仅在首次使用时加载，
未安装时 semantic_search 工具返回明确错误，不影响 MCP 启动。

使用方式：
  from .embedding import get_engine_for_novel, invalidate_cache
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)

_np = None
_st_model = None
_st_available = None


def _ensure_deps():
    global _np, _st_model, _st_available
    if _st_available is not None:
        return _st_available
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        _np = np
        if _st_model is None:
            _st_model = SentenceTransformer(_DEFAULT_MODEL)
        _st_available = True
    except ImportError as e:
        logger.warning(f"sentence-transformers not available: {e}")
        _st_available = False
    return _st_available


class EmbeddingEngine:
    def __init__(self):
        self._documents: list[dict] = []
        self._embeddings = None
        self._model = None

    def index_documents(self, documents: list[dict]):
        self._documents = documents
        if not documents:
            self._embeddings = None
            return
        if not _ensure_deps():
            raise RuntimeError(
                "sentence-transformers 未安装，无法构建语义索引。"
                "请运行: pip install sentence-transformers"
            )
        self._model = _st_model
        texts = [doc.get("text", "") for doc in documents]
        self._embeddings = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

    def search(self, query_text: str, top_k: int = 10) -> list[dict]:
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

    engine = EmbeddingEngine()
    documents = []

    world_rows = query_fn(
        "SELECT id, category, name, data, keys, tags FROM world_settings "
        "WHERE novel_id = ? AND status = 'active'",
        (novel_id,)
    )
    for r in (world_rows or []):
        data = r.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                data = {}
        content = ""
        if isinstance(data, dict):
            content = data.get("content", "")
        keys_str = r.get("keys", "")
        if isinstance(keys_str, list):
            keys_str = " ".join(str(k) for k in keys_str)
        tags_str = r.get("tags", "")
        if isinstance(tags_str, list):
            tags_str = " ".join(str(t) for t in tags_str)
        text = f"{r['name']} {r['category']} {keys_str} {tags_str} {content}"
        documents.append({
            "type": "world_setting",
            "id": r["id"],
            "category": r["category"],
            "name": r["name"],
            "text": text,
        })

    char_rows = query_fn(
        "SELECT id, name, role, personality, speech_style, goals, background FROM characters "
        "WHERE novel_id = ? AND is_active = 1",
        (novel_id,)
    )
    for r in (char_rows or []):
        text = f"{r['name']} {r.get('role', '')} {r.get('personality', '')} {r.get('speech_style', '')} {r.get('goals', '')} {r.get('background', '')}"
        documents.append({
            "type": "character",
            "id": r["id"],
            "category": r.get("role", ""),
            "name": r["name"],
            "text": text,
        })

    fs_rows = query_fn(
        "SELECT id, description, tags FROM foreshadows WHERE novel_id = ?",
        (novel_id,)
    )
    for r in (fs_rows or []):
        tags_str = r.get("tags", "")
        if isinstance(tags_str, list):
            tags_str = " ".join(str(t) for t in tags_str)
        text = f"{r['description']} {tags_str}"
        documents.append({
            "type": "foreshadow",
            "id": r["id"],
            "category": "",
            "name": f"伏笔#{r['id']}",
            "text": text,
        })

    engine.index_documents(documents)
    _engine_cache[novel_id] = engine
    return engine


def invalidate_cache(novel_id: int = None):
    if novel_id and novel_id in _engine_cache:
        del _engine_cache[novel_id]
    elif novel_id is None:
        _engine_cache.clear()
