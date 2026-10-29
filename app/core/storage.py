# -*- coding: utf-8 -*-
"""SQLite storage for the desktop pet.

All runtime data lives under %APPDATA%/YunPet, not in the project folder.
"""

import os
import sqlite3
from datetime import datetime


def _now():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


class Storage:
    def __init__(self, db_path=None):
        if db_path is None:
            base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "YunPet")
            os.makedirs(base, exist_ok=True)
            db_path = os.path.join(base, "yunpet.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT,
                place TEXT DEFAULT '',
                note TEXT DEFAULT '',
                source TEXT DEFAULT 'local',
                external_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TEXT,
                priority TEXT DEFAULT '中',
                done INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                source TEXT DEFAULT 'local',
                external_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                sender TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                snippet TEXT DEFAULT '',
                received_at TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                is_notified INTEGER DEFAULT 0,
                raw_json TEXT DEFAULT '',
                UNIQUE(provider, external_id)
            );
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                to_addr TEXT NOT NULL,
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_at TEXT,
                sent_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT '新对话',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_state (
                conversation_id INTEGER PRIMARY KEY,
                last_intent TEXT DEFAULT '',
                last_date TEXT DEFAULT '',
                last_event TEXT DEFAULT '',
                summary TEXT DEFAULT ''
            );
            """
        )
        self.conn.commit()

    # ---------------- events ----------------
    def add_event(self, title, start_at, end_at="", place="", note="", source="local", external_id=None):
        cur = self.conn.execute(
            "INSERT INTO events(title,start_at,end_at,place,note,source,external_id,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (title, start_at, end_at, place, note, source, external_id, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_event(self, event_id, title, start_at, end_at="", place="", note=""):
        self.conn.execute(
            "UPDATE events SET title=?,start_at=?,end_at=?,place=?,note=? WHERE id=?",
            (title, start_at, end_at, place, note, event_id),
        )
        self.conn.commit()

    def delete_event(self, event_id):
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.conn.commit()

    def list_events(self, start=None, end=None):
        q = "SELECT * FROM events"
        args = []
        if start and end:
            q += " WHERE start_at>=? AND start_at<?"
            args = [start, end]
        q += " ORDER BY start_at"
        return [dict(r) for r in self.conn.execute(q, args)]

    # ---------------- todos ----------------
    def add_todo(self, title, due_at=None, priority="中", note="", source="local", external_id=None):
        cur = self.conn.execute(
            "INSERT INTO todos(title,due_at,priority,done,note,source,external_id,created_at) "
            "VALUES(?,?,?,0,?,?,?,?)",
            (title, due_at, priority, note, source, external_id, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_todo(self, todo_id, title, due_at=None, priority="中", note=""):
        self.conn.execute(
            "UPDATE todos SET title=?,due_at=?,priority=?,note=? WHERE id=?",
            (title, due_at, priority, note, todo_id),
        )
        self.conn.commit()

    def set_todo_done(self, todo_id, done=True):
        self.conn.execute("UPDATE todos SET done=? WHERE id=?", (1 if done else 0, todo_id))
        self.conn.commit()

    def delete_todo(self, todo_id):
        self.conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        self.conn.commit()

    def list_todos(self, done=None):
        q = "SELECT * FROM todos"
        args = []
        if done is not None:
            q += " WHERE done=?"
            args = [1 if done else 0]
        q += " ORDER BY (due_at IS NULL), due_at, priority"
        return [dict(r) for r in self.conn.execute(q, args)]

    def next_todo(self):
        row = self.conn.execute(
            "SELECT * FROM todos WHERE done=0 AND due_at IS NOT NULL AND due_at<>'' "
            "ORDER BY due_at ASC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # ---------------- notes ----------------
    def list_notes(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM notes ORDER BY updated_at DESC")]

    def get_note(self, note_id):
        row = self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        return dict(row) if row else None

    def save_note(self, note_id, title, body):
        if note_id:
            self.conn.execute(
                "UPDATE notes SET title=?,body=?,updated_at=? WHERE id=?",
                (title, body, _now(), note_id),
            )
            self.conn.commit()
            return note_id
        cur = self.conn.execute(
            "INSERT INTO notes(title,body,updated_at) VALUES(?,?,?)",
            (title, body, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_note(self, note_id):
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    # ---------------- messages ----------------
    def add_message(self, provider, external_id, sender, subject, snippet="", received_at=None, raw_json=""):
        """Insert if new. Returns (row, is_new)."""
        received_at = received_at or _now()
        try:
            cur = self.conn.execute(
                "INSERT INTO messages(provider,external_id,sender,subject,snippet,received_at,raw_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (provider, external_id, sender, subject, snippet, received_at, raw_json),
            )
            self.conn.commit()
            row = self.conn.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
            return dict(row), True
        except sqlite3.IntegrityError:
            row = self.conn.execute(
                "SELECT * FROM messages WHERE provider=? AND external_id=?",
                (provider, external_id),
            ).fetchone()
            return (dict(row) if row else None), False

    def mark_message_notified(self, message_id):
        self.conn.execute("UPDATE messages SET is_notified=1 WHERE id=?", (message_id,))
        self.conn.commit()

    def list_unread_messages(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM messages WHERE is_read=0 ORDER BY received_at DESC"
        )]

    # ---------------- drafts ----------------
    def add_draft(self, provider, to_addr, subject, body):
        cur = self.conn.execute(
            "INSERT INTO drafts(provider,to_addr,subject,body,status,created_at) "
            "VALUES(?,?,?,?,'pending',?)",
            (provider, to_addr, subject, body, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def approve_draft(self, draft_id):
        self.conn.execute(
            "UPDATE drafts SET status='approved',approved_at=? WHERE id=? AND status='pending'",
            (_now(), draft_id),
        )
        self.conn.commit()

    def mark_draft_sent(self, draft_id):
        self.conn.execute(
            "UPDATE drafts SET status='sent',sent_at=? WHERE id=?",
            (_now(), draft_id),
        )
        self.conn.commit()

    def list_pending_drafts(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM drafts WHERE status IN ('pending','approved') ORDER BY created_at DESC"
        )]

    # ---------------- chat ----------------
    def create_conversation(self, title="新对话"):
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO chat_conversations(title,created_at,updated_at) VALUES(?,?,?)",
            (title, now, now),
        )
        self.conn.commit()
        self.conn.execute(
            "INSERT OR IGNORE INTO chat_state(conversation_id) VALUES(?)", (cur.lastrowid,))
        self.conn.commit()
        return cur.lastrowid

    def latest_conversation(self):
        row = self.conn.execute(
            "SELECT * FROM chat_conversations ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def list_conversations(self):
        rows = self.conn.execute(
            "SELECT c.*, "
            "(SELECT COUNT(*) FROM chat_turns t WHERE t.conversation_id=c.id) AS turn_count, "
            "(SELECT t.content FROM chat_turns t WHERE t.conversation_id=c.id "
            " ORDER BY t.id DESC LIMIT 1) AS last_content "
            "FROM chat_conversations c ORDER BY c.updated_at DESC, c.id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_conversation(self, conversation_id):
        self.conn.execute("DELETE FROM chat_turns WHERE conversation_id=?", (conversation_id,))
        self.conn.execute("DELETE FROM chat_state WHERE conversation_id=?", (conversation_id,))
        self.conn.execute("DELETE FROM chat_conversations WHERE id=?", (conversation_id,))
        self.conn.commit()

    def delete_all_conversations(self):
        self.conn.execute("DELETE FROM chat_turns")
        self.conn.execute("DELETE FROM chat_state")
        self.conn.execute("DELETE FROM chat_conversations")
        self.conn.commit()

    def add_chat_turn(self, conversation_id, role, content, token_count=0):
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO chat_turns(conversation_id,role,content,token_count,created_at) "
            "VALUES(?,?,?,?,?)",
            (conversation_id, role, content, token_count, now),
        )
        self.conn.execute(
            "UPDATE chat_conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        if role == "user":
            row = self.conn.execute(
                "SELECT title FROM chat_conversations WHERE id=?", (conversation_id,)
            ).fetchone()
            if row and (not row["title"] or row["title"] == "新对话"):
                title = (content or "").strip().replace("\n", " ")[:24] or "新对话"
                self.conn.execute(
                    "UPDATE chat_conversations SET title=? WHERE id=?",
                    (title, conversation_id),
                )
        self.conn.commit()
        return cur.lastrowid

    def list_chat_turns(self, conversation_id, limit=None):
        if limit:
            rows = self.conn.execute(
                "SELECT * FROM (SELECT * FROM chat_turns WHERE conversation_id=? "
                "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM chat_turns WHERE conversation_id=? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_chat_state(self, conversation_id):
        row = self.conn.execute(
            "SELECT * FROM chat_state WHERE conversation_id=?", (conversation_id,)
        ).fetchone()
        if row:
            return dict(row)
        return {"conversation_id": conversation_id, "last_intent": "",
                "last_date": "", "last_event": "", "summary": ""}

    def set_chat_state(self, conversation_id, **kw):
        cur = self.get_chat_state(conversation_id)
        cur.update({k: v for k, v in kw.items() if k in
                    ("last_intent", "last_date", "last_event", "summary")})
        self.conn.execute(
            "INSERT INTO chat_state(conversation_id,last_intent,last_date,last_event,summary) "
            "VALUES(?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET "
            "last_intent=excluded.last_intent,last_date=excluded.last_date,"
            "last_event=excluded.last_event,summary=excluded.summary",
            (conversation_id, cur["last_intent"], cur["last_date"],
             cur["last_event"], cur["summary"]),
        )
        self.conn.commit()

    # ---------------- settings ----------------
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
