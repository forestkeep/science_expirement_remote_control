import time
import logging
import functools

logger = logging.getLogger(__name__)


def time_decorator(level: int = logging.DEBUG):
    """Логирует время выполнения функции."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                logger.log(level, f"{func.__qualname__} выполнялся {elapsed:.4f} с")
        return wrapper
    return decorator