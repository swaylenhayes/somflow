"""Detection backends -- MLX and CoreML."""

from somflow.backends.base import BackendInfo, DetectionBackend
from somflow.backends.selector import BackendPreference, select_backend

__all__ = ["BackendInfo", "BackendPreference", "DetectionBackend", "select_backend"]
