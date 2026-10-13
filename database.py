"""
database.py - Database Layer for GovSchemeBot
Handles SQLite schema management, CSV ingestion, and secure parameterized queries.
"""

import os
import sqlite3
import csv
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "schemes.db")
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "data", "schemes.csv")


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_db(csv_path: Optional[str] = None) -> int:
    """
    Initializes the SQLite database schema and imports schemes from CSV.
    Uses parameterized queries and handles duplicates gracefully.
    Returns the number of schemes loaded.
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create schemes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            scheme_id TEXT PRIMARY KEY,
            scheme_name TEXT NOT NULL,
            ministry TEXT,
            description TEXT,
            min_age INTEGER DEFAULT 0,
            max_age INTEGER DEFAULT 100,
            max_income INTEGER DEFAULT 0,
            eligible_categories TEXT DEFAULT 'ALL',
            eligible_occupations TEXT DEFAULT 'ALL',
            eligible_states TEXT DEFAULT 'ALL',
            eligible_genders TEXT DEFAULT 'ALL',
            disability_required TEXT DEFAULT 'NO',
            required_documents TEXT,
            official_url TEXT NOT NULL,
            data_source TEXT,
            last_updated TEXT
        )
    """)

    # Create indexes for search performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheme_name ON schemes(scheme_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_min_age ON schemes(min_age);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_max_age ON schemes(max_age);")

    inserted_count = 0
    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                min_age = int(row.get("min_age", 0) or 0)
                max_age = int(row.get("max_age", 100) or 100)
                max_income = int(row.get("max_income", 0) or 0)
                cursor.execute("""
                    INSERT OR REPLACE INTO schemes (
                        scheme_id, scheme_name, ministry, description,
                        min_age, max_age, max_income, eligible_categories,
                        eligible_occupations, eligible_states, eligible_genders,
                        disability_required, required_documents, official_url,
                        data_source, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get("scheme_id", "")).strip(),
                    str(row.get("scheme_name", "")).strip(),
                    str(row.get("ministry", "")).strip(),
                    str(row.get("description", "")).strip(),
                    min_age,
                    max_age,
                    max_income,
                    str(row.get("eligible_categories", "ALL")).strip(),
                    str(row.get("eligible_occupations", "ALL")).strip(),
                    str(row.get("eligible_states", "ALL")).strip(),
                    str(row.get("eligible_genders", "ALL")).strip(),
                    str(row.get("disability_required", "NO")).strip(),
                    str(row.get("required_documents", "Proof of Identity, Bank Details")).strip(),
                    str(row.get("official_url", "")).strip(),
                    str(row.get("data_source", "Government of India Portal")).strip(),
                    str(row.get("last_updated", "2024-01-01")).strip()
                ))
                inserted_count += 1

        conn.commit()
    conn.close()
    return inserted_count


def get_all_schemes() -> List[Dict[str, Any]]:
    """Retrieves all government schemes from the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes ORDER BY scheme_id ASC")
    rows = cursor.fetchall()
    schemes = [dict(row) for row in rows]
    conn.close()
    return schemes


def get_scheme_by_id(scheme_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single scheme by its unique ID using a parameterized query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_schemes(
    query: str = "",
    category: str = "",
    occupation: str = "",
    state: str = ""
) -> List[Dict[str, Any]]:
    """
    Search schemes using secure parameterized SQL filters.
    Protects against SQL injection attacks by strictly using `?` placeholders.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params: List[Any] = []

    if query.strip():
        search_pattern = f"%{query.strip()}%"
        conditions.append("(scheme_name LIKE ? OR description LIKE ? OR ministry LIKE ?)")
        params.extend([search_pattern, search_pattern, search_pattern])

    if category.strip() and category.upper() != "ALL":
        cat_pattern = f"%{category.strip()}%"
        conditions.append("(eligible_categories = 'ALL' OR eligible_categories LIKE ?)")
        params.append(cat_pattern)

    if occupation.strip() and occupation.upper() != "ALL":
        occ_pattern = f"%{occupation.strip()}%"
        conditions.append("(eligible_occupations = 'ALL' OR eligible_occupations LIKE ?)")
        params.append(occ_pattern)

    if state.strip() and state.upper() != "ALL":
        state_pattern = f"%{state.strip()}%"
        conditions.append("(eligible_states = 'ALL' OR eligible_states LIKE ?)")
        params.append(state_pattern)

    sql = "SELECT * FROM schemes"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY scheme_id ASC"

    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results


def get_database_stats() -> Dict[str, Any]:
    """Returns summary statistics for the database dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM schemes")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT ministry) AS ministries FROM schemes")
    ministries = cursor.fetchone()["ministries"]

    conn.close()
    return {
        "total_schemes": total,
        "total_ministries": ministries
    }
