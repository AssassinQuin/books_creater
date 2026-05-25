#!/usr/bin/env python3
"""一次性迁移脚本：验证 sentence-transformers 模型可用并预热缓存。

embedding 引擎采用懒加载策略（首次搜索时构建索引），本脚本用于：
1. 验证 sentence-transformers 可正常导入
2. 下载并缓存默认模型
3. 对现有数据做一次索引构建，验证搜索功能正常

用法：
  python scripts/migrate_embedding.py [--db-path data/novel.db]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    db_path = os.environ.get("LIBSQL_DB_PATH", "data/novel.db")
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    if "--db-path" in sys.argv:
        idx = sys.argv.index("--db-path")
        if idx + 1 < len(sys.argv):
            db_path = sys.argv[idx + 1]

    print("Step 1: Checking sentence-transformers...")
    try:
        from sentence_transformers import SentenceTransformer
        print("  OK: sentence-transformers imported")
    except ImportError as e:
        print(f"  FAIL: {e}")
        print("  Install with: pip install sentence-transformers")
        sys.exit(1)

    print("Step 2: Loading model (first run will download ~470MB)...")
    model_name = os.environ.get("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    t0 = time.time()
    model = SentenceTransformer(model_name)
    t1 = time.time()
    print(f"  OK: Model '{model_name}' loaded in {t1 - t0:.1f}s")

    if not os.path.exists(db_path):
        print(f"\nDB not found: {db_path}, skipping index test")
        print("Migration complete (model cached)")
        return

    print("Step 3: Testing index build with DB data...")
    from novel_db.db import query as db_query
    from novel_db.resolvers import _resolve_novel_id

    novels = db_query("SELECT id, name FROM novels")
    if not novels:
        print("  No novels in DB, skipping")
        return

    from novel_db.embedding import get_engine_for_novel, invalidate_cache

    for novel in novels:
        invalidate_cache(novel["id"])
        t0 = time.time()
        engine = get_engine_for_novel(novel["id"], db_query)
        t1 = time.time()
        doc_count = len(engine._documents)
        print(f"  Novel '{novel['name']}': {doc_count} documents indexed in {t1 - t0:.1f}s")

        if doc_count > 0:
            results = engine.search("灵衰症", top_k=3)
            print(f"  Test search '灵衰症': {len(results)} results")
            for r in results:
                print(f"    - {r['type']}:{r['name']} (score={r['score']})")

    print("\nMigration complete!")


if __name__ == "__main__":
    main()
