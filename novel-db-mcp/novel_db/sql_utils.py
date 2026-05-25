def build_update_sql(table, fields_dict, where_clause, where_params):
    if not fields_dict:
        raise ValueError("fields_dict cannot be empty")
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
