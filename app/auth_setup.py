import os
from authlib.integrations.starlette_client import OAuth


"""Storing the configuration into the `auth0_config` variable for later usage"""


oauth = OAuth()
oauth.register(
    "auth0",
    client_id=os.environ.get('AUTH0_CLIENT_ID'),
    client_secret=os.environ.get('AUTH0_CLIENT_SECRET'),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{os.environ.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)