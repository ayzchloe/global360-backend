import httpx

BASE_URL = "https://global360-backend-4.onrender.com"

def test_cors():
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    res = httpx.options(f"{BASE_URL}/auth/login", headers=headers)
    print(f"[CORS Preflight] Status: {res.status_code}")
    print("Allow-Origin Header:", res.headers.get("access-control-allow-origin"), "\n")

def test_missing_auth():
    res = httpx.get(f"{BASE_URL}/auth/user")
    print(f"[Missing Auth Check] Status: {res.status_code} (Expected 401)")
    print("Response:", res.json(), "\n")

def test_payload_validation():
    res = httpx.post(f"{BASE_URL}/auth/login", json={})
    print(f"[Validation Check] Status: {res.status_code} (Expected 422)")
    print("Response:", res.json(), "\n")

if __name__ == "__main__":
    test_cors()
    test_missing_auth()
    test_payload_validation()