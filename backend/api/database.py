"""
SQLite database for time-series storage of grid data.
Stores historical readings for charts and analysis.
"""

import os
import json
import time
import sqlite3
import logging
from typing import Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grid_data.db")


def get_db_path():
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS grid_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                step INTEGER NOT NULL,
                hour_of_day REAL NOT NULL,
                scenario TEXT NOT NULL DEFAULT 'baseline',
                solar_total_kw REAL,
                house_total_kw REAL,
                ev_total_kw REAL,
                battery_soc REAL,
                battery_power_kw REAL,
                net_import_kw REAL,
                import_price REAL,
                step_cost REAL,
                total_cost REAL,
                blackout INTEGER DEFAULT 0,
                ai_action TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            );

            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                step INTEGER NOT NULL,
                controller TEXT NOT NULL,
                battery_action REAL,
                ev_throttle REAL,
                reason TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            );

            CREATE TABLE IF NOT EXISTS scenario_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario TEXT NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL,
                total_cost REAL,
                blackout_count INTEGER,
                total_steps INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_step ON grid_snapshots(step);
            CREATE INDEX IF NOT EXISTS idx_snapshots_scenario ON grid_snapshots(scenario);
            CREATE INDEX IF NOT EXISTS idx_actions_step ON action_log(step);
        """)
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")


def save_snapshot(state: dict, action: Optional[dict] = None):
    """Save a grid state snapshot."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO grid_snapshots 
            (timestamp, step, hour_of_day, scenario, solar_total_kw, house_total_kw,
             ev_total_kw, battery_soc, battery_power_kw, net_import_kw,
             import_price, step_cost, total_cost, blackout, ai_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.time(),
            state.get("timestamp", 0),
            state.get("hour_of_day", 0),
            state.get("scenario", "baseline"),
            state.get("solar", {}).get("total_kw", 0),
            state.get("houses", {}).get("total_kw", 0),
            state.get("ev_chargers", {}).get("total_kw", 0),
            state.get("battery", {}).get("soc", 0),
            state.get("grid", {}).get("battery_power_kw", 0),
            state.get("grid", {}).get("net_import_kw", 0),
            state.get("price", {}).get("import_rate", 0),
            state.get("metrics", {}).get("step_cost", 0),
            state.get("metrics", {}).get("total_cost", 0),
            1 if state.get("grid", {}).get("blackout", False) else 0,
            json.dumps(action) if action else None,
        ))
        conn.commit()


def save_action(step: int, action: dict):
    """Save an AI/controller action."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO action_log (timestamp, step, controller, battery_action, ev_throttle, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            time.time(), step,
            action.get("controller", "unknown"),
            action.get("battery_action", 0),
            action.get("ev_throttle", 1),
            action.get("reason", ""),
        ))
        conn.commit()


def get_recent_snapshots(limit: int = 200, scenario: Optional[str] = None) -> List[dict]:
    """Get recent grid snapshots for charts."""
    with get_connection() as conn:
        if scenario:
            rows = conn.execute(
                "SELECT * FROM grid_snapshots WHERE scenario = ? ORDER BY id DESC LIMIT ?",
                (scenario, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM grid_snapshots ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_recent_actions(limit: int = 50) -> List[dict]:
    """Get recent AI actions."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM action_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_scenario_comparison() -> dict:
    """Get comparison metrics between scenarios."""
    with get_connection() as conn:
        scenarios = {}
        for scenario in ["baseline", "ai", "stress"]:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_steps,
                    COALESCE(SUM(step_cost), 0) as total_cost,
                    COALESCE(SUM(blackout), 0) as blackout_count,
                    COALESCE(AVG(battery_soc), 0) as avg_battery_soc,
                    COALESCE(AVG(net_import_kw), 0) as avg_net_import
                FROM grid_snapshots WHERE scenario = ?
            """, (scenario,)).fetchone()
            if row and row["total_steps"] > 0:
                scenarios[scenario] = dict(row)
        return scenarios
