"""
SyncEngine — 模板驱动的 DB↔文件 通用同步引擎

设计原则:
  1. 模板定义一切：实体类型、DB查询、文件路径、段落顺序、渲染方式
  2. 零代码扩展：新增实体类型 = 新增一个 YAML manifest，不改引擎代码
  3. 向后兼容：现有 sync.py 的公开函数保持不变，内部委托给引擎
  4. YAML 优先：YAML manifest 可覆盖内置 Python 模板

使用方式:
  from novel_db.sync_engine import engine

  # DB → 文件（全量同步）
  engine.db_to_files(novel_name="这次不一样了", entity_type="character")

  # DB → 文件（单条同步）
  engine.db_to_files(novel_name="这次不一样了", entity_type="character", entity_key="沈野")

  # 文件 → DB
  engine.files_to_db(novel_name="这次不一样了", entity_type="world")

  # 双向对比
  report = engine.diff(novel_name="这次不一样了", entity_type="character")

  # YAML manifest 扩展
  engine.load_manifests("sync_manifests/")  # 自动注册目录下所有 .yaml
  engine.available_types  # 查看所有已注册类型

  # 手动注册
  engine.register(my_custom_template)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

_META_BLACKLIST = {
    "keys", "secondary_keys", "tags", "related", "region",
    "volume_range", "priority", "is_constant", "writing_guide",
    "lorebook_id", "faction_id", "锁定", "关联设定", "叙事功能",
}


def clean_data_for_storage(raw_data):
    if isinstance(raw_data, list):
        content_items = []
        for item in raw_data:
            if isinstance(item, dict):
                filtered = {k: v for k, v in item.items() if k not in _META_BLACKLIST}
                if "content" in filtered:
                    content_items.append(str(filtered.pop("content")))
                content_items.extend(
                    str(v) for v in filtered.values()
                    if isinstance(v, str) and v.strip()
                )
            elif isinstance(item, str) and item.strip():
                content_items.append(item.strip())
        return {"content": "\n".join(content_items)} if content_items else raw_data
    elif isinstance(raw_data, dict):
        return {k: v for k, v in raw_data.items() if k not in _META_BLACKLIST}
    return raw_data


from .db import query, PROJECT_ROOT
from .sync import (
    _is_empty, _jsonb_to_md, _jsonb_to_md_narrative, _parse_json_field,
    _render_md_table, _md_bullet,
    _record_db_hash, _record_file_hash,
    _compute_hash, _db_row_to_hashable,
    _get_hash_record, _detect_conflict, _snapshot_sync_hashes,
    _NOVELS_BASE,
)

log = logging.getLogger(__name__)

# ============================================================================
# 内置变换函数 — YAML manifest 中 transform: builtin.xxx 引用
# ============================================================================


def _resolve_faction_name(val, row):
    """Transform: faction_id → faction display name."""
    if not val:
        return None
    frow = query("SELECT name FROM world_settings WHERE id = ?", (val,), fetch="val")
    return frow or str(val)


def _resolve_chapter_number(val, row):
    """Transform: chapter_id → Ch{number} display."""
    if not val:
        return None
    ch = query("SELECT number FROM chapters WHERE id = ?", (val,), fetch="val")
    return f"Ch{ch}" if ch else str(val)


def _resolve_category_file(val, row, tpl=None):
    """Transform: category → 中文文件名（世界观专用）.
    优先从 tpl.category_file_map 查找，回退到内置映射。
    """
    if tpl and tpl.category_file_map and val in tpl.category_file_map:
        return tpl.category_file_map[val]
    _WORLD_CATEGORY_FILES = {
        "core_setting": "核心设定",
        "bestiary": "异灵图鉴",
        "ability": "能力体系",
        "item": "物品装备",
        "economy": "经济体系",
        "daily_life": "日常生活",
        "history": "历史事件",
        "location": "地图",
        "faction": "势力",
        "race": "种族",
        "building": "建筑",
        "culture": "文化",
        "plant": "植物",
    }
    return _WORLD_CATEGORY_FILES.get(val, val)


_BUILTIN_TRANSFORMS: dict[str, Callable] = {
    "resolve_faction": _resolve_faction_name,
    "resolve_chapter_number": _resolve_chapter_number,
    "resolve_category_file": _resolve_category_file,
}


# ============================================================================
# Template Protocol — 同步模板数据结构
# ============================================================================


@dataclass
class FieldDef:
    """字段映射：DB列 → MD输出键"""
    column: str                   # DB列名
    md_key: str | None = None     # MD中的键名（默认同column）
    type: str = "text"            # text | int | bool | jsonb | list
    optional: bool = True
    transform: str | None = None  # transform名称（从template.transforms查找）
    condition: str | None = None  # 条件列名：只有该列非空时才输出


@dataclass
class BlockquoteField:
    """引用式字段：> **标签**：值"""
    column: str
    label: str | None = None      # 默认用column


@dataclass
class SectionDef:
    """段落定义 — 模板中的一个 ## section"""
    heading: str                   # 段落标题
    type: str = "fields"           # fields | jsonb | static | raw | table | blockquote | relation | acts
    condition: str = "not_empty"   # not_empty | always
    indent: int = 1                # jsonb渲染缩进

    # type=fields
    fields: list[FieldDef] | None = None

    # type=jsonb
    jsonb_column: str | None = None
    jsonb_key: str | None = None   # 用作bullet key（默认同jsonb_column）
    title_key: str | None = None   # list[dict] 标注键名（如 "name", "stage"），用于 MD 往返还原
    fallback_columns: list[str] | None = None  # jsonb为空时的备选列
    jsonb_mode: str = "bullet"     # bullet=嵌套列表 | narrative=标题+段落（人可读）

    # type=static
    static_content: str | None = None

    # type=raw
    raw_column: str | None = None

    # type=table
    table_column: str | None = None  # JSONB列名，内容是list[dict]

    # type=blockquote
    blockquotes: list[BlockquoteField] | None = None

    # type=acts（四幕结构）
    acts: list[tuple[str, str]] | None = None  # [(显示名, 列名), ...]

    # type=relation（从关联表查询）
    relation_query: str | None = None
    relation_params: list[str] | None = None  # 从row中取值的列名


@dataclass
class RelationQueryDef:
    """关联查询定义"""
    sql: str                       # SQL模板，用 {row.col} 做参数替换
    param_columns: list[str]        # 从row中取哪些列作为参数
    heading: str
    format: str = "type_arrow"     # type_arrow | custom
    extra_fields: list[str] | None = None  # 额外渲染的字段


@dataclass
class SyncTemplate:
    """
    同步模板 — 定义一种实体类型在 DB 和文件之间的完整映射。

    新增实体类型只需定义一个 SyncTemplate 实例并 register 到引擎。
    """
    # 基本信息
    name: str                       # 模板名（如 "character", "volume"）
    display_name: str               # 中文显示名（如 "人物", "卷级大纲"）

    # DB 映射
    db_table: str                   # 表名
    id_field: str                   # 主标识列（如 "name", "number"）
    file_dir: str                   # 相对于 novels/{name}/ 的目录

    # 同步行为
    authority: str = "db"           # db | file | bidirectional
    merge_mode: str = "overwrite"   # overwrite | section_replace | append

    # 段落定义（有序）
    sections: list[SectionDef] = field(default_factory=list)

    # 关联查询
    relations: RelationQueryDef | None = None

    # 变换函数
    transforms: dict[str, Callable] = field(default_factory=dict)

    # 以下为可选字段（有默认值）
    query_extra: str = ""           # 额外 WHERE 条件
    order_by: str = ""              # 排序
    file_pattern: str = "{name}.md" # 文件名模式
    file_title: str = "{name}"      # 文件内一级标题
    section_marker: str | None = None  # section_replace标记
    file_to_db_enabled: bool = False
    file_to_db_sql: str | None = None
    header_template: str | None = None
    skip_existing: bool = False

    # --- Manifest 扩展字段 ---
    category_file_map: dict[str, str] | None = None  # 世界观：category → 中文文件名
    manifest_path: str | None = None  # 来源 YAML 路径（调试用）
    composite_id_fields: list[str] | None = None  # 复合主键（如 world 的 [category, name]）
    group_by: str | None = None      # 按列分组写入同一文件（如 "category"）


# ============================================================================
# SyncEngine — 通用同步引擎
# ============================================================================


class SyncEngine:
    """
    模板驱动的通用同步引擎。

    核心流程:
      1. engine.register(template)     — 注册模板
      2. engine.db_to_files(...)        — DB→文件
      3. engine.files_to_db(...)        — 文件→DB
      4. engine.diff(...)               — 双向对比
    """

    def __init__(self):
        self._templates: dict[str, SyncTemplate] = {}
        self._manifest_loaded: set[str] = set()
        self._table_columns_cache: dict[str, set[str]] = {}

    # ── 模板管理 ──────────────────────────────────────────────────

    def register(self, template: SyncTemplate):
        """注册一个同步模板。"""
        self._templates[template.name] = template

    def get(self, name: str) -> SyncTemplate:
        """获取已注册的模板。"""
        if name not in self._templates:
            raise KeyError(f"未注册的同步模板: '{name}'，可用: {list(self._templates.keys())}")
        return self._templates[name]

    @property
    def available_types(self) -> list[str]:
        return list(self._templates.keys())

    def _get_table_columns(self, table: str) -> set[str]:
        if table not in self._table_columns_cache:
            cols = query(f"PRAGMA table_info({table})")
            self._table_columns_cache[table] = {c["name"] for c in cols}
        return self._table_columns_cache[table]

    # ── YAML Manifest 加载 ──────────────────────────────────────

    def load_manifest(self, path: str) -> SyncTemplate:
        """
        从单个 YAML 文件加载同步模板并注册。

        Args:
            path: YAML 文件路径

        Returns:
            加载的 SyncTemplate 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: manifest 格式错误
        """
        path = os.path.abspath(path)
        if path in self._manifest_loaded:
            log.debug(f"Manifest 已加载，跳过: {path}")
            return self._templates.get(self._name_from_path(path))

        if not os.path.exists(path):
            raise FileNotFoundError(f"Manifest 文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "name" not in data:
            raise ValueError(f"Manifest 缺少 'name' 字段: {path}")

        tpl = self._parse_manifest(data)
        tpl.manifest_path = path
        self.register(tpl)
        self._manifest_loaded.add(path)
        log.info(f"已加载 manifest: {data['name']} ({path})")
        return tpl

    def load_manifests(self, dir_path: str) -> list[SyncTemplate]:
        """
        从目录批量加载所有 YAML manifest 文件。

        Args:
            dir_path: 包含 .yaml 文件的目录路径

        Returns:
            加载的 SyncTemplate 列表
        """
        dir_path = os.path.abspath(dir_path)
        if not os.path.isdir(dir_path):
            log.warning(f"Manifest 目录不存在: {dir_path}")
            return []

        loaded = []
        for fname in sorted(os.listdir(dir_path)):
            if fname.endswith(('.yaml', '.yml')) and not fname.startswith('_'):
                fpath = os.path.join(dir_path, fname)
                try:
                    tpl = self.load_manifest(fpath)
                    loaded.append(tpl)
                except Exception as e:
                    log.error(f"加载 manifest 失败: {fpath}: {e}")
        return loaded

    def _name_from_path(self, path: str) -> str:
        """从文件路径提取模板名。"""
        return Path(path).stem

    def _parse_manifest(self, data: dict) -> SyncTemplate:
        """
        将 YAML dict 解析为 SyncTemplate 实例。

        YAML 格式与 SyncTemplate 字段 1:1 对应，额外支持:
          - transforms: 可用 builtin.xxx 引用内置函数
          - category_file_map: 世界观分类→文件名映射
        """
        # --- 解析 transforms ---
        transforms = {}
        raw_transforms = data.get("transforms") or {}
        for key, val in raw_transforms.items():
            if isinstance(val, str) and val.startswith("builtin."):
                builtin_name = val[len("builtin."):]  # 去掉 builtin. 前缀
                if builtin_name in _BUILTIN_TRANSFORMS:
                    transforms[key] = _BUILTIN_TRANSFORMS[builtin_name]
                else:
                    log.warning(f"未知内置变换: {val}，可用: {list(_BUILTIN_TRANSFORMS.keys())}")
            # 非 builtin 的暂不支持（需要动态 import）

        # --- 解析 sections ---
        sections = []
        for sec_data in data.get("sections") or []:
            sec = self._parse_section(sec_data)
            if sec:
                sections.append(sec)

        # --- 解析 relations ---
        relations = None
        rel_data = data.get("relations")
        if rel_data:
            relations = RelationQueryDef(
                sql=rel_data["sql"].strip(),
                param_columns=rel_data.get("param_columns", []),
                heading=rel_data.get("heading", "关联"),
            )

        # --- 解析 file_to_db ---
        ftb = data.get("file_to_db")
        file_to_db_enabled = False
        file_to_db_sql = None
        if ftb:
            file_to_db_enabled = ftb.get("enabled", False)

        # --- 构建 SyncTemplate ---
        tpl = SyncTemplate(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            db_table=data["db_table"],
            id_field=data["id_field"],
            file_dir=data.get("file_dir", ""),
            authority=data.get("authority", "db"),
            merge_mode=data.get("merge_mode", "overwrite"),
            group_by=data.get("group_by"),
            sections=sections,
            relations=relations,
            transforms=transforms,
            query_extra=data.get("query_extra", ""),
            order_by=data.get("order_by", ""),
            file_pattern=data.get("file_pattern", "{name}.md"),
            file_title=data.get("file_title", "{name}"),
            section_marker=data.get("section_marker"),
            file_to_db_enabled=file_to_db_enabled,
            file_to_db_sql=file_to_db_sql,
            header_template=data.get("header_template"),
            skip_existing=data.get("skip_existing", False),
            category_file_map=data.get("category_file_map"),
            composite_id_fields=data.get("composite_id_fields"),
        )
        return tpl

    def _parse_section(self, data: dict) -> SectionDef | None:
        """将 YAML section dict 解析为 SectionDef。"""
        sec_type = data.get("type", "fields")

        # fields
        fields = None
        if sec_type == "fields" and data.get("fields"):
            fields = []
            for fd in data["fields"]:
                if isinstance(fd, str):
                    # 简写: "column_name"
                    fields.append(FieldDef(column=fd))
                elif isinstance(fd, dict):
                    fields.append(FieldDef(
                        column=fd["column"],
                        md_key=fd.get("md_key"),
                        type=fd.get("type", "text"),
                        optional=fd.get("optional", True),
                        transform=fd.get("transform"),
                        condition=fd.get("condition"),
                    ))

        # blockquotes
        blockquotes = None
        if sec_type == "blockquote" and data.get("blockquotes"):
            blockquotes = []
            for bq in data["blockquotes"]:
                blockquotes.append(BlockquoteField(
                    column=bq["column"],
                    label=bq.get("label"),
                ))

        # acts
        acts = None
        if sec_type == "acts" and data.get("acts"):
            acts = []
            for act in data["acts"]:
                if isinstance(act, list) and len(act) == 2:
                    acts.append((act[0], act[1]))

        return SectionDef(
            heading=data["heading"],
            type=sec_type,
            condition=data.get("condition", "not_empty"),
            indent=data.get("indent", 1),
            fields=fields,
            jsonb_column=data.get("jsonb_column"),
            jsonb_key=data.get("jsonb_key"),
            title_key=data.get("title_key"),
            fallback_columns=data.get("fallback_columns"),
            jsonb_mode=data.get("jsonb_mode", "bullet"),
            static_content=data.get("static_content"),
            raw_column=data.get("raw_column"),
            table_column=data.get("table_column"),
            blockquotes=blockquotes,
            acts=acts,
        )

    # ── DB → 文件 ────────────────────────────────────────────────

    def db_to_files(self, novel_name: str, entity_type: str,
                    entity_key: str | None = None, overwrite: bool = False) -> dict:
        """
        将DB数据同步到文件。

        Args:
            novel_name: 小说名称
            entity_type: 实体类型（模板名）
            entity_key: 指定实体标识（如角色名），None=全量同步
            overwrite: 是否覆盖已有文件

        Returns:
            {"synced": int, "skipped": int, "errors": list}
        """
        tpl = self.get(entity_type)
        novel_id = self._resolve_novel_id(novel_name)

        # 查询DB行
        rows = self._query_entities(tpl, novel_id, entity_key)

        result = {"synced": 0, "skipped": 0, "errors": [], "conflicts": []}

        # 分组模式：按 group_by 列分组
        # 如果 file_pattern 含 {name}，说明每个实体需要独立文件（如世界观按分类子目录）
        # 否则同一组写入一个聚合文件（如伏笔清单）
        if tpl.group_by:
            if tpl.file_pattern and "{name}" in tpl.file_pattern:
                # 逐实体模式 + 分组目录：每个实体独立文件，但仍按分组组织目录和清理
                groups: dict[str, list[dict]] = {}
                for row in rows:
                    entity_name = row.get("name", "")
                    if entity_name in self._SKIP_ENTITY_NAMES:
                        result["skipped"] += 1
                        continue
                    group_key = str(row.get(tpl.group_by, "_default"))
                    groups.setdefault(group_key, []).append(row)

                for row in rows:
                    if row.get("name", "") in self._SKIP_ENTITY_NAMES:
                        continue
                    try:
                        r = self._sync_one_to_file(
                            tpl, novel_id, novel_name, row, overwrite)
                        if r.get("conflict"):
                            result["conflicts"].append(r["conflict"])
                            result["skipped"] += 1
                        elif r["wrote"]:
                            result["synced"] += 1
                        else:
                            result["skipped"] += 1
                    except Exception as e:
                        result["errors"].append({"key": row.get(tpl.id_field, "?"), "error": str(e)})

                self._cleanup_stale_files(tpl, novel_name, groups)
                return result

            # 聚合模式：同一组所有实体写入一个文件
            groups: dict[str, list[dict]] = {}
            for row in rows:
                entity_name = row.get("name", "")
                if entity_name in self._SKIP_ENTITY_NAMES:
                    result["skipped"] += 1
                    continue
                group_key = str(row.get(tpl.group_by, "_default"))
                groups.setdefault(group_key, []).append(row)

            for group_key, group_rows in groups.items():
                try:
                    r = self._sync_group_to_file(
                        tpl, novel_id, novel_name, group_key, group_rows, overwrite)
                    if r.get("conflict"):
                        result["conflicts"].append(r["conflict"])
                        result["skipped"] += len(group_rows)
                    else:
                        result["synced"] += r["wrote"]
                        result["skipped"] += (len(group_rows) - r["wrote"])
                except Exception as e:
                    result["errors"].append({"key": group_key, "error": str(e)})

            self._cleanup_stale_files(tpl, novel_name, groups)
            return result

        # 原始模式：每个条目一个文件
        for row in rows:
            entity_name = row.get("name", "")
            if entity_name in self._SKIP_ENTITY_NAMES:
                result["skipped"] += 1
                continue
            try:
                r = self._sync_one_to_file(tpl, novel_id, novel_name, row, overwrite)
                if r.get("conflict"):
                    result["conflicts"].append(r["conflict"])
                    result["skipped"] += 1
                elif r["wrote"]:
                    result["synced"] += 1
                else:
                    result["skipped"] += 1
            except Exception as e:
                result["errors"].append({"key": row.get(tpl.id_field, "?"), "error": str(e)})

        return result

    def _query_entities(self, tpl: SyncTemplate, novel_id: int,
                        entity_key: str | None = None) -> list[dict]:
        """根据模板查询DB实体。"""
        sql = f"SELECT * FROM {tpl.db_table} WHERE novel_id = ?"
        params: list[Any] = [novel_id]

        if tpl.query_extra:
            sql += f" {tpl.query_extra}"
        if entity_key is not None:
            sql += f" AND {tpl.id_field} = ?"
            params.append(entity_key)
        if tpl.order_by:
            sql += f" ORDER BY {tpl.order_by}"

        return query(sql, tuple(params), fetch="all") or []

    def _resolve_data_key(self, tpl: SyncTemplate, row: dict) -> str:
        """构造唯一 data_key。对有 composite_id_fields 的模板用复合键。"""
        if tpl.composite_id_fields:
            return ":".join(str(row.get(f, "")) for f in tpl.composite_id_fields)
        return str(row.get(tpl.id_field, ""))

    def _replace_category_file(self, tpl: SyncTemplate, text: str, row: dict) -> str:
        """统一替换 {category_file} 占位符。优先 category_file_map，回退内置映射。"""
        if "{category_file}" not in text or "category" not in row:
            return text
        cat = row["category"]
        resolved = _resolve_category_file(cat, row, tpl=tpl)
        if resolved.endswith("/"):
            resolved = resolved.rstrip("/")
        return text.replace("{category_file}", resolved)

    @staticmethod
    def _resolve_filename_placeholders(fname: str, row: dict, id_field: str) -> str:
        placeholder_cols = [id_field, "title", "number", "category", "category_file"]
        for col in placeholder_cols:
            if col not in row or row[col] is None:
                continue
            val = row[col]
            fmt_pattern = re.compile(rf"\{{{col}:(\w+)\}}")
            fmt_match = fmt_pattern.search(fname)
            if fmt_match:
                fmt_spec = fmt_match.group(1)
                try:
                    formatted = format(val, fmt_spec)
                except (ValueError, TypeError):
                    formatted = str(val)
                fname = fmt_pattern.sub(formatted, fname)
            fname = fname.replace(f"{{{col}}}", str(val))
        return fname

    def _resolve_filepath(self, tpl: SyncTemplate, novel_name: str, row: dict) -> str:
        fname = tpl.file_pattern

        if "{category_file}" in fname and "category" in row:
            cat = row["category"]
            resolved = _resolve_category_file(cat, row, tpl=tpl)
            # resolved 以 / 结尾表示目录，直接替换即可；
            # file_pattern 中的 {name} 等由 _resolve_filename_placeholders 后续处理
            fname = fname.replace("{category_file}", resolved)

        fname = self._resolve_filename_placeholders(fname, row, tpl.id_field)

        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        full_dir = os.path.join(base, os.path.dirname(fname))
        os.makedirs(full_dir, exist_ok=True)
        return os.path.join(base, fname)

    def _cleanup_stale_files(self, tpl: SyncTemplate, novel_name: str,
                              groups: dict[str, list[dict]]) -> None:
        """group_by 模式下，清理不再对应 DB 行的文件。保护用户修改过的文件。"""
        novel_id = self._resolve_novel_id(novel_name)
        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        per_entity = tpl.file_pattern and "{name}" in tpl.file_pattern

        for group_key, group_rows in groups.items():
            cat_file = ""
            if tpl.category_file_map and group_rows:
                cat_file = tpl.category_file_map.get(group_key, group_key + "/")

            group_dir = os.path.join(base, cat_file)
            if not os.path.isdir(group_dir):
                continue

            entity_names = {row.get("name", "") for row in group_rows}

            def _is_user_modified(fpath: str, data_key: str) -> bool:
                """检查文件是否被用户修改过（hash 与上次同步不同）。"""
                stored = _get_hash_record(novel_id, tpl.name, data_key)
                if not stored or not stored.get("last_sync_file_hash"):
                    return False  # 没有同步记录，不算用户修改
                with open(fpath, "r", encoding="utf-8") as f:
                    current_hash = _compute_hash(f.read())
                return current_hash != stored["last_sync_file_hash"]

            if per_entity:
                # 逐实体模式：保留 {name}.md 对应的文件，删除不在 entity_names 中的
                for f in os.listdir(group_dir):
                    if not f.endswith(".md"):
                        continue
                    stem = f[:-3]
                    if stem not in entity_names:
                        fpath = os.path.join(group_dir, f)
                        # 复合键：category:name（匹配 _resolve_data_key 格式）
                        composite_key = f"{group_key}:{stem}" if tpl.composite_id_fields else stem
                        if not _is_user_modified(fpath, composite_key):
                            os.remove(fpath)
                # 清理空目录（所有 .md 都被清理后）
                if os.path.isdir(group_dir):
                    remaining = [f for f in os.listdir(group_dir) if f.endswith(".md")]
                    if not remaining:
                        os.rmdir(group_dir)
            else:
                # 聚合模式：保留分组标签文件，删除旧的单独实体文件
                _CATEGORY_LABELS = {
                    "core_setting": "核心设定", "ability": "能力体系",
                    "faction": "势力", "location": "地理", "economy": "经济",
                    "daily_life": "日常生活", "history": "历史", "item": "物品",
                    "race": "种族", "culture": "文化", "plant": "植物",
                    "bestiary": "异兽图鉴", "building": "建筑",
                }
                keep_name = _CATEGORY_LABELS.get(group_key, group_key) + ".md"
                for f in os.listdir(group_dir):
                    if not f.endswith(".md"):
                        continue
                    if f == keep_name:
                        continue
                    stem = f[:-3]
                    if stem in entity_names:
                        fpath = os.path.join(group_dir, f)
                        if not _is_user_modified(fpath, stem):
                            os.remove(fpath)

    def _sync_group_to_file(self, tpl: SyncTemplate, novel_id: int,
                             novel_name: str, group_key: str,
                             rows: list[dict], overwrite: bool) -> dict:
        """将同一分组的所有条目合并写入一个文件。

        Returns:
            {"wrote": int, "conflict": None | dict}
        """
        # 确定文件路径：用第一个 row 解析 category_file 目录，文件名用分组标签
        sample_row = rows[0]
        cat_file = ""
        if tpl.category_file_map and "category" in sample_row:
            cat_file = tpl.category_file_map.get(
                sample_row["category"],
                sample_row["category"] + "/")

        # 中文标签映射
        _CATEGORY_LABELS = {
            "core_setting": "核心设定",
            "ability": "能力体系",
            "faction": "势力",
            "location": "地理",
            "economy": "经济",
            "daily_life": "日常生活",
            "history": "历史",
            "item": "物品",
            "race": "种族",
            "culture": "文化",
            "plant": "植物",
            "bestiary": "异兽图鉴",
            "building": "建筑",
        }
        label = _CATEGORY_LABELS.get(group_key, group_key)

        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        fpath = os.path.join(base, cat_file, f"{label}.md")

        # 冲突检测
        if not overwrite and os.path.exists(fpath):
            stored = _get_hash_record(novel_id, tpl.name, group_key)
            with open(fpath, "r", encoding="utf-8") as f:
                current_file_hash = _compute_hash(f.read())
            status = _detect_conflict(stored, current_file_hash)
            if status in ("file_newer", "conflict"):
                return {
                    "wrote": 0,
                    "conflict": {
                        "type": tpl.name,
                        "key": group_key,
                        "conflict_type": status,
                        "file_path": fpath,
                    },
                }
            if status == "skip":
                return {"wrote": 0, "conflict": None}

        os.makedirs(os.path.dirname(fpath), exist_ok=True)

        # 渲染所有条目
        all_lines = [f"# {label}\n"]
        for i, row in enumerate(rows):
            if i > 0:
                all_lines.append("\n---\n")
            # 每个条目用一级标题
            entry_name = row.get("name", "")
            all_lines.append(f"# {entry_name}\n")

            # 渲染 blockquote + fields + jsonb（跳过 header_template，因为已用自己的标题）
            for sec in tpl.sections:
                rendered = self._render_section(tpl, sec, row, novel_id)
                if rendered:
                    all_lines.extend(rendered)

        full_content = "\n".join(all_lines) + "\n"

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(full_content)

        file_hash = _compute_hash(full_content)
        db_hash = _compute_hash("\n".join(_db_row_to_hashable(dict(r)) for r in rows))
        _record_file_hash(novel_id, tpl.name, group_key, full_content)
        _snapshot_sync_hashes(novel_id, tpl.name, group_key, db_hash, file_hash)
        return {"wrote": len(rows), "conflict": None}

    def _sync_one_to_file(self, tpl: SyncTemplate, novel_id: int,
                          novel_name: str, row: dict, overwrite: bool) -> dict:
        """将一行DB数据同步到文件。

        Returns:
            {"wrote": bool, "conflict": None | dict}
        """
        fpath = self._resolve_filepath(tpl, novel_name, row)
        data_key = self._resolve_data_key(tpl, row)

        # 跳过已有文件
        if os.path.exists(fpath) and tpl.skip_existing and not overwrite:
            _record_file_hash(novel_id, tpl.name, data_key, "")
            return {"wrote": False, "conflict": None}

        # 冲突检测：写入前检查文件是否被用户修改过
        if not overwrite and os.path.exists(fpath):
            stored = _get_hash_record(novel_id, tpl.name, data_key)
            with open(fpath, "r", encoding="utf-8") as f:
                current_file_hash = _compute_hash(f.read())
            status = _detect_conflict(stored, current_file_hash)
            if status in ("file_newer", "conflict"):
                return {
                    "wrote": False,
                    "conflict": {
                        "type": tpl.name,
                        "key": data_key,
                        "conflict_type": status,
                        "file_path": fpath,
                    },
                }
            if status == "skip":
                return {"wrote": False, "conflict": None}

        # 渲染所有段落
        content_lines = []

        # 文件标题
        if tpl.header_template:
            title = tpl.header_template
            for col, val in row.items():
                if val is not None and f"{{{col}}}" in title:
                    title = title.replace(f"{{{col}}}", str(val))
            title = self._replace_category_file(tpl, title, row)
            content_lines.append(title)

        # 渲染段落
        for sec in tpl.sections:
            rendered = self._render_section(tpl, sec, row, novel_id)
            if rendered:
                content_lines.extend(rendered)

        # 渲染关联查询
        if tpl.relations:
            rendered = self._render_relation(tpl.relations, row, novel_id)
            if rendered:
                content_lines.extend(rendered)

        full_content = "\n".join(content_lines) + "\n"

        # 安全保护：当渲染内容只有标题（无实际数据）时跳过写入
        # 防止空 DB data 覆盖文件中的丰富内容（已发生 3 次）
        non_header_lines = [l for l in content_lines
                           if l.strip()
                           and not l.startswith("# ")
                           and not l.startswith("> ")
                           and not l.startswith("- **")]
        if not non_header_lines:
            log.warning(
                "sync: 跳过空内容写入 %s (data_key=%s) — DB data 为空，"
                "保留文件原有内容", fpath, data_key
            )
            return {"wrote": False, "conflict": None, "skipped_empty": True}

        # 写入文件
        if tpl.merge_mode == "section_replace" and os.path.exists(fpath):
            full_content = self._merge_section(tpl, fpath, full_content, row)
        elif tpl.merge_mode == "append" and os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                existing = f.read()
            full_content = existing + "\n" + full_content
        # else: overwrite（默认）

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(full_content)

        db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
        file_hash = _compute_hash(full_content)
        _record_file_hash(novel_id, tpl.name, data_key, full_content)
        _snapshot_sync_hashes(novel_id, tpl.name, data_key, db_hash, file_hash)
        return {"wrote": True, "conflict": None}

    def _merge_section(self, tpl: SyncTemplate, fpath: str,
                       new_content: str, row: dict) -> str:
        """section_replace模式：替换文件中的匹配段落或追加。

        只匹配行首的 section_marker（用 \n 前缀或文件开头定位），
        避免 marker 出现在用户正文中时误匹配。
        """
        if not tpl.section_marker:
            return new_content

        with open(fpath, "r", encoding="utf-8") as f:
            existing = f.read()

        marker = tpl.section_marker
        for col, val in row.items():
            if val is not None and f"{{{col}}}" in marker:
                marker = marker.replace(f"{{{col}}}", str(val))

        # 只匹配行首: marker 前面是 \n 或文件开头
        match_pos = -1
        search_from = 0
        while search_from < len(existing):
            idx = existing.find(marker, search_from)
            if idx == -1:
                break
            # 行首 = idx==0 或前面是 \n
            if idx == 0 or existing[idx - 1] == "\n":
                match_pos = idx
                break
            search_from = idx + 1

        if match_pos >= 0:
            next_h2 = existing.find("\n## ", match_pos + len(marker))
            if next_h2 == -1:
                next_h2 = len(existing)
            return existing[:match_pos] + new_content + existing[next_h2:]
        else:
            return existing + "\n" + new_content

    # ── 段落渲染器 ──────────────────────────────────────────────

    def _render_section(self, tpl: SyncTemplate, sec: SectionDef,
                        row: dict, novel_id: int) -> list[str] | None:
        """根据段落类型分发渲染。"""
        renderer_map = {
            "fields": self._render_fields,
            "jsonb": self._render_jsonb,
            "static": self._render_static,
            "raw": self._render_raw,
            "table": self._render_table,
            "blockquote": self._render_blockquote,
            "acts": self._render_acts,
        }
        renderer = renderer_map.get(sec.type)
        if not renderer:
            return None

        # 替换 heading 中的模板变量（如 {category}: {name}）
        heading = sec.heading
        for col, val in row.items():
            if val is not None and f"{{{col}}}" in heading:
                heading = heading.replace(f"{{{col}}}", str(val))

        lines = renderer(tpl, sec, row)
        if not lines:
            return None

        if heading:
            return [f"\n## {heading}\n"] + lines
        else:
            return ["\n"] + lines

    def _render_fields(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=fields: 从行字段渲染 bullet 列表。"""
        lines = []
        for fd in sec.fields:
            val = row.get(fd.column)
            if fd.condition and _is_empty(row.get(fd.condition)):
                continue
            if fd.optional and _is_empty(val):
                continue

            # Transform
            if fd.transform and fd.transform in tpl.transforms:
                val = tpl.transforms[fd.transform](val, row)

            key = fd.md_key or fd.column
            bullet = _md_bullet(key, val)
            # _md_bullet 可能返回 list（list 类型多行渲染）
            if isinstance(bullet, list):
                lines.extend(bullet)
            else:
                lines.append(bullet)
        return lines

    def _render_jsonb(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=jsonb: 从JSONB列渲染。支持 bullet(嵌套列表) 和 narrative(标题+段落) 模式。"""
        col = sec.jsonb_column or sec.jsonb_key
        val = row.get(col)
        if _is_empty(val):
            if sec.fallback_columns:
                lines = []
                for fc in sec.fallback_columns:
                    v = row.get(fc)
                    if not _is_empty(v):
                        if isinstance(v, (dict, list)):
                            lines.append(f"- **{fc}**:")
                            lines.extend(_jsonb_to_md(v, sec.indent))
                        else:
                            lines.append(f"- **{fc}**: {v}")
                return lines if lines else None
            return None

        parsed = _parse_json_field(val)
        if not parsed:
            return None

        if tpl.name == "world" and isinstance(parsed, dict):
            parsed = clean_data_for_storage(parsed)

        if sec.jsonb_mode == "narrative" and isinstance(parsed, dict):
            return _jsonb_to_md_narrative(parsed)

        key = sec.jsonb_key or col
        return [f"- **{key}**:"] + _jsonb_to_md(parsed, sec.indent, title_key=sec.title_key)

    def _render_static(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=static: 静态文本内容。"""
        content = sec.static_content or ""
        return [content] if content else None

    def _render_raw(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=raw: 原始文本列直接输出。"""
        val = row.get(sec.raw_column, "")
        if _is_empty(val):
            return None
        return [str(val)]

    def _render_table(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=table: JSONB列渲染为MD表格。"""
        val = _parse_json_field(row.get(sec.table_column))
        if not val or not isinstance(val, list) or not val:
            return None
        cols = list(val[0].keys()) if val else []
        return _render_md_table(val, cols)

    def _render_blockquote(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=blockquote: 引用式字段。"""
        lines = []
        for bq in (sec.blockquotes or []):
            val = row.get(bq.column, "")
            if not _is_empty(val):
                label = bq.label or bq.column
                lines.append(f"> **{label}**：{val}")
        return lines if lines else None

    def _render_acts(self, tpl: SyncTemplate, sec: SectionDef, row: dict) -> list[str]:
        """type=acts: 四幕结构渲染。"""
        all_lines = []
        for label, col_name in (sec.acts or []):
            act = _parse_json_field(row.get(col_name))
            if not act:
                continue
            all_lines.append(f"\n### {label}\n")
            prose = act.get("prose", "")
            if prose:
                all_lines.append(prose)
            events = act.get("events", [])
            if events:
                all_lines.append("\n事件清单：")
                for i, evt in enumerate(events, 1):
                    all_lines.append(f"- E{i}：{evt}")
            feibi = act.get("feibi_notes", [])
            if feibi:
                all_lines.append("\n费笔清单：")
                for i, fb in enumerate(feibi, 1):
                    all_lines.append(f"- 费笔{i}：{fb}")
            list_items = act.get("list_items", [])
            if list_items:
                for item in list_items:
                    all_lines.append(f"- {item}")
        return all_lines if all_lines else None

    def _render_relation(self, rel: RelationQueryDef, row: dict,
                         novel_id: int) -> list[str] | None:
        """渲染关联查询结果。"""
        params = [row.get(col) for col in rel.param_columns]
        rows = query(rel.sql, tuple(params), fetch="all")
        if not rows:
            return None

        lines = [f"\n## {rel.heading}\n"]
        for r in rows:
            desc = r.get("description", "")
            line = f"- **{r['relation_type']}** ({r['from_name']} → {r['to_name']}, 强度{r['intensity']})"
            if desc:
                line += f": {desc}"
            lines.append(line)
            if r.get("subtext_design") and not _is_empty(r["subtext_design"]):
                lines.append(f"    - **弦外之音**: {r['subtext_design']}")
            if r.get("dialogue_adjustment") and not _is_empty(r["dialogue_adjustment"]):
                lines.append("    - **对话调整**:")
                lines.extend(_jsonb_to_md(r["dialogue_adjustment"], 2))
        return lines

    # ── 文件 → DB（结构化解析）───────────────────────────────────

    def files_to_db(self, novel_name: str, entity_type: str) -> dict:
        """
        将文件结构化解析后同步回DB（真正的反向同步，非截断dump）。

        通过模板的 sections 定义逆向解析 MD 文件，按字段映射写入对应 DB 列。
        需要 manifest 中 file_to_db.enabled = true。
        """
        from .md_parser import (
            split_sections, find_section, parse_bullet_fields,
            parse_jsonb_bullets, parse_md_table, parse_blockquotes,
            parse_acts,
        )

        tpl = self.get(entity_type)
        if not tpl.file_to_db_enabled:
            return {"error": f"{entity_type} 未启用 File→DB 同步（file_to_db.enabled 未设置）", "synced": 0}
        novel_id = self._resolve_novel_id(novel_name)
        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        if not os.path.isdir(base):
            return {"error": f"目录不存在: {base}"}

        # section_replace 模式或 group_by 聚合模式：需要处理聚合文件（多行→1文件）
        if tpl.merge_mode == "section_replace" or tpl.group_by:
            return self._files_to_db_aggregate(tpl, novel_id, novel_name)

        # overwrite 模式：一个文件对应一行DB记录
        result = {"synced": 0, "errors": [], "details": []}
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".md"):
                continue

            # 文件名模式过滤：只处理匹配模板 file_pattern 的文件
            if not self._match_file_pattern(tpl, fname):
                continue

            fpath = os.path.join(base, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                row = self._parse_file_to_row(tpl, content)
                if not row:
                    result["errors"].append({"file": fname, "error": "解析结果为空"})
                    continue
                row["novel_id"] = novel_id
                self._upsert_row(tpl, row)
                key = self._resolve_data_key(tpl, row) or fname
                _record_db_hash(novel_id, tpl.name, key, content)
                result["synced"] += 1
                result["details"].append({"file": fname, "key": key, "fields": len(row)})
            except Exception as e:
                log.error(f"File→DB 解析失败: {fpath}: {e}", exc_info=True)
                result["errors"].append({"file": fname, "error": str(e)})

        return result

    def _parse_file_to_row(self, tpl: SyncTemplate, content: str) -> dict | None:
        """
        将单个文件内容解析为 DB 行 dict。
        根据 template 的 sections 定义逆向解析各段落。
        """
        from .md_parser import (
            split_sections, find_section, parse_bullet_fields,
            parse_jsonb_bullets, parse_md_table, parse_blockquotes,
            parse_acts,
        )

        sections = split_sections(content)
        if not sections:
            return None

        row = {}
        for sec_def in tpl.sections:
            heading = sec_def.heading
            # 跳过动态 heading 中的模板变量（如 {category}: {name}）
            if "{" in heading:
                # 尝试匹配：把 {xxx} 替换为 .* 正则
                pattern = re.escape(heading)
                pattern = re.sub(r'\\\{[^}]+\\\}', r'.*?', pattern)
                found = find_section(sections, re.compile(f"^{pattern}$"))
            else:
                found = find_section(sections, heading)

            if not found or not found["body"]:
                continue

            if sec_def.type == "fields":
                fields = parse_bullet_fields(found["body"])
                for fd in sec_def.fields or []:
                    # md_key → column 映射（逆向：文件中的key可能是md_key或column）
                    col = fd.column
                    # 文件中的 key 优先用 md_key，其次用 column
                    val = fields.get(fd.md_key) if fd.md_key else None
                    if val is None:
                        val = fields.get(col)
                    if val is not None:
                        row[col] = val

            elif sec_def.type == "jsonb":
                parsed = parse_jsonb_bullets(found["body"])
                if parsed is not None:
                    row[sec_def.jsonb_column] = json.dumps(parsed, ensure_ascii=False)

            elif sec_def.type == "table":
                parsed = parse_md_table(found["body"])
                if parsed is not None:
                    row[sec_def.table_column] = json.dumps(parsed, ensure_ascii=False)

            elif sec_def.type == "blockquote":
                bq = parse_blockquotes(found["body"])
                for bqf in sec_def.blockquotes or []:
                    col = bqf.column
                    label = bqf.label or col
                    if label in bq:
                        row[col] = bq[label]

            elif sec_def.type == "raw":
                row[sec_def.raw_column] = found["body"]

            elif sec_def.type == "acts":
                act_labels = [a[0] for a in (sec_def.acts or [])]
                parsed = parse_acts(found["body"], act_labels)
                if parsed:
                    for label, col_name in (sec_def.acts or []):
                        if col_name in parsed:
                            row[col_name] = json.dumps(parsed[col_name], ensure_ascii=False)

            # static: 不需要解析

        # 从第一行标题提取 id_field（如 "# 沈野" → name="沈野"）
        h1 = sections[0] if sections else None
        if h1 and h1["level"] == 1 and h1["heading"]:
            if tpl.id_field == "name":
                row["name"] = h1["heading"]
            elif tpl.id_field == "number":
                m = re.match(r'V(\d+)', h1["heading"])
                if m:
                    row["number"] = int(m.group(1))

        return row if row else None

    _SKIP_ENTITY_NAMES = frozenset({"元数据", "详细内容", "写作执行检查清单"})

    def _parse_heading_for_entity(
        self, tpl: SyncTemplate, heading: str, fields: dict, novel_id: int, row: dict, file_category: str | None = None
    ) -> bool:
        stripped = heading.strip()
        if stripped in self._SKIP_ENTITY_NAMES:
            return False

        if tpl.name in ("foreshadow", "echo"):
            m = re.match(rf"{tpl.name}:\s*(\d+)", heading)
            if m:
                row[tpl.id_field] = int(m.group(1))
            else:
                return False

        elif tpl.name == "world":
            m = re.match(r'^(\w+):\s*(.+)$', heading)
            if m:
                row["category"] = m.group(1)
                row["name"] = m.group(2).strip()
            elif file_category:
                row["category"] = file_category
                row["name"] = heading.strip()
            else:
                return False

        elif tpl.name == "relation":
            m = re.match(r'^(.+?)\s*→\s*(.+?)\s*\((.+?)\)$', heading)
            if not m:
                return False
            from_name = m.group(1).strip()
            to_name = m.group(2).strip()
            rel_type = m.group(3).strip()
            if from_name.startswith("{"):
                from_char = query(
                    "SELECT id FROM characters WHERE novel_id = ? AND id = ?",
                    (novel_id, int(fields.get("from", 0))), fetch="one"
                ) if fields.get("from") else None
                to_char = query(
                    "SELECT id FROM characters WHERE novel_id = ? AND id = ?",
                    (novel_id, int(fields.get("to", 0))), fetch="one"
                ) if fields.get("to") else None
            else:
                from_char = query(
                    "SELECT id FROM characters WHERE novel_id = ? AND name = ?",
                    (novel_id, from_name), fetch="one"
                )
                to_char = query(
                    "SELECT id FROM characters WHERE novel_id = ? AND name = ?",
                    (novel_id, to_name), fetch="one"
                )
            if from_char and to_char:
                row["from_character_id"] = from_char["id"]
                row["to_character_id"] = to_char["id"]
                row["relation_type"] = rel_type
            else:
                return False

        else:
            return False

        return True

    def _files_to_db_aggregate(self, tpl: SyncTemplate, novel_id: int,
                                novel_name: str) -> dict:
        """
        聚合文件的 File→DB 解析（section_replace 模式）。
        多行DB记录共享一个文件，每个段落对应一行。

        支持: foreshadow, echo（按id标识）, world（按category:name标识）
        """
        from .md_parser import (
            split_sections, find_section, parse_bullet_fields,
            parse_jsonb_bullets, parse_md_table,
            parse_blockquotes, parse_acts,
        )

        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)

        # 查找匹配的文件（支持两种模式）
        target_files = []
        pattern = tpl.file_pattern

        if "{" not in pattern:
            fpath = os.path.join(base, pattern)
            if os.path.isfile(fpath):
                target_files.append((fpath, None))
        else:
            if tpl.category_file_map:
                for cat, cat_path in tpl.category_file_map.items():
                    if cat_path.endswith("/"):
                        subdir = os.path.join(base, cat_path)
                        if os.path.isdir(subdir):
                            for fname in sorted(os.listdir(subdir)):
                                if not fname.endswith(".md"):
                                    continue
                                target_files.append((os.path.join(subdir, fname), cat))
                    else:
                        fpath = os.path.join(base, f"{cat_path}.md")
                        if os.path.isfile(fpath):
                            target_files.append((fpath, cat))
            else:
                for fname in sorted(os.listdir(base)):
                    if not fname.endswith(".md"):
                        continue
                    target_files.append((os.path.join(base, fname), None))

        if not target_files:
            return {"error": f"找不到匹配文件: {tpl.file_pattern} (目录: {base})"}

        result = {"synced": 0, "errors": [], "details": []}

        for target_file, file_category in target_files:
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()

                sections = split_sections(content)

                for sec in sections:
                    heading = sec["heading"]
                    if not sec["body"]:
                        continue

                    row = {"novel_id": novel_id}
                    fields = parse_bullet_fields(sec["body"])

                    if not self._parse_heading_for_entity(tpl, heading, fields, novel_id, row, file_category):
                        continue

                    # ── 解析段落内容 ──
                    # fields 已在上方提前解析

                    # 将 fields 映射到 DB 列
                    for sec_def in tpl.sections:
                        if sec_def.type == "fields":
                            for fd in sec_def.fields or []:
                                col = fd.column
                                val = fields.get(fd.md_key) if fd.md_key else None
                                if val is None:
                                    val = fields.get(col)
                                if val is not None:
                                    row[col] = val

                        elif sec_def.type == "jsonb":
                            # JSONB 段落：尝试从嵌套 bullet 解析
                            parsed = parse_jsonb_bullets(sec["body"])
                            if parsed is not None:
                                row[sec_def.jsonb_column] = json.dumps(parsed, ensure_ascii=False)

                        elif sec_def.type == "table":
                            parsed = parse_md_table(sec["body"])
                            if parsed is not None:
                                row[sec_def.table_column] = json.dumps(parsed, ensure_ascii=False)

                        elif sec_def.type == "blockquote":
                            bq = parse_blockquotes(sec["body"])
                            for bqf in sec_def.blockquotes or []:
                                col = bqf.column
                                label = bqf.label or col
                                if label in bq:
                                    row[col] = bq[label]

                        elif sec_def.type == "raw":
                            row[sec_def.raw_column] = sec["body"]

                        elif sec_def.type == "acts":
                            act_labels = [a[0] for a in (sec_def.acts or [])]
                            parsed = parse_acts(sec["body"], act_labels)
                            if parsed:
                                for label, col_name in (sec_def.acts or []):
                                    if col_name in parsed:
                                        row[col_name] = json.dumps(parsed[col_name], ensure_ascii=False)

                    if not row.get(tpl.id_field) and not tpl.composite_id_fields and tpl.name != "world":
                        continue
                    if tpl.name == "world" and not row.get("name"):
                        continue

                    try:
                        self._upsert_row(tpl, row)
                        if tpl.name == "world":
                            key = f"{row.get('category', '?')}:{row.get('name', '?')}"
                        elif tpl.composite_id_fields:
                            key = "-".join(str(row.get(f, "?")) for f in tpl.composite_id_fields)
                        else:
                            key = str(row.get(tpl.id_field, "?"))
                        result["synced"] += 1
                        result["details"].append({"key": key, "file": os.path.basename(target_file)})
                    except Exception as e:
                        log.error(f"聚合解析失败 [{heading}]: {e}", exc_info=True)
                        result["errors"].append({"key": heading, "error": str(e)})

            except Exception as e:
                result["errors"].append({"file": os.path.basename(target_file), "error": str(e)})

        return result

    def _upsert_row(self, tpl: SyncTemplate, row: dict):
        """
        通用 upsert: 按 id_field（或 composite_id_fields）查找，
        存在则 UPDATE，不存在则 INSERT。
        """
        from .db import transaction
        # 确定主键字段列表
        if tpl.composite_id_fields:
            pk_fields = tpl.composite_id_fields
            pk_vals = [row.get(f) for f in pk_fields]
            if any(v is None for v in pk_vals):
                raise ValueError(f"缺少复合主键字段 {pk_fields}, row keys={list(row.keys())}")
        else:
            id_val = row.get(tpl.id_field)
            if not id_val:
                raise ValueError(f"缺少主标识字段 {tpl.id_field}")
            pk_fields = [tpl.id_field]
            pk_vals = [id_val]

        # 构建 WHERE 条件
        where_parts = ["novel_id = ?"] + [f"{f} = ?" for f in pk_fields]
        where_clause = " AND ".join(where_parts)
        where_params = [row["novel_id"]] + pk_vals

        with transaction():
            # 检查是否已存在
            existing = query(
                f"SELECT id FROM {tpl.db_table} WHERE {where_clause}",
                tuple(where_params), fetch="one"
            )

            # 收集 SET/INSERT 列（排除主键和 novel_id）
            exclude_cols = {"novel_id", "id"} | set(pk_fields)
            set_cols = []
            set_vals = []
            for col, val in row.items():
                if col in exclude_cols:
                    continue
                if not col or not col.strip():
                    continue
                if col == "data" and tpl.name == "world":
                    val = json.dumps(clean_data_for_storage(
                        json.loads(val) if isinstance(val, str) else val
                    ), ensure_ascii=False)
                set_cols.append(col)
                set_vals.append(val if val is not None else None)

            if not set_cols:
                return

            table_cols = self._get_table_columns(tpl.db_table)
            has_updated_at = "updated_at" in table_cols
            has_created_at = "created_at" in table_cols

            if existing:
                # UPDATE
                set_clause = ", ".join(f"{c} = ?" for c in set_cols)
                if has_updated_at:
                    sql = f"UPDATE {tpl.db_table} SET {set_clause}, updated_at = datetime('now') WHERE id = ?"
                else:
                    sql = f"UPDATE {tpl.db_table} SET {set_clause} WHERE id = ?"
                params = set_vals + [existing["id"]]
            else:
                # INSERT
                insert_cols = ["novel_id"] + pk_fields + set_cols
                insert_vals = [row["novel_id"]] + pk_vals + set_vals
                extra_cols = []
                extra_vals = []
                if has_created_at:
                    extra_cols.append("created_at")
                    extra_vals.append("datetime('now')")
                if has_updated_at:
                    extra_cols.append("updated_at")
                    extra_vals.append("datetime('now')")
                cols_str = ", ".join(insert_cols + extra_cols)
                placeholders = ", ".join(["?"] * len(insert_vals) + extra_vals)
                sql = f"INSERT INTO {tpl.db_table} ({cols_str}) VALUES ({placeholders})"
                params = insert_vals

            query(sql, tuple(params), fetch="none")

    # ── 双向对比 ────────────────────────────────────────────────

    def diff(self, novel_name: str, entity_type: str) -> dict:
        """
        对比DB和文件的差异。

        Returns:
            {"db_only": [], "file_only": [], "conflict": [], "consistent": []}
            conflict items include "source": "both_changed" | "file_changed" | "db_changed"
        """
        tpl = self.get(entity_type)
        novel_id = self._resolve_novel_id(novel_name)
        rows = self._query_entities(tpl, novel_id)

        results = {"db_only": [], "file_only": [], "conflict": [], "consistent": []}

        # 判断模式：与 db_to_files 一致，按 file_pattern 是否含 {name} 分派
        per_entity = not tpl.group_by or (tpl.file_pattern and "{name}" in tpl.file_pattern)

        if not per_entity:
            # 聚合模式：同一组多行→一个文件，hash 存在 group_key 下
            groups_seen: dict[str, list[dict]] = {}
            for row in rows:
                gk = str(row.get(tpl.group_by, "_default"))
                groups_seen.setdefault(gk, []).append(dict(row))

            for gk, group_rows in groups_seen.items():
                # group 模式下 db_to_files 用 group_key 存 hash
                fpath = self._resolve_filepath(tpl, novel_name, group_rows[0])
                if not os.path.exists(fpath):
                    for r in group_rows:
                        results["db_only"].append({"type": entity_type, "key": self._resolve_data_key(tpl, r)})
                    continue

                with open(fpath, "r", encoding="utf-8") as f:
                    file_hash = _compute_hash(f.read())

                stored = _get_hash_record(novel_id, tpl.name, gk)
                if stored and stored.get("last_sync_hash") and stored.get("last_sync_file_hash"):
                    # group 模式用聚合 db_hash（所有行拼接）
                    db_content = "\n".join(_db_row_to_hashable(r) for r in group_rows)
                    db_hash = _compute_hash(db_content)
                    db_changed = db_hash != stored["last_sync_hash"]
                    file_changed = file_hash != stored["last_sync_file_hash"]
                    if db_changed and file_changed:
                        results["conflict"].append({"type": entity_type, "key": gk,
                            "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                            "source": "both_changed"})
                    elif file_changed:
                        results["conflict"].append({"type": entity_type, "key": gk,
                            "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                            "source": "file_changed"})
                    elif db_changed:
                        results["conflict"].append({"type": entity_type, "key": gk,
                            "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                            "source": "db_changed"})
                    else:
                        results["consistent"].append({"type": entity_type, "key": gk})
                else:
                    results["conflict"].append({"type": entity_type, "key": gk,
                        "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                        "source": "unknown"})
        else:
            # per-entity 模式：逐行检查，hash 存在 data_key 下
            for row in rows:
                key = self._resolve_data_key(tpl, row)
                db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
                fpath = self._resolve_filepath(tpl, novel_name, row)

                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8") as f:
                        file_hash = _compute_hash(f.read())
                    stored = _get_hash_record(novel_id, tpl.name, key)
                    if stored and stored.get("last_sync_hash") and stored.get("last_sync_file_hash"):
                        db_changed = db_hash != stored["last_sync_hash"]
                        file_changed = file_hash != stored["last_sync_file_hash"]
                        if db_changed and file_changed:
                            results["conflict"].append({"type": entity_type, "key": key,
                                "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                                "source": "both_changed"})
                        elif file_changed:
                            results["conflict"].append({"type": entity_type, "key": key,
                                "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                                "source": "file_changed"})
                        elif db_changed:
                            results["conflict"].append({"type": entity_type, "key": key,
                                "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                                "source": "db_changed"})
                        else:
                            results["consistent"].append({"type": entity_type, "key": key})
                    else:
                        results["conflict"].append({"type": entity_type, "key": key,
                            "resolution": "DB→file" if tpl.authority == "db" else "file→DB",
                            "source": "unknown"})
                else:
                    results["db_only"].append({"type": entity_type, "key": key})

        # 文件中有但DB无的
        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        if os.path.isdir(base):
            for fname in os.listdir(base):
                if not fname.endswith(".md"):
                    continue
                fkey = fname.replace(".md", "")
                if fkey not in file_keys_seen:
                    results["file_only"].append({"type": entity_type, "key": fkey})

        return results

    def resolve_conflict(self, novel_name: str, entity_type: str,
                         entity_key: str, strategy: str) -> dict:
        """解决单个冲突。

        Args:
            strategy: "overwrite" (强制DB→文件) | "skip" (保留文件) | "reverse" (文件→DB)
        """
        tpl = self.get(entity_type)
        novel_id = self._resolve_novel_id(novel_name)

        if strategy == "overwrite":
            return self.db_to_files(novel_name, entity_type,
                                    entity_key=entity_key, overwrite=True)
        elif strategy == "skip":
            # 不写入，但更新 snapshot hash 使当前状态成为"已同步"
            rows = self._query_entities(tpl, novel_id, entity_key)
            if not rows:
                return {"error": f"实体不存在: {entity_key}"}
            fpath = self._resolve_filepath(tpl, novel_name, rows[0])
            db_hash = _compute_hash("\n".join(_db_row_to_hashable(dict(r)) for r in rows))
            hash_key = str(rows[0].get(tpl.group_by, "_default")) if tpl.group_by else self._resolve_data_key(tpl, rows[0])
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    file_hash = _compute_hash(f.read())
                _snapshot_sync_hashes(novel_id, tpl.name, hash_key, db_hash, file_hash)
            return {"resolved": entity_key, "strategy": "skip"}
        elif strategy == "reverse":
            return self.files_to_db(novel_name, entity_type)
        else:
            return {"error": f"未知策略: {strategy}。可选: overwrite/skip/reverse"}

    # ── 内部工具 ────────────────────────────────────────────────

    def roundtrip(self, novel_name: str, entity_type: str) -> dict:
        """
        双向无损验证：File→DB→File round-trip 测试。

        流程:
          1. 读取原始文件内容（hash_original）
          2. files_to_db() — 文件解析写入DB
          3. db_to_files(overwrite=True) — DB渲染写回文件
          4. 读取新文件内容（hash_roundtrip）
          5. 对比两个hash

        Returns:
          {"lossless": bool, "tested": int, "mismatches": [...]}
        """
        from .sync import _compute_hash

        tpl = self.get(entity_type)
        novel_id = self._resolve_novel_id(novel_name)
        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)

        if not os.path.isdir(base):
            return {"error": f"目录不存在: {base}"}

        # Phase 1: 收集所有待测文件的原始 hash
        original_hashes: dict[str, str] = {}
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".md"):
                continue
            if not self._match_file_pattern(tpl, fname):
                continue
            fpath = os.path.join(base, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                original_hashes[fname] = _compute_hash(f.read())

        if not original_hashes:
            return {"lossless": True, "tested": 0, "mismatches": [], "entity_type": entity_type}

        # Phase 2: File→DB→File（全局只执行一次）
        try:
            self.files_to_db(novel_name, entity_type)
            self.db_to_files(novel_name, entity_type, overwrite=True)
        except Exception as e:
            return {"lossless": False, "tested": 0, "error": str(e),
                    "mismatches": [], "entity_type": entity_type}

        # Phase 3: 逐文件对比 hash
        result = {"lossless": True, "tested": 0, "mismatches": [], "entity_type": entity_type}

        for fname, hash_original in sorted(original_hashes.items()):
            fpath = os.path.join(base, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    roundtrip_content = f.read()
                hash_roundtrip = _compute_hash(roundtrip_content)

                result["tested"] += 1
                if hash_original != hash_roundtrip:
                    result["lossless"] = False
                    result["mismatches"].append({
                        "file": fname,
                        "hash_original": hash_original,
                        "hash_roundtrip": hash_roundtrip,
                    })
            except Exception as e:
                result["mismatches"].append({"file": fname, "error": str(e)})
                result["lossless"] = False

        return result

    def _match_file_pattern(self, tpl: SyncTemplate, fname: str) -> bool:
        """检查文件名是否匹配模板的 file_pattern。

        支持:
          - 固定模式: "伏笔清单.md" → 精确匹配
          - 变量模式: "V{number}-{title}.md" → 转为正则匹配
          - "{name}.md" → 匹配任意 .md 文件（兜底）
        """
        pattern = tpl.file_pattern

        # 固定文件名（无变量占位符）
        if "{" not in pattern:
            return fname == pattern

        # {name}.md → 匹配所有 .md 文件（宽泛模式）
        if pattern == "{name}.md":
            return True

        # 变量模式 → 转为正则
        # 策略: 先将 {xxx} 占位符替换为通配符，再对剩余字面部分做 re.escape
        placeholder_map = {"{number}": r"\d+", "{title}": ".+", "{name}": ".+"}

        # 按 {xxx} 切分 pattern 为 literal segments 和 placeholders
        parts = re.split(r'(\{[^}]+\})', pattern)
        regex_parts = []
        for part in parts:
            if part in placeholder_map:
                regex_parts.append(placeholder_map[part])
            elif part.startswith("{") and part.endswith("}"):
                # 未知占位符 → 通配
                regex_parts.append(".+")
            else:
                # 字面部分 → 转义
                regex_parts.append(re.escape(part))

        regex = "^" + "".join(regex_parts) + "$"

        try:
            return re.match(regex, fname) is not None
        except re.error:
            return True  # 正则错误时兜底放行

    def _resolve_novel_id(self, novel_name: str) -> int:
        from .resolvers import _resolve_novel_id
        return _resolve_novel_id(novel_name)


# ============================================================================
# 全局引擎实例 — 纯 YAML manifest 驱动
# ============================================================================

engine = SyncEngine()

# 从 sync_manifests/ 加载 YAML manifests（必须成功，否则启动报错）
_MANIFESTS_DIR = os.path.join(PROJECT_ROOT, "sync_manifests")
if os.path.isdir(_MANIFESTS_DIR):
    loaded = engine.load_manifests(_MANIFESTS_DIR)
    if not loaded:
        raise RuntimeError(
            f"No YAML manifests loaded from {_MANIFESTS_DIR}. "
            "At least one manifest (character/world/foreshadow/volume/echo) is required."
        )
else:
    raise FileNotFoundError(
        f"Manifest directory not found: {_MANIFESTS_DIR}. "
        "Please create sync_manifests/ with at least one .yaml manifest."
    )
