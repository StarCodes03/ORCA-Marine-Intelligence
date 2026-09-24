"""ORCA Marine Intelligence - Persistent Storage Repository

Provides a clean storage abstraction supporting local SQLite by default,
in-memory mode for isolated testing, and optional PostgreSQL for production.
Persists multi-turn conversations, individual message turns, custom vessel profiles,
and deterministic maritime alerts.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import threading
from app.config.risk_thresholds import VESSEL_PROFILES

logger = logging.getLogger("orca.services.storage")


class StorageRepository:
    """Thread-safe storage repository using SQLite."""

    def __init__(self, db_url: Optional[str] = None):
        url = db_url or os.getenv("DATABASE_URL", "sqlite:///./orca_marine.db")
        if url.startswith("sqlite:///"):
            self.db_path = url.replace("sqlite:///", "")
        elif url == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = "./orca_marine.db"

        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        """Create schema tables if they do not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Conversations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                context_json TEXT NOT NULL
            )
        """)

        # Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                timestamp TEXT NOT NULL,
                metadata_json TEXT
            )
        """)

        # Vessel Profiles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vessel_profiles (
                vessel_type TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                is_custom INTEGER DEFAULT 0
            )
        """)

        # Alerts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                zone_id TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        conn.commit()

        # Seed built-in profiles if empty
        cursor.execute("SELECT COUNT(*) FROM vessel_profiles")
        if cursor.fetchone()[0] == 0:
            for v_type, prof in VESSEL_PROFILES.items():
                cursor.execute(
                    "INSERT INTO vessel_profiles (vessel_type, name, parameters_json, is_custom) VALUES (?, ?, ?, 0)",
                    (v_type, prof.get("name", v_type), json.dumps(prof))
                )
            conn.commit()
            logger.info("[StorageRepository] Seeded built-in vessel seaworthiness profiles.")

    # 1. Conversations Persistence
    def save_conversation(self, conversation_id: str, context: Dict[str, Any]) -> None:
        """Upsert conversation context state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        ctx_str = json.dumps(context)

        cursor.execute("""
            INSERT INTO conversations (conversation_id, created_at, updated_at, context_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                context_json = excluded.context_json
        """, (conversation_id, now, now, ctx_str))
        conn.commit()

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation context state."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT context_json FROM conversations WHERE conversation_id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["context_json"])
        return None

    def list_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List active conversation sessions sorted by recent activity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT conversation_id, created_at, updated_at, context_json
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        results = []
        for row in cursor.fetchall():
            ctx = json.loads(row["context_json"])
            results.append({
                "conversation_id": row["conversation_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "location": ctx.get("location"),
                "vessel_type": ctx.get("vessel_type"),
                "turn_count": ctx.get("turn_count", 0)
            })
        return results

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and related messages."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
        conv_deleted = cursor.rowcount > 0
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM alerts WHERE conversation_id = ?", (conversation_id,))
        conn.commit()
        return conv_deleted

    # 2. Message History
    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Append message turn to message history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata) if metadata else None
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, intent, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conversation_id, role, content, intent, now, meta_str))
        conn.commit()
        return cursor.lastrowid

    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve message history for conversation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, role, content, intent, timestamp, metadata_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (conversation_id, limit))
        return [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "intent": r["intent"],
                "timestamp": r["timestamp"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else None
            }
            for r in cursor.fetchall()
        ]

    # 3. Custom Vessel Profiles
    def save_vessel_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a custom vessel seaworthiness profile."""
        conn = self._get_connection()
        cursor = conn.cursor()
        v_type = profile["vessel_type"]
        v_name = profile.get("name", v_type.replace("_", " ").title())
        is_custom = 1 if profile.get("is_custom", True) else 0

        cursor.execute("""
            INSERT INTO vessel_profiles (vessel_type, name, parameters_json, is_custom)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(vessel_type) DO UPDATE SET
                name = excluded.name,
                parameters_json = excluded.parameters_json,
                is_custom = excluded.is_custom
        """, (v_type, v_name, json.dumps(profile), is_custom))
        conn.commit()
        return profile

    def get_vessel_profiles(self) -> List[Dict[str, Any]]:
        """List all available vessel profiles (built-in and custom)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT parameters_json FROM vessel_profiles ORDER BY is_custom ASC, name ASC")
        return [json.loads(r["parameters_json"]) for r in cursor.fetchall()]

    def get_vessel_profile(self, vessel_type: str) -> Optional[Dict[str, Any]]:
        """Get specific vessel profile by key."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT parameters_json FROM vessel_profiles WHERE vessel_type = ?", (vessel_type,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["parameters_json"])
        return None

    # 4. Alerts
    def save_alert(self, alert: Dict[str, Any]) -> None:
        """Persist structured maritime alert."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = alert.get("created_at") or datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO alerts (id, conversation_id, severity, title, message, zone_id, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert["id"],
            alert.get("conversation_id"),
            alert["severity"],
            alert["title"],
            alert["message"],
            alert.get("zone_id"),
            now,
            1 if alert.get("is_active", True) else 0
        ))
        conn.commit()

    def get_active_alerts(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active alerts, optionally filtered by conversation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        if conversation_id:
            cursor.execute("""
                SELECT id, conversation_id, severity, title, message, zone_id, created_at, is_active
                FROM alerts
                WHERE is_active = 1 AND (conversation_id = ? OR conversation_id IS NULL)
                ORDER BY created_at DESC
            """, (conversation_id,))
        else:
            cursor.execute("""
                SELECT id, conversation_id, severity, title, message, zone_id, created_at, is_active
                FROM alerts
                WHERE is_active = 1
                ORDER BY created_at DESC
            """)
        return [dict(r) for r in cursor.fetchall()]


# Singleton storage repository instance
storage_repo = StorageRepository()
