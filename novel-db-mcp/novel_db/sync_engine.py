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

from .db import query, PROJECT_ROOT
from .sync import (
    _is_empty, _jsonb_to_md, _parse_json_field,
    _render_md_table, _md_bullet,
    _record_db_hash, _record_file_hash,
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
    frow = query("SELECT name FROM world_settings WHERE id = %s", (val,), fetch="val")
    return frow or str(val)


def _resolve_chapter_number(val, row):
    """Transform: chapter_id → Ch{number} display."""
    if not val:
        return None
    ch = query("SELECT number FROM chapters WHERE id = %s", (val,), fetch="val")
    return f"Ch{ch}" if ch else str(val)


def _resolve_category_file(val, row):
    """Transform: category → 中文文件名（世界观专用）."""
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
        self._manifest_loaded: set[str] = set()  # 已加载的 manifest 路径

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

        result = {"synced": 0, "skipped": 0, "errors": []}
        for row in rows:
            try:
                did_write = self._sync_one_to_file(tpl, novel_id, novel_name, row, overwrite)
                if did_write:
                    result["synced"] += 1
                else:
                    result["skipped"] += 1
            except Exception as e:
                result["errors"].append({"key": row.get(tpl.id_field, "?"), "error": str(e)})

        return result

    def _query_entities(self, tpl: SyncTemplate, novel_id: int,
                        entity_key: str | None = None) -> list[dict]:
        """根据模板查询DB实体。"""
        sql = f"SELECT * FROM {tpl.db_table} WHERE novel_id = %s"
        params: list[Any] = [novel_id]

        if tpl.query_extra:
            sql += f" {tpl.query_extra}"
        if entity_key is not None:
            sql += f" AND {tpl.id_field} = %s"
            params.append(entity_key)
        if tpl.order_by:
            sql += f" ORDER BY {tpl.order_by}"

        return query(sql, tuple(params), fetch="all") or []

    def _resolve_filepath(self, tpl: SyncTemplate, novel_name: str, row: dict) -> str:
        """根据模板和DB行解析文件路径。支持 category_file_map（世界观专用）。"""
        fname = tpl.file_pattern

        # category_file_map 支持：{category_file} → 中文文件名
        if "{category_file}" in fname and "category" in row:
            cat = row["category"]
            if tpl.category_file_map and cat in tpl.category_file_map:
                fname = fname.replace("{category_file}", tpl.category_file_map[cat])
            elif tpl.transforms and "resolve_category_file" in tpl.transforms:
                fname = fname.replace("{category_file}", tpl.transforms["resolve_category_file"](cat, row))
            else:
                fname = fname.replace("{category_file}", str(cat))

        for col in [tpl.id_field, "title", "number", "category", "category_file"]:
            if col in row and f"{{{col}}}" in fname:
                val = row[col]
                if val is not None:
                    fname = fname.replace(f"{{{col}}}", str(val))

        base = os.path.join(_NOVELS_BASE, novel_name, tpl.file_dir)
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, fname)

    def _sync_one_to_file(self, tpl: SyncTemplate, novel_id: int,
                          novel_name: str, row: dict, overwrite: bool) -> bool:
        """将一行DB数据同步到文件。返回是否实际写入了文件。"""
        fpath = self._resolve_filepath(tpl, novel_name, row)

        # 跳过已有文件
        if os.path.exists(fpath) and tpl.skip_existing and not overwrite:
            _record_file_hash(novel_id, tpl.name, str(row.get(tpl.id_field, "")), "")
            return False

        # 渲染所有段落
        content_lines = []

        # 文件标题
        if tpl.header_template:
            title = tpl.header_template
            for col, val in row.items():
                if val is not None and f"{{{col}}}" in title:
                    title = title.replace(f"{{{col}}}", str(val))
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

        _record_file_hash(novel_id, tpl.name, str(row.get(tpl.id_field, "")), full_content)
        return True

    def _merge_section(self, tpl: SyncTemplate, fpath: str,
                       new_content: str, row: dict) -> str:
        """section_replace模式：替换文件中的匹配段落或追加。"""
        if not tpl.section_marker:
            return new_content

        with open(fpath, "r", encoding="utf-8") as f:
            existing = f.read()

        marker = tpl.section_marker
        for col, val in row.items():
            if val is not None and f"{{{col}}}" in marker:
                marker = marker.replace(f"{{{col}}}", str(val))

        if marker in existing:
            start = existing.index(marker)
            next_h2 = existing.find("\n## ", start + len(marker))
            if next_h2 == -1:
                next_h2 = len(existing)
            return existing[:start] + new_content + existing[next_h2:]
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

        return [f"\n## {heading}\n"] + lines

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
        """type=jsonb: 从JSONB列渲染嵌套bullet。"""
        col = sec.jsonb_column or sec.jsonb_key
        val = row.get(col)
        if _is_empty(val):
            # 尝试 fallback columns
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

        # section_replace 模式：需要处理聚合文件（多行→1文件）
        if tpl.merge_mode == "section_replace":
            return self._files_to_db_aggregate(tpl, novel_id, novel_name, base)

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
                key = str(row.get(tpl.id_field, fname))
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

    def _files_to_db_aggregate(self, tpl: SyncTemplate, novel_id: int,
                                novel_name: str, base: str) -> dict:
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

        # 查找匹配的文件（支持两种模式）
        target_files = []
        pattern = tpl.file_pattern

        # 模式1：固定文件名（如 "伏笔清单.md"）
        if "{" not in pattern:
            fpath = os.path.join(base, pattern)
            if os.path.isfile(fpath):
                target_files.append(fpath)
        else:
            # 模式2：含变量的文件名（如 "{category_file}.md"）
            # 扫描目录下所有 .md 文件
            for fname in sorted(os.listdir(base)):
                if not fname.endswith(".md"):
                    continue
                target_files.append(os.path.join(base, fname))

        if not target_files:
            return {"error": f"找不到匹配文件: {tpl.file_pattern} (目录: {base})"}

        result = {"synced": 0, "errors": [], "details": []}

        for target_file in target_files:
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()

                sections = split_sections(content)

                for sec in sections:
                    heading = sec["heading"]
                    if not sec["body"]:
                        continue

                    row = {"novel_id": novel_id}

                    # ── 确定实体标识 ──
                    if tpl.name in ("foreshadow", "echo"):
                        # "foreshadow: 123" → id=123
                        m = re.match(rf"{tpl.name}:\s*(\d+)", heading)
                        if m:
                            row[tpl.id_field] = int(m.group(1))
                        else:
                            continue

                    elif tpl.name == "world":
                        # "core_setting: 某个设定" → category=core_setting, name=某个设定
                        m = re.match(r'^(\w+):\s*(.+)$', heading)
                        if m:
                            row["category"] = m.group(1)
                            row["name"] = m.group(2).strip()
                        else:
                            continue

                    else:
                        # 通用：尝试从模板 heading 提取
                        continue

                    # ── 解析段落内容 ──
                    fields = parse_bullet_fields(sec["body"])

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

                    if not row.get(tpl.id_field) and tpl.name != "world":
                        continue
                    if tpl.name == "world" and not row.get("name"):
                        continue

                    try:
                        self._upsert_row(tpl, row)
                        if tpl.name == "world":
                            key = f"{row.get('category', '?')}:{row.get('name', '?')}"
                        else:
                            key = str(row[tpl.id_field])
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
        where_parts = ["novel_id = %s"] + [f"{f} = %s" for f in pk_fields]
        where_clause = " AND ".join(where_parts)
        where_params = [row["novel_id"]] + pk_vals

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
            set_cols.append(col)
            set_vals.append(val if val is not None else None)

        if existing:
            # UPDATE
            set_clause = ", ".join(f"{c} = %s" for c in set_cols)
            sql = f"UPDATE {tpl.db_table} SET {set_clause}, updated_at = NOW() WHERE id = %s"
            params = set_vals + [existing["id"]]
        else:
            # INSERT
            insert_cols = ["novel_id"] + pk_fields + set_cols
            insert_vals = [row["novel_id"]] + pk_vals + set_vals
            cols_str = ", ".join(insert_cols)
            placeholders = ", ".join(["%s"] * len(insert_vals))
            sql = f"INSERT INTO {tpl.db_table} ({cols_str}, created_at, updated_at) VALUES ({placeholders}, NOW(), NOW())"
            params = insert_vals

        query(sql, tuple(params), fetch="none")

    # ── 双向对比 ────────────────────────────────────────────────

    def diff(self, novel_name: str, entity_type: str) -> dict:
        """
        对比DB和文件的差异。

        Returns:
            {"db_only": [], "file_only": [], "conflict": [], "consistent": []}
        """
        from .sync import _compute_hash, _db_row_to_hashable

        tpl = self.get(entity_type)
        novel_id = self._resolve_novel_id(novel_name)
        rows = self._query_entities(tpl, novel_id)

        results = {"db_only": [], "file_only": [], "conflict": [], "consistent": []}

        file_keys_seen = set()
        for row in rows:
            key = str(row.get(tpl.id_field, ""))
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            fpath = self._resolve_filepath(tpl, novel_name, row)

            if os.path.exists(fpath):
                file_keys_seen.add(key)
                with open(fpath, "r", encoding="utf-8") as f:
                    file_hash = _compute_hash(f.read())
                if db_hash != file_hash:
                    results["conflict"].append({
                        "type": entity_type, "key": key,
                        "resolution": "DB→file" if tpl.authority == "db" else "file→DB"
                    })
                else:
                    results["consistent"].append({"type": entity_type, "key": key})
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
