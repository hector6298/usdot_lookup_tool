from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from datetime import datetime, timedelta
from app.crud.oauth import delete_salesforce_token

class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds=900):
        super().__init__(app)
        self.timeout = timeout_seconds

    async def dispatch(self, request, call_next):
        session = request.session
        now = datetime.utcnow().timestamp()
        last_activity = session.get("last_activity")

        if last_activity:
            if now - last_activity > self.timeout:
                if 'sf_connected' in session and session['sf_connected']:
                    delete_salesforce_token(request.state.db, 
                                            session.get("user_id"), 
                                            session.get("org_id"), 
                                            "salesforce")
                session.clear()
                return RedirectResponse("/login")
        session["last_activity"] = now
        response = await call_next(request)
        return response