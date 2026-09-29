# tests for app/main.py — the request-id + timing middleware.
# uses the plain /health route so no llm/db mocking is needed.


def test_response_includes_request_id_header(client):
    response = client.get("/health")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 12  # uuid4().hex[:12]


def test_each_request_gets_a_different_request_id(client):
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]

    assert first != second
