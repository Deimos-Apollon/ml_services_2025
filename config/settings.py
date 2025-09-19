import os
from dataclasses import dataclass


@dataclass
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    DB_PATH: str = os.getenv("DB_PATH", "./app.db")

    MODEL_BASIC_PATH: str = os.getenv("MODEL_BASIC_PATH", "./models/basic/model_basic.pkl")
    MODEL_PRO_PATH: str = os.getenv("MODEL_PRO_PATH", "./models/pro/model_pro.pkl")
    MODEL_PREMIUM_PATH: str = os.getenv("MODEL_PREMIUM_PATH", "./models/premium/model_premium.pkl")

    PRICE_BASIC_INFER_CREDITS: int = int(os.getenv("PRICE_BASIC_INFER_CREDITS", "1"))
    PRICE_PRO_INFER_CREDITS: int = int(os.getenv("PRICE_PRO_INFER_CREDITS", "5"))
    PRICE_PREMIUM_INFER_CREDITS: int = int(os.getenv("PRICE_PREMIUM_INFER_CREDITS", "20"))

    TOPUP_DEFAULT_AMOUNT_CENTS: int = int(os.getenv("TOPUP_DEFAULT_AMOUNT_CENTS", "100"))

settings = Settings()
print(settings)