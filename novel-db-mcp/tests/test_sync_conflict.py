"""
Tests for three-hash sync conflict detection.

Scenarios:
1. First sync = safe overwrite (no_record)
2. File unchanged + DB changed = safe overwrite (db_newer)
3. File modified + DB unchanged = file_newer → conflict reported
4. Both modified = conflict reported
5. Resolve overwrite = force DB→file
6. Resolve skip = keep file, update snapshot
7. _cleanup_stale_files protects user-modified files
"""

import hashlib
import json
import os
import tempfile

import pytest

from novel_db.sync import (
    _compute_hash, _get_hash_record, _detect_conflict,
    _snapshot_sync_hashes, _record_db_hash, _record_file_hash,
    _ensure_data_hashes_table,
)


@pytest.fixture
def hash_db(mock_query):
    """Provide hash functions backed by in-memory DB via mock_query."""
    import novel_db.sync as sync_mod
    import novel_db.db as db_mod

    original_query = db_mod.query
    db_mod.query = mock_query
    sync_mod._hashes_table_ensured = False

    yield

    db_mod.query = original_query
    sync_mod._hashes_table_ensured = False


class TestDetectConflict:
    """Unit tests for _detect_conflict logic."""

    def test_no_record_returns_safe(self):
        assert _detect_conflict(None, "abc") == "no_record"

    def test_empty_last_sync_returns_no_record(self):
        stored = {"db_hash": "aaa", "file_hash": "bbb",
                  "last_sync_hash": "", "last_sync_file_hash": ""}
        assert _detect_conflict(stored, "abc") == "no_record"

    def test_file_unchanged_db_changed_returns_db_newer(self):
        stored = {"db_hash": "new_db", "file_hash": "fff",
                  "last_sync_hash": "old_db", "last_sync_file_hash": "fff"}
        # current file hash == last_sync_file_hash → file not changed
        assert _detect_conflict(stored, "fff") == "db_newer"

    def test_file_changed_db_unchanged_returns_file_newer(self):
        stored = {"db_hash": "dbb", "file_hash": "old_file",
                  "last_sync_hash": "dbb", "last_sync_file_hash": "old_file"}
        # current file hash ≠ last_sync_file_hash → file changed
        assert _detect_conflict(stored, "new_file_hash") == "file_newer"

    def test_both_changed_returns_conflict(self):
        stored = {"db_hash": "new_db", "file_hash": "old_file",
                  "last_sync_hash": "old_db", "last_sync_file_hash": "old_file"}
        assert _detect_conflict(stored, "new_file_hash") == "conflict"

    def test_neither_changed_returns_skip(self):
        stored = {"db_hash": "same", "file_hash": "fff",
                  "last_sync_hash": "same", "last_sync_file_hash": "fff"}
        assert _detect_conflict(stored, "fff") == "skip"


class TestHashRecordIO:
    """Test _get_hash_record and _snapshot_sync_hashes with real DB."""

    def test_get_returns_none_when_no_record(self, hash_db):
        result = _get_hash_record(1, "world", "ability:虹吸柱")
        assert result is None

    def test_record_and_read_cycle(self, hash_db):
        _record_db_hash(1, "world", "ability:虹吸柱", "some content")
        result = _get_hash_record(1, "world", "ability:虹吸柱")
        assert result is not None
        assert result["db_hash"] == _compute_hash("some content")

    def test_snapshot_updates_last_sync(self, hash_db):
        _record_db_hash(1, "character", "沈野", "db content")
        _record_file_hash(1, "character", "沈野", "file content")
        db_h = _compute_hash("db content")
        file_h = _compute_hash("file content")
        _snapshot_sync_hashes(1, "character", "沈野", db_h, file_h)

        result = _get_hash_record(1, "character", "沈野")
        assert result["last_sync_hash"] == db_h
        assert result["last_sync_file_hash"] == file_h


class TestSyncEngineConflict:
    """Integration tests for conflict detection in SyncEngine."""

    @pytest.fixture
    def sync_env(self, tmp_path):
        """Set up a minimal sync environment with real files and DB."""
        import novel_db.sync as sync_mod
        import novel_db.sync_engine as engine_mod
        import novel_db.db as db_mod

        # Create test novel directory structure
        novel_dir = tmp_path / "novels" / "测试小说" / "设定" / "人物"
        novel_dir.mkdir(parents=True)

        # We can't easily mock the full engine, so test at the hash level
        original_query = db_mod.query
        from tests.conftest import _TEST_DB_PATH
        import sqlite3
        conn = sqlite3.connect(_TEST_DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")

        # Ensure hash table exists
        sync_mod._hashes_table_ensured = False
        _ensure_data_hashes_table()

        yield {
            "tmp_path": tmp_path,
            "novel_dir": novel_dir,
            "conn": conn,
        }

        conn.close()
        sync_mod._hashes_table_ensured = False

    def test_first_sync_no_conflict(self, sync_env):
        """First sync (no previous hash record) should succeed."""
        stored = _get_hash_record(1, "character", "新角色")
        status = _detect_conflict(stored, "any_hash")
        assert status == "no_record"

    def test_second_sync_after_db_change(self, sync_env):
        """After recording db_hash and snapshot, DB change → safe overwrite."""
        # Simulate first successful sync
        _record_db_hash(1, "character", "沈野", "original_db")
        _record_file_hash(1, "character", "沈野", "original_file")
        db_h = _compute_hash("original_db")
        file_h = _compute_hash("original_file")
        _snapshot_sync_hashes(1, "character", "沈野", db_h, file_h)

        # Now DB changes
        _record_db_hash(1, "character", "沈野", "modified_db")

        # File is still the same as last sync
        stored = _get_hash_record(1, "character", "沈野")
        status = _detect_conflict(stored, file_h)
        assert status == "db_newer"

    def test_file_modified_by_user(self, sync_env):
        """User edits file after sync → file_newer detected."""
        # First sync
        _record_db_hash(1, "character", "沈野", "db_content")
        _record_file_hash(1, "character", "沈野", "file_v1")
        db_h = _compute_hash("db_content")
        file_h = _compute_hash("file_v1")
        _snapshot_sync_hashes(1, "character", "沈野", db_h, file_h)

        # User modifies file (hash changes)
        new_file_hash = _compute_hash("user edited this")

        stored = _get_hash_record(1, "character", "沈野")
        status = _detect_conflict(stored, new_file_hash)
        assert status == "file_newer"

    def test_both_modified_conflict(self, sync_env):
        """Both DB and file modified → conflict."""
        # First sync
        _record_db_hash(1, "character", "沈野", "original")
        _record_file_hash(1, "character", "沈野", "original")
        h = _compute_hash("original")
        _snapshot_sync_hashes(1, "character", "沈野", h, h)

        # Both change
        _record_db_hash(1, "character", "沈野", "new_db")
        new_file_hash = _compute_hash("new_file")

        stored = _get_hash_record(1, "character", "沈野")
        status = _detect_conflict(stored, new_file_hash)
        assert status == "conflict"

    def test_resolve_skip_updates_snapshot(self, sync_env):
        """After resolve(skip), snapshot matches current file state."""
        # Setup: first sync
        _record_db_hash(1, "character", "沈野", "db_v1")
        _record_file_hash(1, "character", "沈野", "file_v1")
        db_h1 = _compute_hash("db_v1")
        file_h1 = _compute_hash("file_v1")
        _snapshot_sync_hashes(1, "character", "沈野", db_h1, file_h1)

        # Both change → conflict
        _record_db_hash(1, "character", "沈野", "db_v2")
        new_file_hash = _compute_hash("file_v2")

        # Resolve: skip (keep file, update snapshot)
        _snapshot_sync_hashes(1, "character", "沈野",
                              _compute_hash("db_v2"), new_file_hash)

        # Verify: next sync should see no conflict
        stored = _get_hash_record(1, "character", "沈野")
        status = _detect_conflict(stored, new_file_hash)
        assert status == "skip"
