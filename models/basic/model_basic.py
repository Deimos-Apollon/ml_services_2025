import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin


class TruncatedNormalModel(BaseEstimator, RegressorMixin):
    def __init__(self, mean=0.5, std=0.1, random_state=None):
        self.mean = mean
        self.std = std
        self.random_state = random_state

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        n_samples = X.shape[0] if hasattr(X, 'shape') else len(X)
        rng = np.random.RandomState(self.random_state)
        numbers = rng.normal(self.mean, self.std, n_samples)
        return np.clip(numbers, 0, 1)
