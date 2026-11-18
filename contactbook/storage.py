"""SQLite operations. Every contact belongs to a workspace."""

from contextlib import closing
from pathlib import Path
import sqlite3
from uuid import uuid4


FIELDS = "id, name, research_group, research_topic, stage"


class ContactStore:
    def __init__(self, path: Path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    workspace TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    research_group TEXT NOT NULL,
                    research_topic TEXT NOT NULL,
                    stage TEXT NOT NULL CHECK (stage IN ('saved', 'contacted', 'following_up')),
                    PRIMARY KEY (workspace, id)
                )
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def list_contacts(self, workspace):
        with closing(self.connect()) as db:
            rows = db.execute(
                f"SELECT {FIELDS} FROM contacts WHERE workspace = ? ORDER BY name COLLATE NOCASE, id",
                (workspace,),
            )
            return [dict(row) for row in rows]

    def create(self, workspace, name, research_group, research_topic):
        contact_id = str(uuid4())
        with closing(self.connect()) as db, db:
            result = db.execute(
                f"""INSERT INTO contacts (workspace, id, name, research_group, research_topic, stage)
                    VALUES (?, ?, ?, ?, ?, 'saved') RETURNING {FIELDS}""",
                (workspace, contact_id, name, research_group, research_topic),
            ).fetchone()
            return dict(result)

    def find(self, workspace, contact_id):
        with closing(self.connect()) as db:
            row = db.execute(
                f"SELECT {FIELDS} FROM contacts WHERE workspace = ? AND id = ?",
                (workspace, contact_id),
            ).fetchone()
            return dict(row) if row else None

    def set_stage(self, workspace, contact_id, stage):
        with closing(self.connect()) as db, db:
            row = db.execute(
                f"UPDATE contacts SET stage = ? WHERE workspace = ? AND id = ? RETURNING {FIELDS}",
                (stage, workspace, contact_id),
            ).fetchone()
            return dict(row) if row else None
