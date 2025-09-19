import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from core.entities.user import User
from core.entities.transaction import Transaction
from core.repositories.user_repository import UserRepository

def init_db(db_path: str) -> None:
    if db_path != ":memory:" and not db_path.startswith("file:"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            balance_cents INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'basic'
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        conn.commit()
    finally:
        conn.close()

class SQLiteUserRepository(UserRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_admin=bool(row["is_admin"]),
            balance_cents=int(row["balance_cents"]),
            created_at=row["created_at"],
            plan=row["plan"],
        )

    def _row_to_tx(self, row: sqlite3.Row) -> Transaction:
        meta = None
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                meta = {"raw": row["metadata"]}
        return Transaction(
            id=row["id"],
            user_id=row["user_id"],
            type=row["type"],
            amount_cents=row["amount_cents"],
            balance_after=row["balance_after"],
            metadata=meta,
            created_at=row["created_at"],
        )

    def create_user(self, email: str, password_hash: str, is_admin: bool = False, plan: str = "basic") -> User:
        created_at = datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, is_admin, balance_cents, created_at, plan) VALUES (?, ?, ?, ?, ?, ?)",
            (email, password_hash, 1 if is_admin else 0, 0, created_at, plan),
        )
        self.conn.commit()
        user_id = cur.lastrowid
        return User(id=user_id, email=email, password_hash=password_hash,
                    is_admin=is_admin, balance_cents=0, created_at=created_at, plan=plan)

    def get_by_email(self, email: str) -> Optional[User]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone
        row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def add_balance(self, user_id: int, delta_cents: int) -> User:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
            (int(delta_cents), int(user_id)),
        )
        if cur.rowcount == 0:
            raise ValueError("User not found")
        self.conn.commit()
        user = self.get_by_id(user_id)
        assert user is not None
        return user

    def debit_if_sufficient(self, user_id: int, amount_cents: int) -> User:
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE users SET balance_cents = balance_cents - ? WHERE id = ? AND balance_cents >= ?",
            (int(amount_cents), int(user_id), int(amount_cents)),
        )
        if cur.rowcount == 0:
            if self.get_by_id(user_id) is None:
                raise ValueError("User not found")
            raise ValueError("Insufficient funds")
        self.conn.commit()
        user = self.get_by_id(user_id)
        assert user is not None
        return user

    def update_plan(self, user_id: int, plan: str) -> User:
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, int(user_id)))
        if cur.rowcount == 0:
            raise ValueError("User not found")
        self.conn.commit()
        user = self.get_by_id(user_id)
        assert user is not None
        return user

    # Новое: транзакции
    def log_transaction(self, user_id: int, type: str, amount_cents: int, balance_after: int, metadata: Optional[Dict[str, Any]] = None) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO transactions (user_id, type, amount_cents, balance_after, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (int(user_id), type, int(amount_cents), int(balance_after), meta_str, created_at),
        )
        self.conn.commit()

    def list_transactions(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Transaction]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (int(user_id), int(limit), int(offset)),
        )
        rows = cur.fetchall()
        return [self._row_to_tx(r) for r in rows]
