import logging

logger = logging.getLogger(__name__)


def fire_post_save(novel_id: int, entity_type: str, entity_id: int) -> list[str]:
    failed = []
    for hook in _HOOKS:
        try:
            hook(novel_id, entity_type, entity_id)
        except Exception as e:
            logger.error(f"post_save hook {hook.__name__} failed for "
                         f"{entity_type}:{entity_id} novel={novel_id}: {e}")
            failed.append(f"{hook.__name__}: {e}")
    return failed


def fire_and_report(novel_id: int, entity_type: str, entity_id: int) -> list[str]:
    """fire_post_save with warning log. Returns list of hook failures."""
    failed = fire_post_save(novel_id, entity_type, entity_id)
    if failed:
        logger.warning(f"post_save hooks partially failed for "
                       f"{entity_type}:{entity_id}: {failed}")
    return failed


def _sync_edges_hook(novel_id: int, entity_type: str, entity_id: int):
    from .tools_graph import _sync_edges
    _sync_edges(novel_id, entity_type, entity_id)


def _invalidate_embedding_hook(novel_id: int, entity_type: str, entity_id: int):
    from .embedding import invalidate_cache, mark_dirty
    invalidate_cache(novel_id)
    mark_dirty(novel_id, entity_type, entity_id)


_HOOKS = [
    _sync_edges_hook,
    _invalidate_embedding_hook,
]
