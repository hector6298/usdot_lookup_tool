from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from datetime import datetime

class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds=900):
        super().__init__(app)
        self.timeout = timeout_seconds

    async def dispatch(self, request, call_next):
        # Skip timeout check for logout and static files
        if request.url.path.startswith("/logout") or request.url.path.startswith("/static"):
            return await call_next(request)

        session = request.session
        now = datetime.utcnow().timestamp()
        last_activity = session.get("last_activity")

        if last_activity:
            if now - last_activity > self.timeout:
                return RedirectResponse("/logout")
        session["last_activity"] = now
        response = await call_next(request)
        return response