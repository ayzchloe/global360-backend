"""
Validation for the LinkedIn OAuth scope fix (openid profile email).

Run: python test_linkedin_scope_fix.py
"""
import os

# Must be set BEFORE importing app modules (load_dotenv does not override
# existing env vars), so the endpoint uses this redirect URI in the test.
os.environ.setdefault(
    "LINKEDIN_REDIRECT_URI", "https://global360-zeta.vercel.app/auth/linkedin/callback"
)

from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from main import app
import auth


def check(label, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label} {extra}")
    return cond


failures = []

# 1. Scope constant uses the modern OIDC scopes only
failures.append(check(
    "LINKEDIN_SCOPE is 'openid profile email'",
    auth.LINKEDIN_SCOPE == "openid profile email",
    f"-> {auth.LINKEDIN_SCOPE!r}",
))
failures.append(check(
    "No deprecated scopes present",
    not any(
        s in auth.LINKEDIN_SCOPE
        for s in ("r_liteprofile", "r_emailaddress", "r_basicprofile")
    ),
))

# 2. OAUTH_PROVIDERS carries the new config
li_cfg = auth.OAUTH_PROVIDERS["linkedin"]
failures.append(check(
    "OAUTH_PROVIDERS['linkedin'] updated",
    li_cfg["scope"] == "openid profile email"
    and li_cfg["authorization_url"] == "https://www.linkedin.com/oauth/v2/authorization",
))

# 3. Generated authorization URL structure
state = "test-state-123"
result = auth.get_linkedin_authorization_url(state=state)
url = result["authorization_url"]
parts = urlsplit(url)
qs = parse_qs(parts.query)
failures.append(check(
    "Authorization URL uses LinkedIn v2 endpoint",
    f"{parts.scheme}://{parts.netloc}{parts.path}"
    == "https://www.linkedin.com/oauth/v2/authorization",
    f"-> {parts.scheme}://{parts.netloc}{parts.path}",
))
failures.append(check(
    "URL query parameters correct",
    qs.get("response_type") == ["code"]
    and qs.get("scope") == ["openid profile email"]
    and qs.get("state") == [state]
    and qs.get("client_id") == [auth.LINKEDIN_CLIENT_ID]
    and qs.get("redirect_uri") == [os.environ["LINKEDIN_REDIRECT_URI"]],
    f"-> scope={qs.get('scope')}",
))
failures.append(check(
    "State is auto-generated when omitted",
    len(auth.get_linkedin_authorization_url()["state"]) >= 20,
))

# 4. Endpoints serve the URL (JSON with "url" key + aliases)
client = TestClient(app)
for path in (
    "/auth/linkedin/authorize",
    "/auth/linkedin/login",
    "/auth/linkedin/url",
    "/auth/oauth/linkedin/authorize",
    "/auth/oauth/linkedin/url",
):
    res = client.get(path)
    body = res.json()
    failures.append(check(
        f"GET {path} works",
        res.status_code == 200
        and "url" in body
        and "authorization_url" in body
        and "state" in body
        and body["url"] == body["authorization_url"],
        f"-> {res.status_code} keys={sorted(body)}",
    ))
    failures.append(check(
        f"GET {path} URL has correct scope/params",
        parse_qs(urlsplit(body["url"]).query).get("scope") == ["openid profile email"]
        and parse_qs(urlsplit(body["url"]).query).get("response_type") == ["code"]
        and parse_qs(urlsplit(body["url"]).query).get("state") == [body["state"]]
        and urlsplit(body["url"])._replace(query="").geturl()
        == "https://www.linkedin.com/oauth/v2/authorization",
    ))

# 5. Redirect mode: ?redirect=true -> 302 straight to LinkedIn
res_red = client.get("/auth/linkedin/authorize", follow_redirects=False)
res_red2 = client.get(
    "/auth/linkedin/authorize?redirect=true", follow_redirects=False
)
failures.append(check(
    "?redirect=true returns 302 to LinkedIn",
    res_red2.status_code == 302
    and res_red2.headers["location"].startswith("https://www.linkedin.com/oauth/v2/authorization"),
    f"-> {res_red2.status_code} location={res_red2.headers.get('location', '')[:60]}...",
))
failures.append(check(
    "Default (no redirect param) returns JSON, not 302",
    res_red.status_code == 200 and "url" in res_red.json(),
    f"-> {res_red.status_code}",
))

# 5. Missing redirect URI -> clear error, not a crash
import importlib
saved = auth.LINKEDIN_REDIRECT_URI
auth.LINKEDIN_REDIRECT_URI = None
try:
    auth.get_linkedin_authorization_url()
    failures.append(check("Missing redirect URI raises", False))
except ValueError as exc:
    failures.append(check("Missing redirect URI raises clear ValueError", True, f"-> {str(exc)[:50]}..."))
auth.LINKEDIN_REDIRECT_URI = saved

# 6. Token verification endpoint still OIDC-consistent (no legacy member-profile API)
import inspect
src = inspect.getsource(auth.verify_oauth_token)
failures.append(check(
    "verify_oauth_token uses OIDC userinfo endpoint",
    "api.linkedin.com/v2/userinfo" in src
    and "people/~" not in src and "/v1/people" not in src,
))

# 7. No deprecated scope tokens anywhere in routes or configuration
import glob
route_config_files = (
    ["auth.py", "main.py", "schemas.py", "models.py", "database.py", ".env"]
    + glob.glob("routers/*.py")
)
offenders = []
for fpath in route_config_files:
    with open(fpath, encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    for bad in ("r_liteprofile", "r_emailaddress", "r_basicprofile"):
        if bad in content:
            offenders.append(f"{fpath}:{bad}")
failures.append(check(
    "No deprecated scope tokens in routes/config files",
    not offenders,
    f"-> offenders={offenders or 'none'}",
))

print()
if any(not f for f in failures):
    raise SystemExit(1)
print("All LinkedIn scope checks PASSED")
