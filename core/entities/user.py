from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: Optional[int]
    email: str
    password_hash: str
    is_admin: bool
    balance_cents: int
    created_at: str
    plan: str = "basic"  # basic | pro | premium
