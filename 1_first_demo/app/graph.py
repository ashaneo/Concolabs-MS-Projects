# import requests

# GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# def graph_get(path: str, access_token: str, params: dict | None = None):
#     r = requests.get(f"{GRAPH_BASE}{path}", headers={"Authorization": f"Bearer {access_token}"}, params=params or {})
#     if r.status_code >= 400:
#         raise Exception(f"Graph GET {path} failed: {r.status_code} {r.text}")
#     return r.json()

# def graph_post(path: str, access_token: str, payload: dict):
#     r = requests.post(f"{GRAPH_BASE}{path}", headers={
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }, json=payload)
#     if r.status_code >= 400:
#         raise Exception(f"Graph POST {path} failed: {r.status_code} {r.text}")
#     return r.json()

# app/graph.py
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def _req(method: str, path: str, access_token: str,
         json: dict | None = None, params: dict | None = None,
         extra_headers: dict | None = None):
    headers = {"Authorization": f"Bearer {access_token}"}
    if json is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    r = requests.request(method, f"{GRAPH_BASE}{path}", headers=headers, json=json, params=params)
    if r.status_code >= 400:
        # bubble Graph error verbatim for easy debugging
        raise Exception(f"{method} {path} -> {r.status_code} {r.text}")
    return r

def graph_get(path: str, access_token: str, params: dict | None = None):
    return _req("GET", path, access_token, params=params).json()

def graph_get_raw(path: str, access_token: str):
    return _req("GET", path, access_token)  # caller reads headers/json

def graph_post(path: str, access_token: str, payload: dict):
    return _req("POST", path, access_token, json=payload).json()

def graph_patch(path: str, access_token: str, payload: dict, etag: str):
    return _req("PATCH", path, access_token, json=payload, extra_headers={"If-Match": etag})

def graph_delete(path: str, access_token: str, etag: str):
    return _req("DELETE", path, access_token, extra_headers={"If-Match": etag})
