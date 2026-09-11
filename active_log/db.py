import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content_html TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    tistory_url TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    published_at TEXT
);
CREATE TABLE IF NOT EXISTS runtime_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS view_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tistory_post_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    public_url TEXT,
    views INTEGER NOT NULL,
    captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_view_snapshots_post_time
    ON view_snapshots(tistory_post_id, captured_at DESC);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def save_post(self, post: dict) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO posts
                (topic_key, category, title, summary, content_html, tags_json, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    post["topic_key"], post["category"], post["title"], post["summary"],
                    post["content_html"], json.dumps(post["tags"], ensure_ascii=False),
                    json.dumps(post["sources"], ensure_ascii=False), datetime.now().isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def recent_topic_keys(self, limit: int | None = None) -> list[str]:
        with self.connect() as connection:
            query = "SELECT topic_key FROM posts ORDER BY id DESC"
            rows = connection.execute(
                query if limit is None else query + " LIMIT ?",
                () if limit is None else (limit,),
            ).fetchall()
        return [str(row["topic_key"]) for row in rows]

    def list_posts(self, limit: int = 50, *, oldest_first: bool = False) -> list[dict]:
        direction = "ASC" if oldest_first else "DESC"
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM posts ORDER BY id {direction} LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_post(self, post_id: int) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return dict(row) if row else None

    def update_post(self, post_id: int, post: dict) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                """UPDATE posts SET
                topic_key=?, category=?, title=?, summary=?, content_html=?,
                tags_json=?, sources_json=?,
                status=CASE WHEN status='failed' THEN 'draft' ELSE status END,
                error=CASE WHEN status='failed' THEN NULL ELSE error END
                WHERE id=?""",
                (
                    post["topic_key"], post["category"], post["title"], post["summary"],
                    post["content_html"], json.dumps(post["tags"], ensure_ascii=False),
                    json.dumps(post["sources"], ensure_ascii=False), post_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")

    def get_next_draft(self) -> dict | None:
        """Return the oldest queued draft so posts are published in FIFO order."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM posts WHERE status='draft' ORDER BY id ASC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def claim_post_for_publish(self, post_id: int) -> dict:
        """Atomically move one draft to publishing and return its contents."""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE posts SET status='publishing', error=NULL WHERE id=? AND status='draft'",
                (post_id,),
            )
            if cursor.rowcount != 1:
                row = connection.execute("SELECT status FROM posts WHERE id=?", (post_id,)).fetchone()
                if row is None:
                    raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")
                raise RuntimeError(
                    f"글 {post_id}은 게시 대기 상태가 아닙니다. 현재 상태: {row['status']}"
                )
            row = connection.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        return dict(row)

    def count_drafts(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM posts WHERE status='draft'"
            ).fetchone()
        return int(row["count"])

    def requeue_post(self, post_id: int) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE posts SET status='draft', error=NULL WHERE id=?", (post_id,)
            )
            if cursor.rowcount != 1:
                raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")

    def delete_post(self, post_id: int) -> None:
        with self.connect() as connection:
            row = connection.execute("SELECT status FROM posts WHERE id=?", (post_id,)).fetchone()
            if row is None:
                raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")
            if row["status"] == "publishing":
                raise RuntimeError("게시 중인 글은 삭제할 수 없습니다.")
            connection.execute("DELETE FROM posts WHERE id=?", (post_id,))

    def update_publish_result(self, post_id: int, *, status: str, url: str | None = None, error: str | None = None) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE posts SET status=?, tistory_url=?, error=?, published_at=? WHERE id=?",
                (status, url, error, datetime.now().isoformat() if status in {"private", "public"} else None, post_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")

    def set_state(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO runtime_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_state(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM runtime_state WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def save_view_snapshots(self, rows: list[dict]) -> int:
        """Store one point-in-time view count for each Tistory post."""
        captured_at = datetime.now().isoformat()
        valid_rows = [row for row in rows if row.get("views") is not None]
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO view_snapshots
                (tistory_post_id, title, public_url, views, captured_at)
                VALUES (?, ?, ?, ?, ?)""",
                [
                    (int(row["id"]), str(row.get("title", "")), row.get("url"),
                     int(row["views"]), captured_at)
                    for row in valid_rows
                ],
            )
        return len(valid_rows)

    def latest_view_stats(self, limit: int = 50) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT current.tistory_post_id AS id, current.title,
                    current.public_url AS url, current.views, current.captured_at,
                    current.views - COALESCE(previous.views, 0) AS delta
                FROM view_snapshots AS current
                LEFT JOIN view_snapshots AS previous
                  ON previous.tistory_post_id = current.tistory_post_id
                 AND previous.id = (
                    SELECT p.id FROM view_snapshots AS p
                    WHERE p.tistory_post_id = current.tistory_post_id AND p.id < current.id
                    ORDER BY p.id DESC LIMIT 1
                 )
                WHERE current.id IN (SELECT MAX(id) FROM view_snapshots GROUP BY tistory_post_id)
                ORDER BY current.views DESC, current.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
