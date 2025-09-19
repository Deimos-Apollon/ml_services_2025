from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Transaction:
    id: Optional[int]
    user_id: int
    type: str               # "topup" | "predict" | "debit"
    amount_cents: int       # пополнение: >0, списание: <0
    balance_after: int      # баланс после операции
    metadata: Optional[Dict[str, Any]]
    created_at: str
