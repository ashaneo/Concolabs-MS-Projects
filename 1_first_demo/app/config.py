# import os
# from dotenv import load_dotenv

# load_dotenv()

# TENANT_ID = os.getenv("TENANT_ID", "")
# TENANT_DOMAIN = os.getenv("TENANT_DOMAIN", "")
# BACKEND_CLIENT_ID = os.getenv("BACKEND_CLIENT_ID", "")
# BACKEND_OBJECT_ID = os.getenv("BACKEND_OBJECT_ID", "")
# BACKEND_CLIENT_SECRET = os.getenv("BACKEND_CLIENT_SECRET", "")
# BACKEND_APP_ID_URI = os.getenv("BACKEND_APP_ID_URI", "")  # audience expected in incoming JWT

# GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "Tasks.ReadWrite Group.Read.All").split()

# # OpenID config / JWKS
# ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
# JWKS_URI = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

# ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

import os
from dotenv import load_dotenv
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
BACKEND_CLIENT_ID = os.getenv("BACKEND_CLIENT_ID")
BACKEND_CLIENT_SECRET = os.getenv("BACKEND_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GRAPH_SCOPES = os.getenv("GRAPH_SCOPES","openid profile offline_access Tasks.ReadWrite Group.Read.All").split()

LOGIN_SCOPES = "openid profile offline_access Tasks.ReadWrite Group.Read.All"
RESOURCE_SCOPES = ["Tasks.ReadWrite", "Group.Read.All"]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTH_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS","").split(",") if o.strip()]
