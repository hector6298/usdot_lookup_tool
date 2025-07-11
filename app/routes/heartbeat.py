from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/session/heartbeat")
def session_heartbeat(request: Request):
    """Check if the session is still active."""
    if 'id_token' not in request.session:
        return JSONResponse(status_code=401, content={"status": "Session expiredor not logged in"})
    return JSONResponse(status_code=200, content={"status": "ok"})