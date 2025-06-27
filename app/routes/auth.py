import os
from urllib.parse import quote_plus, urlencode
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import Session
from app.auth_setup import oauth
from app.crud.user_org_membership import save_user_org_membership
from app.database import get_db

router = APIRouter()


@router.get("/login")
async def login(request: Request):
    """
    Redirects the user to the Auth0 Universal Login (https://auth0.com/docs/authenticate/login/auth0-universal-login)
    """
    if 'id_token' not in request.session:  # it could be userinfo instead of id_token
        return await oauth.auth0.authorize_redirect(
            request,
            redirect_uri=request.url_for("callback")
        )
    return RedirectResponse(url=request.url_for("dashboard", dashboard_type="carriers"))


@router.get("/signup")
async def signup(request: Request):
    """
    Redirects the user to the Auth0 Universal Login (https://auth0.com/docs/authenticate/login/auth0-universal-login)
    """
    if 'id_token' not in request.session:  # it could be userinfo instead of id_token
        return await oauth.auth0.authorize_redirect(
            request,
            redirect_uri=request.url_for("callback"),
            screen_hint="signup"
        )
    return RedirectResponse(url=request.url_for("dashboard", dashboard_type="carriers"))


@router.get("/logout")
def logout(request: Request):
    """
    Redirects the user to the Auth0 Universal Login (https://auth0.com/docs/authenticate/login/auth0-universal-login)
    """
    response = RedirectResponse(
        url="https://" + os.environ.get('AUTH0_DOMAIN')
            + "/v2/logout?"
            + urlencode(
                {
                    "returnTo": request.url_for("home"),
                    "client_id": os.environ.get('AUTH0_CLIENT_ID'),
                },
                quote_via=quote_plus,
            )
    )
    request.session.clear()
    return response


@router.get("/callback")
async def callback(request: Request,
                   db: Session = Depends(get_db)):
    """
    Callback redirect from Auth0
    """
    token = await oauth.auth0.authorize_access_token(request)
    # Store `id_token`, and `userinfo` in session
    request.session['id_token'] = token['id_token']
    request.session['userinfo'] = token['userinfo']

    # Create user in DB if not exists
    save_user_org_membership(db, token)

    return RedirectResponse(url=request.url_for("dashboard", dashboard_type="carriers"))


def verify_login(request: Request):
    """
    This Dependency protects an endpoint and it can only be accessed if the user has an active session
    """
    if 'id_token' not in request.session:  # it could be userinfo instead of id_token
        # this will redirect people to the login after if they are not logged in
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authorized",
            headers={
                "Location": "/login"
            }
        )
    
def verify_login_json_response(request: Request):
    """
    This Dependency protects an endpoint and it can only be accessed if the user has an active session
    """
    if 'id_token' not in request.session:  # it could be userinfo instead of id_token
        # this will redirect people to the login after if they are not logged in
        return JSONResponse(status_code=403, content={"detail": "Forbidden: User not authenticated"})
