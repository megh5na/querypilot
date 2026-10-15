# in-memory sliding-window rate limiter - per client IP

import logging
import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,  # injectable so tests don't need real sleeps
    ):
        if max_requests < 1 or window_seconds <= 0:  # fail at startup, not on the first request
            raise ValueError("max_requests must be >= 1 and window_seconds > 0")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}  # client key -> timestamps of allowed requests
        self._last_sweep = clock()

    def check(self, key: str) -> float | None:
        # records a hit and returns None if allowed, otherwise the seconds until a slot frees up.
        # rejected requests are NOT recorded, so hammering while blocked doesn't extend the block.
        now = self._clock()
        self._sweep(now)

        hits = self._hits.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:  # drop hits that have slid out of the window
            hits.popleft()

        if len(hits) >= self.max_requests:
            return hits[0] + self.window_seconds - now  # oldest hit expiring frees the first slot
        hits.append(now)
        return None

    def _sweep(self, now: float) -> None:
        # once per window, forget clients whose newest hit is outside it, so the dict
        # can't grow forever with one entry per ip that ever called us
        if now - self._last_sweep < self.window_seconds:
            return
        cutoff = now - self.window_seconds
        self._hits = {k: h for k, h in self._hits.items() if h and h[-1] > cutoff}
        self._last_sweep = now

    def reset(self) -> None:
        self._hits.clear()


ask_limiter = SlidingWindowLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)


# async on purpose: an `async def` dependency runs on the event loop, and check() has no
# await inside it, so check-then-append is atomic. a plain `def` dependency would run in a
# threadpool and this shared dict would need a lock.
async def rate_limit_ask(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    retry_after = ask_limiter.check(client)
    if retry_after is not None:
        seconds = max(1, math.ceil(retry_after))  # Retry-After is whole seconds
        logger.warning("rate limit exceeded", extra={"client": client, "retry_after": seconds})
        raise HTTPException(
            status_code=429,
            detail={"error": "Too many requests"},
            headers={"Retry-After": str(seconds)},
        )
