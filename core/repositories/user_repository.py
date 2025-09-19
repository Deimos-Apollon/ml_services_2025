from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from core.entities.user import User
from core.entities.transaction import Transaction


class UserRepository(ABC):
    @abstractmethod
    def create_user(self, email: str, password_hash: str, is_admin: bool = False) -> User:...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:...

    @abstractmethod
    def add_balance(self, user_id: int, delta_cents: int) -> User:...

    @abstractmethod
    def debit_if_sufficient(self, user_id: int, amount_cents: int) -> User:...

    @abstractmethod
    def update_plan(self, user_id: int, plan: str) -> User:...

    @abstractmethod
    def log_transaction(self, user_id: int, type: str, amount_cents: int, balance_after: int,
                        metadata: Optional[Dict[str, Any]] = None) -> None:...

    @abstractmethod
    def list_transactions(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Transaction]:...
