from abc import ABC, abstractmethod
import numpy as np

class BasePredictor(ABC):
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray):
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        pass

class LinearTrendPredictor(BasePredictor):
    """
    Linear regression trend predictor to forecast threshold breaches
    (e.g., estimating time until memory exhaustion).
    """
    def __init__(self):
        self.slope = 0.0
        self.intercept = 0.0
        self.fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray):
        if len(X) < 2:
            self.fitted = False
            return
        # X is represented as timestamps (seconds relative to baseline)
        A = np.vstack([X, np.ones(len(X))]).T
        self.slope, self.intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        self.fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.fitted:
            return np.zeros_like(X)
        return self.slope * X + self.intercept

    def estimate_seconds_to_threshold(self, start_timestamp: float, threshold: float) -> float:
        """
        Calculates time remaining (in seconds) until the metric crosses threshold.
        Returns -1.0 if the trend is flat/negative or not fitted.
        """
        if not self.fitted or self.slope <= 1e-5:
            return -1.0
        target_time = (threshold - self.intercept) / self.slope
        seconds_remaining = target_time - start_timestamp
        return max(0.0, seconds_remaining)
