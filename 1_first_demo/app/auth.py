import time
import requests
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Depends, Request
from app.config import JWKS_URI, ISSUER, BACKEND_APP_ID_URI, BACKEND_CLIENT_ID, BACKEND_CLIENT_SECRET, TENANT_ID, GRAPH_SCOPES
from msal import ConfidentialClientApplication

# --- Verify incoming bearer token from SPA (audience = BACKEND_APP_ID_URI) ---
_jwks_client = PyJWKClient(JWKS_URI)

def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ", 1)[1].strip()

def verify_spa_jwt(request: Request) -> dict:
    token = _get_bearer_token(request)
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=BACKEND_APP_ID_URI,   # MUST match your API App ID URI (api://<backend-client-id>)
            issuer=ISSUER,
            options={"verify_aud": True, "verify_iss": True},
        )
        # Basic expiration check
        if decoded.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token expired")
        return {"raw": token, "claims": decoded}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# --- OBO: exchange SPA token -> Graph token with requested scopes ---
def obo_graph_token(user_assertion: str) -> str:
    cca = ConfidentialClientApplication(
        client_id=BACKEND_CLIENT_ID,
        client_credential=BACKEND_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    )
    result = cca.acquire_token_on_behalf_of(user_assertion=user_assertion, scopes=GRAPH_SCOPES)
    if "access_token" not in result:
        # Helpful error bubble-up
        error = result.get("error_description") or result
        raise HTTPException(status_code=500, detail=f"OBO failed: {error}")
    return result["access_token"]

def get_graph_token(dep=Depends(verify_spa_jwt)) -> str:
    spa_token = dep["raw"]
    return obo_graph_token(spa_token)
