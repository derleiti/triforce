"""Test helpers for async mocking and test utilities."""

import asyncio
from typing import Any, Iterable, Optional


class AsyncIter:
    """Helper class to create async iterators from regular iterables.

    Fixes async generator mock issues in tests.

    Example:
        async def fake_stream(*args, **kwargs):
            return AsyncIter([b"chunk1", b"chunk2", b""])

        # monkeypatch your streaming call to return fake_stream
    """

    def __init__(self, items: Iterable[Any]):
        self._items = items

    def __aiter__(self):
        self._it = iter(self._items)
        return self

    async def __anext__(self):
        await asyncio.sleep(0)  # Yield control to event loop
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class AsyncContextManager:
    """Helper class to create async context managers for mocking.

    Example:
        async with AsyncContextManager(mock_client) as client:
            response = await client.get("/endpoint")
    """

    def __init__(self, obj: Any):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self._obj, 'aclose'):
            await self._obj.aclose()
        return False
