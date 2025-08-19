from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import AUTHORITY, AUTH_URL, TOKEN_URL, BACKEND_CLIENT_ID, BACKEND_CLIENT_SECRET, REDIRECT_URI, GRAPH_SCOPES, ALLOWED_ORIGINS, LOGIN_SCOPES,RESOURCE_SCOPES
# from app.config import AUTH_URL, REDIRECT_URI, LOGIN_SCOPES, RESOURCE_SCOPES
import msal, requests, secrets, urllib.parse
# app/main.py (replace the callback handler)
from app.models import TaskCreate, TaskUpdate, PlanCreate, BucketCreate
from app.graph import graph_get, graph_get_raw, graph_post, graph_patch, graph_delete
from fastapi import HTTPException, Request


app = FastAPI(title="Planner Server-Side")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# super simple in-memory "session" for demo purposes
SESSION = {}  # key: state -> {"account": <oid>, "token": <access_token>, "refresh": <refresh_token>}

def msal_confidential_client():
    return msal.ConfidentialClientApplication(
        client_id=BACKEND_CLIENT_ID,
        client_credential=BACKEND_CLIENT_SECRET,
        authority=AUTHORITY
    )

@app.get("/")
def root():
    return {"ok": True}

# @app.get("/login")
# def login():
#     state = secrets.token_urlsafe(24)
#     params = {
#         "client_id": BACKEND_CLIENT_ID,
#         "response_type": "code",
#         "redirect_uri": REDIRECT_URI,
#         "response_mode": "query",
#         "scope": " ".join(GRAPH_SCOPES),
#         "state": state,
#     }
#     url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
#     return RedirectResponse(url)

# @app.get("/auth/callback")
# def auth_callback(code: str | None = None, state: str | None = None, error: str | None = None, error_description: str | None = None):
#     if error:
#         raise HTTPException(400, f"Auth error: {error} - {error_description}")

#     if not code:
#         raise HTTPException(400, "Missing authorization code")

#     cca = msal_confidential_client()
#     result = cca.acquire_token_by_authorization_code(
#         code=code,
#         scopes=GRAPH_SCOPES,
#         redirect_uri=REDIRECT_URI
#     )
#     if "access_token" not in result:
#         raise HTTPException(400, f"Token exchange failed: {result}")

#     # store a minimal session
#     oid = result.get("id_token_claims",{}).get("oid","")
#     SESSION[state or "default"] = {
#         "account": oid,
#         "token": result["access_token"],
#         "refresh": result.get("refresh_token")
#     }
#     return JSONResponse({"signed_in": True, "state": state, "oid": oid})

def get_token_from_state(state: str | None):
    if not state or state not in SESSION:
        raise HTTPException(401, "Not signed in. Hit /login first (browser) and capture 'state' from callback JSON.")
    return SESSION[state]["token"]

@app.get("/api/plans")
def get_plans(state: str):
    token = get_token_from_state(state)
    r = requests.get(
        "https://graph.microsoft.com/v1.0/me/planner/plans",
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.post("/logout")
def logout(state: str | None = None):
    if state and state in SESSION:
        del SESSION[state]
    return {"signed_out": True}

@app.get("/login")
def login():
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": BACKEND_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": LOGIN_SCOPES,          # <-- includes openid/profile/offline_access + Graph scopes
        "state": state,
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/callback")
def auth_callback(code: str | None = None, state: str | None = None,
                  error: str | None = None, error_description: str | None = None):
    if error:
        return JSONResponse({"auth_error": error, "description": error_description}, status_code=400)
    if not code:
        return JSONResponse({"error": "missing_code"}, status_code=400)

    cca = msal_confidential_client()
    # IMPORTANT: pass ONLY resource scopes here
    result = cca.acquire_token_by_authorization_code(
        code=code,
        scopes=RESOURCE_SCOPES,
        redirect_uri=REDIRECT_URI
    )
    if "access_token" not in result:
        return JSONResponse({"token_error": result}, status_code=400)

    oid = result.get("id_token_claims", {}).get("oid", "")
    SESSION[state or "default"] = {
        "account": oid,
        "token": result["access_token"],
        "refresh": result.get("refresh_token")
    }
    return JSONResponse({"signed_in": True, "state": state, "oid": oid})

# app/main.py
@app.get("/debug/states")
def debug_states():
    return {"states": list(SESSION.keys())}


