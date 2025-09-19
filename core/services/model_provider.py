from abc import ABC, abstractmethod
from typing import List, Any


class Model(ABC):
    @abstractmethod
    def predict_one(self, features: List[float]) -> Any: ...

class ModelProvider(ABC):
    @abstractmethod
    def get_model(self, plan: str) -> Model: ...
