"""Helper utilities for retries and safe operations."""

import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


def retry_async(max_attempts: int = 3, delay: float = 1.0) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry an async function with backoff."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay * (attempt + 1))

        return wrapper

    return decorator


def chunk_bytes(data: bytes, size: int = 3200) -> list[bytes]:
    """Split bytes into chunks; useful for streaming audio."""
    return [data[i : i + size] for i in range(0, len(data), size)]
