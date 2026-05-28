import json
import re


_VALID_TABLES = frozenset({
    "characters", "world_settings", "chapters", "chapter_summaries",
    "foreshadows", "volumes", "echoes", "timeline_events",
    "entity_edges", "character_relations", "character_state_snapshots",
    "relation_snapshots", "distillation_evolutions", "scene_outlines",
    "chapter_qualities", "writing_rules", "novels", "novel_config",
    "plot_threads", "embedding_vectors",
})

_SAFE_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_table(table: str):
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table name: {table}")


def _validate_identifiers(names):
    for name in names:
        if not _SAFE_IDENTIFIER.match(str(name)):
            raise ValueError(f"Invalid SQL identifier: {name}")


def safe_json_loads(value, field_name: str = ""):
    """json.loads with clear error message for MCP tool callers."""
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as e:
        from .errors import ValidationError
        raise ValidationError(f"'{field_name or 'value'}' 不是合法 JSON: {e}")


def build_update_sql(table, fields_dict, where_clause, where_params):
    if not fields_dict:
        raise ValueError("fields_dict cannot be empty")
    _validate_table(table)
    _validate_identifiers(fields_dict.keys())
    set_parts = []
    params = []
    for col, val in fields_dict.items():
        set_parts.append(f"{col} = ?")
        params.append(val)
    set_parts.append("updated_at = datetime('now')")
    sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_clause}"
    params.extend(where_params)
    return (sql, tuple(params))


def build_upsert_sql(table, insert_cols, update_cols, insert_params, update_params):
    _validate_table(table)
    _validate_identifiers(insert_cols)
    _validate_identifiers(update_cols)
    placeholders = ", ".join(["?"] * len(insert_cols))
    cols_str = ", ".join(insert_cols)
    conflict_cols = ", ".join(insert_cols[:3])
    update_parts = [f"{col} = ?" for col in update_cols]
    update_str = ", ".join(update_parts) + ", updated_at = datetime('now')"
    all_params = list(insert_params) + list(update_params)
    sql = (
        f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_cols}) DO UPDATE SET {update_str}"
    )
    return (sql, tuple(all_params))
