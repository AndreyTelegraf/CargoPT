import asyncio
from collections import defaultdict
from collections import deque
from time import monotonic

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send


class WebRequestRateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_requests: int,
        window_seconds: int,
        max_body_bytes: int,
        location_search_max_requests: int = 120,
        location_search_window_seconds: int = 3600,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_body_bytes = max_body_bytes
        self.location_search_max_requests = location_search_max_requests
        self.location_search_window_seconds = location_search_window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._location_search_requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_key(scope: Scope) -> str:
        client = scope.get("client")
        return str(client[0]) if client else "unknown"

    async def _is_allowed(
        self,
        key: str,
        now: float,
        *,
        history_by_key: dict[str, deque[float]],
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        cutoff = now - window_seconds
        async with self._lock:
            history = history_by_key[key]
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= max_requests:
                return False
            history.append(now)
            return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == "/api/v1/locations/search"
        ):
            allowed = await self._is_allowed(
                self._client_key(scope),
                monotonic(),
                history_by_key=self._location_search_requests,
                max_requests=self.location_search_max_requests,
                window_seconds=self.location_search_window_seconds,
            )
            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "too many location searches"},
                    headers={
                        "Retry-After": str(self.location_search_window_seconds)
                    },
                )
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/v1/requests"
        ):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_content_length = headers.get(b"content-length", b"0")
        try:
            content_length = int(raw_content_length)
        except ValueError:
            content_length = self.max_body_bytes + 1

        if content_length > self.max_body_bytes:
            response = JSONResponse(
                status_code=413,
                content={"detail": "request body too large"},
            )
            await response(scope, receive, send)
            return

        received_messages = []
        received_bytes = 0
        more_body = True
        while more_body:
            message = await receive()
            received_messages.append(message)
            if message.get("type") == "http.disconnect":
                break
            chunk = message.get("body", b"")
            received_bytes += len(chunk)
            if received_bytes > self.max_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "request body too large"},
                )
                await response(scope, receive, send)
                return
            more_body = bool(message.get("more_body", False))

        async def replay_receive():
            if received_messages:
                return received_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        allowed = await self._is_allowed(
            self._client_key(scope),
            monotonic(),
            history_by_key=self._requests,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
        )
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "too many requests"},
                headers={"Retry-After": str(self.window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, replay_receive, send)
