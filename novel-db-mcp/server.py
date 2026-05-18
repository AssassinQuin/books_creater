"""Novel Writer MCP Server - FastMCP 3.x + PostgreSQL"""

from novel_db.db import mcp

from novel_db.tools_novel import (  # noqa: F401
    novel_create, novel_list, novel_get, novel_update,
)
from novel_db.tools_world import (  # noqa: F401
    world_upsert, world_query, world_delete, world_deactivate,
    sync_lorebook, seed_engine_data, engine_detail,
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
)
from novel_db.tools_chapter import (  # noqa: F401
    chapter_plan, chapter_list, chapter_save_summary, chapter_get_context,
    chapter_plan_batch, chapter_update_metadata,
    scene_create, scene_list,
    dimension_log, dimension_query,
    timeline_add, timeline_query,
)
from novel_db.tools_writing import (  # noqa: F401
    writing_start, writing_finish, validate_chapter, chapter_self_check,
    rule_detail, record_new_content, event_checklist,
    foreshadow_plant, foreshadow_recall, foreshadow_list, foreshadow_abandon,
    get_chapter_context,
)
from novel_db.tools_misc import (  # noqa: F401
    health_check, skill_loader, db_search,
    sync_startup, sync_db_to_files,
)

if __name__ == "__main__":
    mcp.run()
