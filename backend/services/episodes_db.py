import json
import logging
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Fallback SQLite database for episodes
DB_PATH = "episodes.sqlite"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT,
                    detected_at TEXT,
                    finalized_at TEXT,
                    diagnosis TEXT,
                    confidence_score REAL,
                    anomaly_type TEXT,
                    trigger_index INTEGER,
                    trigger_timestamp INTEGER,
                    leads_data TEXT,
                    attention_weights TEXT,
                    status TEXT,
                    report_state TEXT
                )
            """)
            conn.commit()
            logger.info("Initialized Episodes SQLite database.")
    except Exception as e:
        logger.error(f"Failed to initialize Episodes SQLite database: {e}")

def save_episode(
    patient_id: str,
    detected_at: str,
    finalized_at: str,
    diagnosis: str,
    confidence_score: float,
    anomaly_type: str,
    trigger_index: int,
    trigger_timestamp: int,
    leads_data: List[List[float]],
    attention_weights: List[float]
) -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO episodes (
                    patient_id, detected_at, finalized_at, diagnosis, confidence_score,
                    anomaly_type, trigger_index, trigger_timestamp, leads_data, attention_weights,
                    status, report_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                detected_at,
                finalized_at,
                diagnosis,
                confidence_score,
                anomaly_type,
                trigger_index,
                trigger_timestamp,
                json.dumps(leads_data),
                json.dumps(attention_weights),
                "FROZEN",
                "PENDING"
            ))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Failed to save episode: {e}")
        return -1

def get_episodes_by_patient(patient_id: str) -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM episodes WHERE patient_id = ? ORDER BY id DESC", (patient_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        return []

def get_episode_by_id(episode_id: int) -> Optional[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Failed to get episode: {e}")
        return None

def update_episode_report(episode_id: int, report: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE episodes SET report_state = ? WHERE id = ?", (report, episode_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update episode report: {e}")
