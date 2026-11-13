"""Full-text-ish search over ticket titles for the agent console."""
import sqlite3


def search_titles(conn: sqlite3.Connection, needle: str, limit: int = 20) -> list[tuple]:
    """Tickets whose title contains `needle`, newest first."""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, title, priority FROM tickets WHERE title LIKE '%{needle}%' ORDER BY created_at DESC LIMIT {limit}"
    )
    return cursor.fetchall()
