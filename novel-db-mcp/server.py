"""Novel Writer MCP Server - FastMCP 3.x + SQLite (libsql)"""

from novel_db.db import mcp

from novel_db.tools_novel import (  # noqa: F401
    novel_create, novel_list, novel_get, novel_update,
)
from novel_db.tools_world import (  # noqa: F401
    world,
    author_voice, writing_spec,
)
from novel_db.tools_volume import (  # noqa: F401
    volume_create, volume_list, volume_get, volume_update,
)
from novel_db.tools_character import (  # noqa: F401
    character_create, character_list, character_get, character_update,
    character_state,
    relation,
    plot_thread,
    character_batch_detail,
)
from novel_db.tools_chapter import (  # noqa: F401
    chapter_plan, chapter_list, chapter_save_summary, get_chapter_context,
    scene, timeline,
)
from novel_db.tools_writing import (  # noqa: F401
    writing_finish, validate_chapter,
    rule_detail, record_new_content, event_checklist,
    foreshadow, echo, writing_rule,
)
from novel_db.tools_misc import (  # noqa: F401
    health_check, skill_loader, search, engine,
    sync, tool_stats,
)
from novel_db.tools_graph import (  # noqa: F401
    graph,
)
# vector tools are private helpers, accessed via search() dispatch in tools_misc
from novel_db.tools_distill import (  # noqa: F401
    distill,
    distillation,
)

if __name__ == "__main__":
    mcp.run()
