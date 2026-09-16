"""
Regression test: GET /enrollments/ must survive corrupt/orphaned data, and
unhandled 500s must carry CORS headers.

Run with the project venv:
    .\\venv\\Scripts\\python.exe test_enrollments_regression.py

The script is self-cleaning: any row it inserts is deleted again.
"""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from database import SessionLocal
import models


def login(client: TestClient) -> dict:
    resp = client.post(
        "/auth/login",
        json={"email": "admin@global360.edu", "password": "AdminPass123!"},
    )
    if resp.status_code != 200:
        print("FAIL: could not log in as default admin:", resp.text[:300])
        sys.exit(1)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def insert_orphan_enrollment(db) -> int:
    """Insert an enrollment whose course_id points at a non-existent course."""
    orphan = models.Enrollment(
        student_id=db.query(models.Student).first().id,
        course_id=999999,  # no such course
        status="active",
        progress_percentage=0.0,
        enrolled_at=models.utcnow(),
    )
    db.add(orphan)
    db.commit()
    db.refresh(orphan)
    return orphan.id


def insert_null_field_enrollment(db) -> int:
    """Insert an enrollment with NULL status/progress/enrolled_at (raw SQL path)."""
    from sqlalchemy import text

    student_id = db.query(models.Student).first().id
    res = db.execute(
        text(
            "INSERT INTO enrollments (student_id, course_id, status, progress_percentage, enrolled_at) "
            "VALUES (:sid, 1, NULL, NULL, NULL)"
        ),
        {"sid": student_id},
    )
    db.commit()
    return res.lastrowid


def main() -> int:
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    headers = login(client)
    failures = []

    # ---- Test 0: CourseOut consumers still work after relaxing the schema
    for url in ["/courses/", "/courses/1", "/enrollments/student/1"]:
        r = client.get(url, headers=headers)
        print(f"0) GET {url} -> {r.status_code}")
        if r.status_code != 200:
            failures.append(f"{url} broke")

    db = SessionLocal()
    orphan_id = null_id = None
    try:
        # ---- Test 1: normal data still works -------------------------------
        r = client.get("/enrollments/", headers=headers)
        print(f"1) GET /enrollments/ (clean data) -> {r.status_code}")
        if r.status_code != 200:
            failures.append("clean listing failed")

        # ---- Test 2: orphaned enrollment (course missing) ------------------
        orphan_id = insert_orphan_enrollment(db)
        r = client.get("/enrollments/", headers=headers)
        ok = r.status_code == 200
        print(f"2) GET /enrollments/ (orphaned course_id=999999) -> {r.status_code}")
        if not ok:
            failures.append("orphaned enrollment crashed the listing")
        else:
            row = next((e for e in r.json() if e["id"] == orphan_id), None)
            print(f"   orphan row serialized: course={row and row.get('course')}")
            if row is None:
                failures.append("orphaned enrollment missing from listing")

        # ---- Test 3: NULL required fields ----------------------------------
        null_id = insert_null_field_enrollment(db)
        r = client.get("/enrollments/", headers=headers)
        print(f"3) GET /enrollments/ (NULL status/progress/enrolled_at) -> {r.status_code}")
        if r.status_code != 200:
            failures.append("NULL-field enrollment crashed the listing")

        # ---- Test 4: single-enrollment detail route with orphan ------------
        r = client.get(f"/enrollments/{orphan_id}", headers=headers)
        print(f"4) GET /enrollments/{orphan_id} (orphan) -> {r.status_code}")
        if r.status_code != 200:
            failures.append("orphaned enrollment detail crashed")

        # ---- Test 5: unhandled 500 carries CORS headers --------------------
        @app.get("/__test_boom", include_in_schema=False)
        def __boom():
            raise RuntimeError("simulated unhandled error")

        r = client.get(
            "/__test_boom",
            headers={"Origin": (os.getenv("ALLOWED_ORIGINS") or "").split(",")[0].strip()},
        )
        acao = r.headers.get("access-control-allow-origin")
        print(f"5) unhandled 500 -> {r.status_code}, ACAO={acao!r}, body={r.text[:80]}")
        if r.status_code != 500:
            failures.append("unhandled exception did not map to 500")
        if not acao:
            failures.append("unhandled 500 missing CORS headers")

        # ---- Test 6: CORS still on normal responses ------------------------
        r = client.get(
            "/",
            headers={"Origin": (os.getenv("ALLOWED_ORIGINS") or "").split(",")[0].strip()},
        )
        acao = r.headers.get("access-control-allow-origin")
        print(f"6) GET / (normal) ACAO={acao!r}")
        if r.status_code != 200 or not acao:
            failures.append("normal response lost CORS headers")
    finally:
        # ---- cleanup --------------------------------------------------------
        if orphan_id:
            db.query(models.Enrollment).filter(models.Enrollment.id == orphan_id).delete()
        if null_id:
            db.query(models.Enrollment).filter(models.Enrollment.id == null_id).delete()
        db.commit()
        db.close()

    print()
    if failures:
        print("FAILED:", "; ".join(failures))
        return 1
    print("ALL REGRESSION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
