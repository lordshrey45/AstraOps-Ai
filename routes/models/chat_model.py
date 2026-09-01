"""
Chat Model — Database access layer for the 'chat_history' table.

Provides CRUD operations for storing user-AI conversation logs.
Marked as "optional, nice-to-have" in the architecture.
Uses raw SQL via sqlite3 (no ORM) as per architecture.

Table schema:
    id          INTEGER PK AUTOINCREMENT
    user_id     INTEGER FK → users.id (nullable)
    message     TEXT NOT NULL (user's message)
    response    TEXT NOT NULL (Gemini's response)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

from models.db import get_db_connection, close_db


def save_chat_message(db_path, message, response, user_id=None):
    """
    Save a chat exchange (user message + AI response) to history.

    Args:
        db_path: Path to the SQLite database file.
        message: The user's message text.
        response: The Gemini AI's response text.
        user_id: ID of the logged-in user (None for anonymous chats).

    Returns:
        The ID of the newly saved chat record, or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO chat_history (user_id, message, response)
               VALUES (?, ?, ?)""",
            (user_id, message, response)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error saving chat message: {e}")
        return None
    finally:
        close_db(conn)


def get_chat_history_by_user(db_path, user_id, limit=50):
    """
    Retrieve chat history for a specific logged-in user.
    Used by GET /api/chat/history.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's ID.
        limit: Maximum number of messages to return (default: 50).

    Returns:
        A list of sqlite3.Row objects, ordered by most recent first.
    """
    conn = get_db_connection(db_path)
    try:
        history = conn.execute(
            """SELECT * FROM chat_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        return history
    finally:
        close_db(conn)


def get_recent_chat_context(db_path, user_id, limit=5):
    """
    Retrieve the most recent chat messages for context building.
    Used by gemini_service.py to include short chat history
    in the Gemini prompt for contextual responses.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's ID.
        limit: Number of recent exchanges to include (default: 5).

    Returns:
        A list of sqlite3.Row objects, ordered chronologically (oldest first).
    """
    conn = get_db_connection(db_path)
    try:
        # Get recent messages in reverse order, then reverse for chronological
        history = conn.execute(
            """SELECT message, response FROM chat_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        # Return in chronological order (oldest first) for prompt context
        return list(reversed(history))
    finally:
        close_db(conn)


def get_all_chat_history(db_path, limit=100):
    """
    Retrieve all chat history across all users.
    Useful for admin/analytics purposes.

    Args:
        db_path: Path to the SQLite database file.
        limit: Maximum number of records to return (default: 100).

    Returns:
        A list of sqlite3.Row objects.
    """
    conn = get_db_connection(db_path)
    try:
        history = conn.execute(
            """SELECT c.*, u.name as user_name
               FROM chat_history c
               LEFT JOIN users u ON c.user_id = u.id
               ORDER BY c.created_at DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return history
    finally:
        close_db(conn)


def delete_chat_history_by_user(db_path, user_id):
    """
    Delete all chat history for a specific user.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's ID.

    Returns:
        The number of records deleted.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM chat_history WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        return result.rowcount
    except Exception as e:
        conn.rollback()
        print(f"Error deleting chat history: {e}")
        return 0
    finally:
        close_db(conn)


def delete_chat_message(db_path, chat_id):
    """
    Delete a single chat message by its ID.

    Args:
        db_path: Path to the SQLite database file.
        chat_id: The chat record's primary key ID.

    Returns:
        True if deleted, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM chat_history WHERE id = ?", (chat_id,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting chat message: {e}")
        return False
    finally:
        close_db(conn)
