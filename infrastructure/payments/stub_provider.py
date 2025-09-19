from uuid import uuid4
from core.entities.user import User
from core.services.payment_provider import PaymentProvider, PaymentReceipt


class StubPaymentProvider(PaymentProvider):
    """Класс-заглушка для простоты пополнения баланса - всегда успех на данную сумму"""
    def charge(self, user: User, amount_cents: int) -> PaymentReceipt:
        return PaymentReceipt(
            success=True,
            amount_cents=int(amount_cents),
            transaction_id=f"stub-{uuid4()}",
            message="Stub payment approved",
        )
