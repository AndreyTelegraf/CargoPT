import asyncio

from app.api.rate_limit import WebRequestRateLimitMiddleware


async def call_app(
    middleware,
    *,
    path,
    body=b"{}",
    client="203.0.113.1",
    method="POST",
):
    messages = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    await middleware(
        {
            "type": "http",
            "method": method,
            "path": path,
            "client": (client, 12345),
            "headers": [],
        },
        receive,
        send,
    )
    return sent


async def app(scope, receive, send):
    message = await receive()
    await send({"type": "http.response.start", "status": 201, "headers": []})
    await send({"type": "http.response.body", "body": message.get("body", b"")})


async def main():
    middleware = WebRequestRateLimitMiddleware(
        app,
        max_requests=2,
        window_seconds=3600,
        max_body_bytes=8,
        location_search_max_requests=2,
        location_search_window_seconds=3600,
    )
    first = await call_app(middleware, path="/api/v1/requests")
    second = await call_app(middleware, path="/api/v1/requests")
    limited = await call_app(middleware, path="/api/v1/requests")
    assert first[0]["status"] == 201
    assert second[0]["status"] == 201
    assert limited[0]["status"] == 429

    oversized = await call_app(
        middleware,
        path="/api/v1/requests",
        body=b"123456789",
        client="203.0.113.2",
    )
    assert oversized[0]["status"] == 413

    unrelated = await call_app(
        middleware,
        path="/api/v1/track/token/completion/confirm",
        client="203.0.113.1",
    )
    assert unrelated[0]["status"] == 201

    first_search = await call_app(
        middleware,
        path="/api/v1/locations/search",
        client="203.0.113.3",
        method="GET",
    )
    second_search = await call_app(
        middleware,
        path="/api/v1/locations/search",
        client="203.0.113.3",
        method="GET",
    )
    limited_search = await call_app(
        middleware,
        path="/api/v1/locations/search",
        client="203.0.113.3",
        method="GET",
    )
    assert first_search[0]["status"] == 201
    assert second_search[0]["status"] == 201
    assert limited_search[0]["status"] == 429
    print("RATE_LIMIT_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
