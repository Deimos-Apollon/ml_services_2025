import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr, Field

from config.settings import settings
from core.entities.user import User

from core.use_cases.user_use_cases import register_user, authenticate_user, top_up_balance
from core.use_cases.ml_use_cases import predict_with_billing_async, InsufficientFundsError
from infrastructure.db.sqlite import SQLiteUserRepository

from core.services.payment_provider import PaymentProvider
from core.services.model_provider import ModelProvider

from infrastructure.payments.stub_provider import StubPaymentProvider
from infrastructure.ml.sklearn_provider import build_sklearn_provider


router = APIRouter(prefix="", tags=["auth"])

basic_security = HTTPBasic()


# DTO для транзакций
class TransactionItem(BaseModel):
    id: int
    type: str
    amount_cents: int
    balance_after: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: str

def get_db():
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_user_repo(conn: sqlite3.Connection = Depends(get_db)) -> SQLiteUserRepository:
    return SQLiteUserRepository(conn)

# jwt авторизация
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]

# используем любой PaymentProvider, пока что - заглушка
def get_payment_provider() -> PaymentProvider:
    return StubPaymentProvider()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    balance_cents: int
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TopUpRequest(BaseModel):
    amount_cents: Optional[int] = None  # опционально, если не передан — берём дефолтное из settings

async def get_current_user(
    token: str = Depends(get_bearer_token),
    repo: SQLiteUserRepository = Depends(get_user_repo),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, repo: SQLiteUserRepository = Depends(get_user_repo)):
    try:
        user = register_user(repo, email=payload.email, password=payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        balance_cents=user.balance_cents,
        created_at=user.created_at,
    )

@router.post("/login", response_model=TokenResponse)
def login(
    credentials: HTTPBasicCredentials = Depends(basic_security),
    repo: SQLiteUserRepository = Depends(get_user_repo),
):
    user = authenticate_user(repo, email=credentials.username, password=credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_admin=current_user.is_admin,
        balance_cents=current_user.balance_cents,
        created_at=current_user.created_at,
    )


@router.post("/topup", response_model=UserResponse)
def topup(
    payload: Optional[TopUpRequest] = None,
    current_user: User = Depends(get_current_user),
    repo: SQLiteUserRepository = Depends(get_user_repo),
    provider: PaymentProvider = Depends(get_payment_provider),
):
    amount = payload.amount_cents if payload and payload.amount_cents else settings.TOPUP_DEFAULT_AMOUNT_CENTS
    try:
        updated = top_up_balance(repo, provider, current_user, amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(
        id=updated.id,
        email=updated.email,
        is_admin=updated.is_admin,
        balance_cents=updated.balance_cents,
        created_at=updated.created_at,
    )


# Провайдер моделей, пока что - локальный sklearn
def get_model_provider() -> ModelProvider:
    return build_sklearn_provider()

def get_price_table() -> Dict[str, int]:
    return {
        "basic": settings.PRICE_BASIC_INFER_CREDITS,
        "pro": settings.PRICE_PRO_INFER_CREDITS,
        "premium": settings.PRICE_PREMIUM_INFER_CREDITS,
    }

class PredictRequest(BaseModel):
    features: List[float] = Field(..., description="Вектор признаков")

class PredictResponse(BaseModel):
    result: Any
    charged_credits: int
    balance_credits: int
    plan: str

@router.post("/predict", response_model=PredictResponse)
async def predict(
    payload: PredictRequest,
    current_user: User = Depends(get_current_user),
    repo: SQLiteUserRepository = Depends(get_user_repo),
    provider: ModelProvider = Depends(get_model_provider),
    prices: Dict[str, int] = Depends(get_price_table),
):
    try:
        result, charged, updated_user = await predict_with_billing_async(
            repo=repo,
            provider=provider,
            user=current_user,
            features=payload.features,
            prices=prices,
        )
    except InsufficientFundsError:
        raise HTTPException(status_code=402, detail="Insufficient funds")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PredictResponse(
      result=result,
      charged_credits=charged,
      balance_credits=updated_user.balance_cents,
      plan=updated_user.plan,
    )

class PlanRequest(BaseModel):
    plan: str  # basic | pro | premium

class PlanResponse(BaseModel):
    id: int
    email: EmailStr
    plan: str
    balance_credits: int

@router.post("/plan", response_model=PlanResponse)
def change_plan(
    payload: PlanRequest,
    current_user: User = Depends(get_current_user),
    repo: SQLiteUserRepository = Depends(get_user_repo),
):
    plan = payload.plan.lower().strip()
    if plan not in {"basic", "pro", "premium"}:
        raise HTTPException(status_code=400, detail="Invalid plan")
    try:
        updated = repo.update_plan(current_user.id, plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlanResponse(
        id=updated.id, email=updated.email, plan=updated.plan, balance_credits=updated.balance_cents
    )

@router.get("/transactions", response_model=List[TransactionItem])
def get_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    repo: SQLiteUserRepository = Depends(get_user_repo),
):
    limit = max(1, min(100, int(limit)))  # пагинация, не хотим возвращать много
    offset = max(0, int(offset))
    txs = repo.list_transactions(current_user.id, limit=limit, offset=offset)
    return [
        TransactionItem(
            id=tx.id,
            type=tx.type,
            amount_cents=tx.amount_cents,
            balance_after=tx.balance_after,
            metadata=tx.metadata,
            created_at=tx.created_at,
        )
        for tx in txs
    ]
