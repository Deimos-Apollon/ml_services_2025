from typing import List, Any, Tuple, Dict
from core.entities.user import User
from core.repositories.user_repository import UserRepository
from core.services.model_provider import ModelProvider
import asyncio
import inspect


class InsufficientFundsError(ValueError):
    pass

async def predict_with_billing_async(
    repo: UserRepository,
    provider: ModelProvider,
    user: User,
    features: List[float],
    prices: Dict[str, int],
) -> Tuple[float, int, User]:
    plan = (user.plan or "basic").lower()
    if plan not in prices:
        raise ValueError("Unsupported plan")

    model = provider.get_model(plan)
    print(model)
    predict_async = getattr(model, "predict_one_async", None)
    if predict_async and inspect.iscoroutinefunction(predict_async):
        result = await predict_async(features)
    else:
        result = await asyncio.to_thread(model.predict_one, features)

    price = int(prices[plan])
    if price > 0:
        updated_user = repo.debit_if_sufficient(user.id, price)
        # логгируем транзакцию
        repo.log_transaction(
            user_id=user.id,
            type="predict",
            amount_cents=-price,
            balance_after=updated_user.balance_cents,
            metadata={"plan": plan, "features_len": len(features)},
        )
    else:
        updated_user = user

    return result, price, updated_user