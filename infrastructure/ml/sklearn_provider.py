from typing import List, Any, Dict
from threading import Lock
import os
from core.services.model_provider import Model, ModelProvider
from config.settings import settings


try:
    import joblib
except Exception:
    joblib = None


class SklearnModelWrapper(Model):
    """У моделей sklearn единый интерфейс"""
    def __init__(self, estimator):
        self.estimator = estimator
    def predict_one(self, features: List[float]) -> Any:
        return self.estimator.predict([features])[0]


class FallbackStubModel(Model):
    """Класс-заглушка, который всегда возвращает 1"""
    def predict_one(self, features: List[float]) -> Any:
        return 1 if sum(float(x) for x in features) >= 0 else 0


class SklearnModelProvider(ModelProvider):
    """Provider для моделей sklearn"""
    def __init__(self, paths: Dict[str, str]):
        self.paths = paths
        self._models: Dict[str, Model] = {}
        self._lock = Lock()

    def _load_model_from_path(self, path: str) -> Model:
        if joblib and path and os.path.exists(path):
            try:
                est = joblib.load(path)
                return SklearnModelWrapper(est)
            except Exception as e:
                print(f"Error in loading model: {e}")
        return FallbackStubModel()

    def get_model(self, plan: str) -> Model:
        key = plan.lower()
        if key in self._models:
            return self._models[key]
        with self._lock:
            if key in self._models:
                return self._models[key]
            path = self.paths.get(key)
            model = self._load_model_from_path(path)
            self._models[key] = model
            return model

def build_sklearn_provider() -> SklearnModelProvider:
    return SklearnModelProvider({
        "basic": settings.MODEL_BASIC_PATH,
        "pro": settings.MODEL_PRO_PATH,
        "premium": settings.MODEL_PREMIUM_PATH,
    })
