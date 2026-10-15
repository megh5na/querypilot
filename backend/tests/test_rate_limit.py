# tests for app/core/rate_limit.py. the limiter takes an injectable clock, so the unit
# tests advance time by hand instead of sleeping — fast and deterministic.

import pytest

from app.core import rate_limit
from app.core.rate_limit import SlidingWindowLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


def test_allows_up_to_max_requests(clock):
    limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60, clock=clock)
    assert [limiter.check("a") for _ in range(3)] == [None, None, None]


def test_rejects_request_over_the_limit_with_retry_after(clock):
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60, clock=clock)
    limiter.check("a")
    clock.advance(10)
    limiter.check("a")
    clock.advance(5)

    # oldest hit was 15s ago, so a slot frees up in 45s
    assert limiter.check("a") == pytest.approx(45)


def test_clients_are_limited_independently(clock):
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60, clock=clock)
    assert limiter.check("a") is None
    assert limiter.check("a") is not None
    assert limiter.check("b") is None  # b is unaffected by a


def test_window_slides_and_frees_slots(clock):
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.check("a")
    assert limiter.check("a") is not None

    clock.advance(61)
    assert limiter.check("a") is None


def test_rejected_requests_do_not_extend_the_block(clock):
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.check("a")
    for _ in range(5):  # hammering while blocked
        clock.advance(1)
        assert limiter.check("a") is not None

    clock.advance(56)  # 61s after the one allowed hit
    assert limiter.check("a") is None


def test_sweep_forgets_idle_clients(clock):
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.check("idle")

    clock.advance(120)
    limiter.check("active")  # triggers the periodic sweep

    assert "idle" not in limiter._hits
    assert "active" in limiter._hits


# --- wired into /ask ---------------------------------------------------

def test_ask_returns_429_with_retry_after_when_limit_exceeded(
    client, mock_generate_sql, mock_run_query, monkeypatch
):
    monkeypatch.setattr(rate_limit, "ask_limiter", SlidingWindowLimiter(2, 60))
    mock_generate_sql.return_value = "SELECT 1"
    mock_run_query.return_value = [{"?column?": 1}]

    assert client.post("/ask", json={"question": "q"}).status_code == 200
    assert client.post("/ask", json={"question": "q"}).status_code == 200
    blocked = client.post("/ask", json={"question": "q"})

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json()["detail"] == {"error": "Too many requests"}


def test_blocked_request_never_reaches_llm_or_db(
    client, mock_generate_sql, mock_run_query, monkeypatch
):
    limiter = SlidingWindowLimiter(1, 60)
    limiter.check("testclient")  # testclient's ip is "testclient" — use up its one slot
    monkeypatch.setattr(rate_limit, "ask_limiter", limiter)

    response = client.post("/ask", json={"question": "q"})

    assert response.status_code == 429
    mock_generate_sql.assert_not_called()
    mock_run_query.assert_not_called()


def test_health_is_not_rate_limited(client, monkeypatch):
    limiter = SlidingWindowLimiter(1, 60)
    limiter.check("testclient")
    monkeypatch.setattr(rate_limit, "ask_limiter", limiter)

    assert all(client.get("/health").status_code == 200 for _ in range(5))


@pytest.mark.parametrize("max_requests, window", [(0, 60), (-1, 60), (5, 0)])
def test_rejects_nonsensical_limits(max_requests, window):
    with pytest.raises(ValueError):
        SlidingWindowLimiter(max_requests, window)
