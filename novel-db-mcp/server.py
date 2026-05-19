"""Novel Writer MCP Server - FastMCP 3.x + SQLite (libsql)"""

from novel_db.db import mcp

from novel_db.tools_novel import (  # noqa: F401
    novel_create, novel_list, novel_get, novel_update,
)
from novel_db.tools_world import (  # noqa: F401
    world_upsert, world_query, world_load_context, world_batch_update_meta,
    world_delete, world_deactivate,
    sync_lorebook, engine_detail,
    author_voice, writing_spec,
)
from novel_db.tools_volume import (  # noqa: F401
    volume_create, volume_list, volume_get, volume_update,
)
from novel_db.tools_character import (  # noqa: F401
    character_create, character_list, character_get, character_detail,
    character_update, character_snapshot, character_get_latest,
    character_increment,
    relation_create, relation_list, relation_update, relation_snapshot,
    plot_thread_create, plot_thread_list, plot_thread_update,
    character_batch_detail,
    distillation_evolve, distillation_get, distillation_timeline, distillation_compare,
)
from novel_db.tools_chapter import (  # noqa: F401
    chapter_plan, chapter_list, chapter_save_summary, get_chapter_context,
    scene_create, scene_list, scene_update, scene_delete,
    dimension_log, dimension_query,
    timeline_add, timeline_query, timeline_update, timeline_delete,
)
from novel_db.tools_writing import (  # noqa: F401
    writing_finish, validate_chapter,
    rule_detail, record_new_content, event_checklist,
    foreshadow_plant, foreshadow_recall, foreshadow_list, foreshadow_update,
)
from novel_db.tools_misc import (  # noqa: F401
    health_check, skill_loader, db_search,
    sync_startup, sync_db_to_files, sync_files_to_db,
)

if __name__ == "__main__":
    mcp.run()
