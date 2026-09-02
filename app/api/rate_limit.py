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
        acquisition_event_max_requests: int = 240,
        acquisition_event_window_seconds: int = 3600,
        location_search_max_requests: int = 120,
        location_search_window_seconds: int = 3600,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_body_bytes = max_body_bytes
        self.acquisition_event_max_requests = acquisition_event_max_requests
        self.acquisition_event_window_seconds = acquisition_event_window_seconds
        self.location_search_max_requests = location_search_max_requests
        self.location_search_window_seconds = location_search_window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._acquisition_event_requests: dict[str, deque[float]] = defaultdict(deque)
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

        is_web_request = (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/v1/requests"
        )
        is_acquisition_event = (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/v1/acquisition-events"
        )
        if not is_web_request and not is_acquisition_event:
            await self.app(scope, receive, send)
            return

        body_limit = self.max_body_bytes if is_web_request else min(
            self.max_body_bytes,
            8192,
        )

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_content_length = headers.get(b"content-length", b"0")
        try:
            content_length = int(raw_content_length)
        except ValueError:
            content_length = body_limit + 1

        if content_length > body_limit:
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
            if received_bytes > body_limit:
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

        history_by_key = (
            self._requests
            if is_web_request
            else self._acquisition_event_requests
        )
        max_requests = (
            self.max_requests
            if is_web_request
            else self.acquisition_event_max_requests
        )
        window_seconds = (
            self.window_seconds
            if is_web_request
            else self.acquisition_event_window_seconds
        )
        allowed = await self._is_allowed(
            self._client_key(scope),
            monotonic(),
            history_by_key=history_by_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "too many requests"
                        if is_web_request
                        else "too many acquisition events"
                    )
                },
                headers={"Retry-After": str(window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, replay_receive, send)
