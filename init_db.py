"""
init_db.py - Standalone Database Initialization Script for GovSchemeBot
Run this script to create the SQLite database schema and load schemes from schemes.csv.
Usage:
    python init_db.py
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_database_stats, DB_PATH, DEFAULT_CSV_PATH


def main():
    print("=" * 60)
    print("GovSchemeBot - Database Initialization")
    print("=" * 60)
    print(f"Reading schemes from: {DEFAULT_CSV_PATH}")
    print(f"Target SQLite database: {DB_PATH}")

    if not os.path.exists(DEFAULT_CSV_PATH):
        print(f"Error: Dataset not found at {DEFAULT_CSV_PATH}")
        sys.exit(1)

    count = init_db()
    stats = get_database_stats()

    print(f"\n[SUCCESS] Successfully initialized database!")
    print(f"Loaded {count} schemes across {stats['total_ministries']} ministries/departments.")
    print("=" * 60)


if __name__ == "__main__":
    main()
