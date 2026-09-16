"""
Live validation for the /auth/login fix (JSON payload) and CORS config.

Run: python test_login_fix.py
"""
import json
from fastapi.testclient import TestClient

from main import app, CORS_ALLOWED_ORIGINS, ALLOW_ALL_ORIGINS


def check(label, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label} {extra}")
    return cond


failures = []
client = TestClient(app, raise_server_exceptions=False)

# 1. CORS preflight from production origin
origin = "https://global360-zeta.vercel.app"
pf = client.options(
    "/auth/login",
    headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    },
)
failures.append(check(
    "CORS preflight (production origin)",
    pf.status_code == 200 and pf.headers.get("access-control-allow-origin") == origin,
    f"-> {pf.status_code}, allow-origin={pf.headers.get('access-control-allow-origin')}",
))

# 2. CORS for a non-allowed origin must NOT be granted
pf_bad = client.options(
    "/auth/login",
    headers={
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "POST",
    },
)
failures.append(check(
    "CORS rejects unknown origin",
    pf_bad.headers.get("access-control-allow-origin") != "https://evil.example.com",
    f"-> allow-origin={pf_bad.headers.get('access-control-allow-origin')!r}",
))

# 3. JSON login (the frontend contract: {"email": ..., "password": ...})
res = client.post(
    "/auth/login",
    json={"email": "admin@global360.edu", "password": "AdminPass123!"},
    headers={"Origin": origin},
)
body = res.json()
failures.append(check(
    "JSON login with valid credentials",
    res.status_code == 200 and "access_token" in body and body.get("user", {}).get("email"),
    f"-> {res.status_code} keys={list(body)[:3]}",
))
failures.append(check(
    "CORS header on successful login response",
    res.headers.get("access-control-allow-origin") == origin,
    f"-> {res.headers.get('access-control-allow-origin')!r}",
))

# 4. Wrong password -> 401
res_bad = client.post(
    "/auth/login",
    json={"email": "admin@global360.edu", "password": "WrongPassword!"},
)
failures.append(check(
    "Wrong password returns 401",
    res_bad.status_code == 401,
    f"-> {res_bad.status_code} {res_bad.json()}",
))

# 5. Case-insensitive email lookup
res_case = client.post(
    "/auth/login",
    json={"email": "ADMIN@GLOBAL360.EDU", "password": "AdminPass123!"},
)
failures.append(check(
    "Case-insensitive email login",
    res_case.status_code == 200,
    f"-> {res_case.status_code}",
))

# 6. Missing fields -> 422 (schema validation), not 500
res_empty = client.post("/auth/login", json={})
failures.append(check(
    "Empty JSON body returns 422",
    res_empty.status_code == 422,
    f"-> {res_empty.status_code}",
))

# 7. Form-encoded login should fail with 422 (JSON-only contract, but stays a 4xx not 500)
res_form = client.post(
    "/auth/login",
    data=json.dumps({"email": "admin@global360.edu", "password": "AdminPass123!"}),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
failures.append(check(
    "Form-encoded body rejected with 422",
    res_form.status_code == 422,
    f"-> {res_form.status_code}",
))

# 8. Malformed / non-bcrypt stored hash must yield 401, not 500
import auth as auth_mod
failures.append(check(
    "verify_password(None) -> False",
    auth_mod.verify_password("x", None) is False,
))
failures.append(check(
    "verify_password(plaintext stored) -> False",
    auth_mod.verify_password("x", "not-a-hash") is False,
))
failures.append(check(
    "verify_password(corrupt bcrypt) -> False",
    auth_mod.verify_password("x", "$2b$12$corruptedhashcorruptedhashcorruptedhashco") is False,
))
failures.append(check(
    "verify_password(valid hash) works",
    auth_mod.verify_password("AdminPass123!", auth_mod.hash_password("AdminPass123!")) is True,
))

# 9. Config sanity
failures.append(check(
    "CORS origins loaded from env (production domains)",
    "https://www.itsglobal360.com" in CORS_ALLOWED_ORIGINS
    and "https://global360-zeta.vercel.app" in CORS_ALLOWED_ORIGINS,
    f"-> {CORS_ALLOWED_ORIGINS} (allow_all={ALLOW_ALL_ORIGINS})",
))

print()
if failures:
    print(f"{sum(1 for f in failures if not f)} / {len(failures)} checks FAILED")
    raise SystemExit(1)
print("All login/CORS checks PASSED")
