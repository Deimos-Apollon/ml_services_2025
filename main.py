from fastapi import FastAPI
from config.settings import settings
from infrastructure.db.sqlite import init_db
from infrastructure.web.controllers.user_controller import router as user_router
from fastapi.middleware.cors import CORSMiddleware
from models.basic.model_basic import TruncatedNormalModel
import sys

sys.modules['__main__'].TruncatedNormalModel = TruncatedNormalModel

app = FastAPI(title="Survivorship prediction")

# от CORS
origins = [
    "http://localhost:8000",
    "http://localhost:63342"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
def on_startup():
    init_db(settings.DB_PATH)

app.include_router(user_router)
