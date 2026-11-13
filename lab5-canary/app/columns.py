"""Sortable ticket listings: the column name comes from a fixed allow-list, the values are bound."""
import sqlite3

SORTABLE = {"created": "created_at", "priority": "priority", "title": "title"}


def list_tickets(conn: sqlite3.Connection, status: str, sort: str) -> list[tuple]:
    """Tickets with the given status, sorted by one of the allow-listed columns."""
    column = SORTABLE.get(sort, "created_at")
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, title FROM tickets WHERE status = ? ORDER BY {column}", (status,))
    return cursor.fetchall()
