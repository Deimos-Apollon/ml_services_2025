from typing import Optional
from passlib.context import CryptContext
from core.entities.user import User
from core.repositories.user_repository import UserRepository
from core.services.payment_provider import PaymentProvider


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def register_user(repo: UserRepository, email: str, password: str, is_admin: bool = False) -> User:
    email = email.strip().lower()
    existing = repo.get_by_email(email)
    if existing is not None:
        raise ValueError("User with this email already exists")
    password_hash = get_password_hash(password)
    user = repo.create_user(email=email, password_hash=password_hash, is_admin=is_admin)
    return user

def authenticate_user(repo: UserRepository, email: str, password: str) -> Optional[User]:
    email = email.strip().lower()
    user = repo.get_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def top_up_balance(repo: UserRepository, provider: PaymentProvider, user: User, amount_cents: int) -> User:
    if amount_cents <= 0:
        raise ValueError("Amount must be positive")
    receipt = provider.charge(user, amount_cents)
    if not receipt.success:
        raise ValueError("Payment failed")
    updated = repo.add_balance(user.id, receipt.amount_cents)

    # логгируем транзакцию
    repo.log_transaction(
        user_id=user.id,
        type="topup",
        amount_cents=receipt.amount_cents,
        balance_after=updated.balance_cents,
        metadata={"tx_id": receipt.transaction_id, "provider": "stub"},
    )
    return updated
