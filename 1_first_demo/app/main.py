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


# ---------- Plans ----------

@app.post("/api/plans", status_code=201)
def create_plan(body: PlanCreate, state: str):
    """Create a plan under a Microsoft 365 group (owner = groupId)."""
    token = get_token_from_state(state)
    payload = {"owner": body.groupId, "title": body.title}
    return graph_post("/planner/plans", token, payload)

@app.get("/api/plans/{plan_id}/buckets")
def list_buckets(plan_id: str, state: str):
    token = get_token_from_state(state)
    return graph_get(f"/planner/plans/{plan_id}/buckets", token)

# ---------- Buckets ----------

@app.post("/api/plans/{plan_id}/buckets", status_code=201)
def create_bucket(plan_id: str, body: BucketCreate, state: str):
    token = get_token_from_state(state)
    payload = {
        "name": body.name,
        "planId": plan_id,
        # Extremely simple default order hint; good enough for dev
        "orderHint": body.orderHint or " !"
    }
    return graph_post("/planner/buckets", token, payload)

@app.delete("/api/buckets/{bucket_id}")
def delete_bucket(bucket_id: str, etag: str, state: str):
    """Delete a bucket (requires ETag)."""
    token = get_token_from_state(state)
    graph_delete(f"/planner/buckets/{bucket_id}", token, etag)
    return {"deleted": True}

# ---------- Tasks ----------

@app.get("/api/plans/{plan_id}/tasks")
def list_tasks(plan_id: str, state: str):
    token = get_token_from_state(state)
    return graph_get(f"/planner/plans/{plan_id}/tasks", token)

@app.post("/api/plans/{plan_id}/tasks", status_code=201)
def create_task(plan_id: str, body: TaskCreate, state: str):
    token = get_token_from_state(state)
    payload = {"planId": plan_id, "bucketId": body.bucketId, "title": body.title}
    return graph_post("/planner/tasks", token, payload)

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, state: str):
    token = get_token_from_state(state)
    return graph_get(f"/planner/tasks/{task_id}", token)

@app.get("/api/tasks/{task_id}/etag")
def get_task_etag(task_id: str, state: str):
    """Helper to fetch the current ETag for update/delete."""
    token = get_token_from_state(state)
    r = graph_get_raw(f"/planner/tasks/{task_id}", token)
    etag = r.json().get("@odata.etag")
    return {"etag": etag}

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, etag: str, state: str):
    token = get_token_from_state(state)
    # MS Graph requires If-Match with latest ETag
    graph_patch(f"/planner/tasks/{task_id}", token, body.model_dump(exclude_none=True), etag)
    return {"updated": True}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, etag: str, state: str):
    token = get_token_from_state(state)
    graph_delete(f"/planner/tasks/{task_id}", token, etag)
    return {"deleted": True}

# ---------- Utility to find groups you own/are in ----------
@app.get("/api/me/groups")
def my_groups(state: str):
    token = get_token_from_state(state)
    return graph_get("/me/joinedGroups?$select=id,displayName,groupTypes", token)

# @app.get("/api/me/groups")
# def my_groups(state: str):
#     token = get_token_from_state(state)
#     try:
#         # pass $select as params so it’s encoded correctly
#         return graph_get("/me/joinedGroups", token, params={"$select": "id,displayName,groupTypes"})
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/graph")
def graph_proxy(request: Request, path: str, state: str):
    token = get_token_from_state(state)
    params = dict(request.query_params)
    params.pop("path", None)
    params.pop("state", None)
    try:
        return graph_get(path, token, params=params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/me/groups")
def my_groups(state: str, unified_only: bool = True):
    token = get_token_from_state(state)
    params = {"$select": "id,displayName,groupTypes"}
    if unified_only:
        # Only Microsoft 365 groups (Unified)
        params["$filter"] = "groupTypes/any(c:c eq 'Unified')"
    try:
        return graph_get("/me/memberOf/microsoft.graph.group", token, params=params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))