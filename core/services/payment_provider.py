from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from core.entities.user import User


@dataclass
class PaymentReceipt:
    success: bool
    amount_cents: int
    transaction_id: str
    message: Optional[str] = None

class PaymentProvider(ABC):
    @abstractmethod
    def charge(self, user: User, amount_cents: int) -> PaymentReceipt:...