"""
End-to-end test: password field on application submission + approval
provisioning.

Run with the project venv:
    .\\venv\\Scripts\\python.exe test_application_password_flow.py

Self-cleaning: every row it creates (application, user, student, enrollment)
is deleted again.
"""
import os
import sys
import uuid

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from database import SessionLocal
import auth
import models

CHOSEN_PASSWORD = "S3curePass!2026"


def login(client: TestClient) -> dict:
    resp = client.post(
        "/auth/login",
        json={"email": "admin@global360.edu", "password": "AdminPass123!"},
    )
    if resp.status_code != 200:
        print("FAIL: could not log in as default admin:", resp.text[:300])
        sys.exit(1)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def main() -> int:
    from main import app, ensure_application_password_column

    # Ensure the hashed_password column exists on pre-existing dev/prod DBs
    # (uvicorn would do this via the lifespan; do it explicitly here).
    ensure_application_password_column()

    client = TestClient(app, raise_server_exceptions=False)
    headers = login(client)
    failures = []
    suffix = uuid.uuid4().hex[:8]
    app_id = None
    legacy_app_id = None
    created_user_ids = []

    db = SessionLocal()
    try:
        # ---- 1) Submit WITH password -----------------------------------
        email1 = f"applicant.pw.{suffix}@test.com"
        r = client.post("/applications/", json={
            "full_name": "Password Applicant",
            "email": email1,
            "track": "ai-automation",
            "message": "hi",
            "password": CHOSEN_PASSWORD,
        })
        print(f"1) POST /applications/ (with password) -> {r.status_code}")
        if r.status_code != 201:
            failures.append(f"submit with password failed: {r.text[:200]}")
        else:
            body = r.json()
            app_id = body["id"]
            if any(k in body for k in ("password", "hashed_password")):
                failures.append("ApplicationOut leaked password/hash")

        # Verify stored hash + no plaintext
        row = db.query(models.Application).filter(models.Application.id == app_id).first()
        stored = row.hashed_password if row else None
        if not stored or not stored.startswith("$2"):
            failures.append(f"stored hash missing/not bcrypt: {stored!r}")
        if stored and CHOSEN_PASSWORD in stored:
            failures.append("plaintext password stored!")
        if stored and not auth.verify_password(CHOSEN_PASSWORD, stored):
            failures.append("stored hash does not verify against chosen password")
        print(f"   stored hash: {stored[:20]}... verify={auth.verify_password(CHOSEN_PASSWORD, stored)}")

        # Legacy row (no password) for fallback test
        r2 = client.post("/applications/", json={
            "full_name": "Legacy Applicant",
            "email": f"applicant.legacy.{suffix}@test.com",
            "track": "full-stack",
        })
        print(f"2) POST /applications/ (no password) -> {r2.status_code}")
        if r2.status_code != 201:
            failures.append("legacy submit (no password) failed")
        else:
            legacy_app_id = r2.json()["id"]
            legacy_row = db.query(models.Application).filter(models.Application.id == legacy_app_id).first()
            if legacy_row.hashed_password is not None:
                failures.append("legacy row should have NULL hashed_password")

        # ---- 3) Validation: too-short password rejected -----------------
        r3 = client.post("/applications/", json={
            "full_name": "Short PW",
            "email": f"short.{suffix}@test.com",
            "track": "ai-automation",
            "password": "short",
        })
        print(f"3) POST /applications/ (short password) -> {r3.status_code} (expect 422)")
        if r3.status_code != 422:
            failures.append("short password not rejected with 422")

        # ---- 4) Approve: user must get the chosen password --------------
        r4 = client.post(f"/applications/{app_id}/approve", headers=headers)
        print(f"4) POST /applications/{app_id}/approve -> {r4.status_code}")
        if r4.status_code != 200:
            failures.append(f"approve failed: {r4.text[:300]}")
        else:
            body = r4.json()
            if body.get("email") != email1:
                failures.append("approval response missing top-level email")
            if not body.get("user_id"):
                failures.append("approval response missing user_id")
            print(f"   response email={body.get('email')!r}, user_id={body.get('user_id')!r}")

            user = db.query(models.User).filter(models.User.email == email1).first()
            if not user:
                failures.append("user not provisioned")
            else:
                created_user_ids.append(user.id)
                if not auth.verify_password(CHOSEN_PASSWORD, user.hashed_password):
                    failures.append("provisioned user hash does not match chosen password")
                # double-hash guard: user hash must equal the stored app hash
                if user.hashed_password != stored:
                    failures.append("user hash != application hash (possible double-hash)")
                # real login with the chosen password
                lr = client.post("/auth/login", json={"email": email1, "password": CHOSEN_PASSWORD})
                print(f"   login with chosen password -> {lr.status_code}")
                if lr.status_code != 200:
                    failures.append("login with chosen password failed")

        # ---- 5) Approve legacy app: default password fallback -----------
        r5 = client.post(f"/applications/{legacy_app_id}/approve", headers=headers)
        print(f"5) POST /applications/{legacy_app_id}/approve (legacy) -> {r5.status_code}")
        if r5.status_code != 200:
            failures.append(f"legacy approve failed: {r5.text[:300]}")
        else:
            email2 = r5.json()["email"]
            user2 = db.query(models.User).filter(models.User.email == email2).first()
            if not user2:
                failures.append("legacy user not provisioned")
            else:
                created_user_ids.append(user2.id)
                lr = client.post("/auth/login", json={
                    "email": email2, "password": "Global360@2026"
                })
                print(f"   login with default password -> {lr.status_code}")
                if lr.status_code != 200:
                    failures.append("legacy fallback default password login failed")
    finally:
        # ---- cleanup --------------------------------------------------------
        for aid in (app_id, legacy_app_id):
            if aid:
                a = db.query(models.Application).filter(models.Application.id == aid).first()
                if a:
                    db.delete(a)
        for uid in created_user_ids:
            u = db.query(models.User).filter(models.User.id == uid).first()
            if u:
                if u.student_profile:
                    db.query(models.Enrollment).filter(
                        models.Enrollment.student_id == u.student_profile.id
                    ).delete()
                    db.delete(u.student_profile)
                db.query(models.PasswordResetToken).filter(
                    models.PasswordResetToken.user_id == u.id
                ).delete()
                db.query(models.Notification).filter(
                    models.Notification.user_id == u.id
                ).delete()
                db.delete(u)
        db.commit()
        db.close()

    print()
    if failures:
        print("FAILED:", "; ".join(failures))
        return 1
    print("ALL APPLICATION-PASSWORD CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
