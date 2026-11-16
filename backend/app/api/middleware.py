import uuid

class CorrelationIdMiddleware:
    """
    Pure ASGI Middleware for S04 Correlation IDs.
    Avoids Starlette BaseHTTPMiddleware anyio streaming issues in test environments.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        corr_id = headers.get(b"x-correlation-id") or headers.get(b"x-request-id")
        correlation_id = corr_id.decode("latin1") if corr_id else str(uuid.uuid4())

        # Expose correlation_id in scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["correlation_id"] = correlation_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-correlation-id", correlation_id.encode("latin1")))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
