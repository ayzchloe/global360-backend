import os
import sys

# Ensure utf-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    print("[*] Starting Global360 Complete API Integration Test Suite...\n")
    passed = 0
    total = 0

    def assert_test(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}: {details}")

    # 1. Health Check
    res = client.get("/")
    assert_test("Health check GET /", res.status_code == 200 and res.json().get("status") == "online")

    # 2. Auth: Register & Student Auto-creation
    unique_email = f"test.user.{os.urandom(4).hex()}@example.com"
    reg_res = client.post("/auth/register", json={
        "name": "Integration Test User",
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "student"
    })
    assert_test("Register student POST /auth/register", reg_res.status_code == 201)
    token = reg_res.json().get("access_token")
    user_id = reg_res.json().get("user", {}).get("id")

    headers = {"Authorization": f"Bearer {token}"}

    # Verify student record was automatically created
    me_res = client.get("/students/me", headers=headers)
    assert_test("Auto student profile created GET /students/me", me_res.status_code == 200 and me_res.json().get("user_id") == user_id)
    student_id = me_res.json().get("id")

    # 3. Auth: Login
    login_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "SecurePassword123!"
    })
    assert_test("Login POST /auth/login", login_res.status_code == 200 and "access_token" in login_res.json())

    # 4. Auth: Admin Login
    admin_login = client.post("/auth/login", json={
        "email": "admin@global360.edu",
        "password": "AdminPass123!"
    })
    assert_test("Admin login POST /auth/login", admin_login.status_code == 200)
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # 5. Auth: Instructor Login
    instructor_login = client.post("/auth/login", json={
        "email": "instructor@global360.edu",
        "password": "InstructorPass123!"
    })
    assert_test("Instructor login POST /auth/login", instructor_login.status_code == 200)
    instructor_headers = {"Authorization": f"Bearer {instructor_login.json()['access_token']}"}

    # 6. OAuth Google & LinkedIn
    oauth_res = client.post("/auth/oauth/google", json={
        "provider": "google",
        "email": f"google.{os.urandom(3).hex()}@gmail.com",
        "name": "Google OAuth User"
    })
    assert_test("Google OAuth flow POST /auth/oauth/google", oauth_res.status_code == 200 and "access_token" in oauth_res.json())

    oauth_li = client.post("/auth/oauth/linkedin", json={
        "provider": "linkedin",
        "email": f"li.{os.urandom(3).hex()}@example.com",
        "name": "LinkedIn OAuth User"
    })
    assert_test("LinkedIn OAuth flow POST /auth/oauth/linkedin", oauth_li.status_code == 200 and "access_token" in oauth_li.json())

    # 7. Password Recovery Flow
    forgot_res = client.post("/auth/forgot-password", json={"email": unique_email})
    assert_test("Forgot password POST /auth/forgot-password", forgot_res.status_code == 200 and forgot_res.json().get("reset_token") is not None)
    reset_token = forgot_res.json().get("reset_token")

    reset_res = client.post("/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewSecretPassword123!"
    })
    assert_test("Reset password POST /auth/reset-password", reset_res.status_code == 200)

    # 8. Admissions & Newsletter (/admissions page)
    app_res = client.post("/applications/", json={
        "full_name": "Applicant Test",
        "email": f"applicant.{os.urandom(3).hex()}@test.com",
        "track": "ai-automation",
        "message": "Interested in joining"
    })
    assert_test("Submit application POST /applications/", app_res.status_code == 201)

    news_res = client.post("/applications/newsletter", json={"email": f"newsletter.{os.urandom(3).hex()}@test.com"})
    assert_test("Newsletter subscription POST /applications/newsletter", news_res.status_code == 201)

    # 9. Contact & Inquiries (/contact page)
    contact_res = client.post("/contact/", json={
        "name": "Prospective Student",
        "email": "inquiry@test.com",
        "subject": "Tuition Question",
        "message": "Do you offer payment installments?"
    })
    assert_test("Submit contact message POST /contact/", contact_res.status_code == 201)

    # 10. Fee Challans (/portal/admin -> Issue Challan)
    challan_res = client.post("/fee-challans/", json={
        "student_id": student_id,
        "amount": 350.0,
        "due_date": "2026-10-15",
        "title": "Semester 2 Tuition Fee"
    }, headers=admin_headers)
    assert_test("Issue fee challan POST /fee-challans/", challan_res.status_code == 201)
    challan_id = challan_res.json()["id"]

    student_challans = client.get(f"/fee-challans/student/{student_id}", headers=headers)
    assert_test("Get student challans GET /fee-challans/student/{id}", student_challans.status_code == 200 and len(student_challans.json()) > 0)

    pay_res = client.put(f"/fee-challans/{challan_id}/pay", json={"payment_method": "Credit Card"}, headers=headers)
    assert_test("Pay fee challan PUT /fee-challans/{id}/pay", pay_res.status_code == 200 and pay_res.json()["status"] == "paid")

    # 11. Payment Accounts (/portal/admin -> Add Payment Account)
    acc_res = client.post("/payment-accounts/", json={
        "bank_name": "Habib Bank Limited",
        "account_title": "Global360 Education",
        "account_number": "00427901234503",
        "iban": "PK36HABB0000427901234503"
    }, headers=admin_headers)
    assert_test("Add payment account POST /payment-accounts/", acc_res.status_code == 201)

    list_acc = client.get("/payment-accounts/")
    assert_test("List payment accounts GET /payment-accounts/", list_acc.status_code == 200 and len(list_acc.json()) > 0)

    # 12. Partnerships (/portal/admin -> Add Partnership, /partnerships)
    part_res = client.post("/partnerships/", json={
        "company_name": "Anthropic AI Research",
        "partnership_type": "AI Research Partner",
        "website": "https://anthropic.com",
        "description": "Model access and safety benchmark studies."
    }, headers=admin_headers)
    assert_test("Add partnership POST /partnerships/", part_res.status_code == 201)

    part_list = client.get("/partnerships/")
    assert_test("List partnerships GET /partnerships/", part_list.status_code == 200 and len(part_list.json()) > 0)

    # 13. Courses & Syllabus
    courses_res = client.get("/courses/")
    assert_test("List courses GET /courses/", courses_res.status_code == 200 and len(courses_res.json()) > 0)
    first_course = courses_res.json()[0]
    course_id = first_course["id"]

    course_detail = client.get(f"/courses/{course_id}")
    assert_test("Course detail with lessons GET /courses/{id}", course_detail.status_code == 200 and len(course_detail.json()["lessons"]) > 0)
    lesson_id = course_detail.json()["lessons"][0]["id"]

    # 14. Enrollments & Progress Tracking (/portal/dashboard)
    enr_res = client.post("/enrollments/", json={
        "student_id": student_id,
        "course_id": course_id
    }, headers=headers)
    assert_test("Enroll in course POST /enrollments/", enr_res.status_code == 201)
    enrollment_id = enr_res.json()["id"]

    dash_enrollments = client.get(f"/enrollments/student/{student_id}", headers=headers)
    assert_test("Dashboard enrolled courses GET /enrollments/student/{id}", dash_enrollments.status_code == 200 and len(dash_enrollments.json()) > 0)

    prog_res = client.post("/enrollments/progress", json={
        "enrollment_id": enrollment_id,
        "lesson_id": lesson_id,
        "completed": True
    }, headers=headers)
    assert_test("Mark lesson progress POST /enrollments/progress", prog_res.status_code == 201 and prog_res.json()["completed"] is True)

    # 15. Sessions (/portal/dashboard, /portal/instructor, Schedule Session)
    sess_create = client.post("/sessions/", json={
        "title": "Automated Agent Testing Session",
        "course_id": course_id,
        "scheduled_time": "2026-09-20T15:00:00",
        "duration_minutes": 60,
        "meeting_link": "https://meet.google.com/test-session",
        "session_type": "Live Workshop"
    }, headers=instructor_headers)
    assert_test("Schedule session POST /sessions/", sess_create.status_code == 201)

    sessions_list = client.get("/sessions/", headers=headers)
    assert_test("List sessions GET /sessions/", sessions_list.status_code == 200 and len(sessions_list.json()) > 0)

    # 16. Notifications (/portal/dashboard)
    notif_list = client.get("/notifications/", headers=headers)
    assert_test("Dashboard notifications GET /notifications/", notif_list.status_code == 200)

    # 17. Instructor Portal Endpoints (/portal/instructor)
    inst_courses = client.get("/instructor/courses", headers=instructor_headers)
    assert_test("Instructor courses GET /instructor/courses", inst_courses.status_code == 200)

    pending_asg = client.get("/assignments/pending", headers=instructor_headers)
    assert_test("Instructor grading queue GET /assignments/pending", pending_asg.status_code == 200 and len(pending_asg.json()) > 0)

    # 18. Assignment Submission & Instructor Grading
    new_asg = client.post("/assignments/", json={
        "course_id": course_id,
        "title": "Integration Test Project",
        "description": "Submit a working prototype.",
        "max_points": 100
    }, headers=instructor_headers)
    assert_test("Create assignment POST /assignments/", new_asg.status_code == 201)
    asg_id = new_asg.json()["id"]

    sub_res = client.post(f"/assignments/{asg_id}/submit", json={
        "content": "Here is my completed work repository.",
        "file_url": "https://github.com/example/repo"
    }, headers=headers)
    assert_test("Student submit assignment POST /assignments/{id}/submit", sub_res.status_code == 201)
    sub_id = sub_res.json()["id"]

    grade_res = client.post(f"/assignments/submissions/{sub_id}/grade", json={
        "grade": 94.5,
        "feedback": "Great implementation!"
    }, headers=instructor_headers)
    assert_test("Instructor grade submission POST /assignments/submissions/{id}/grade", grade_res.status_code == 200 and grade_res.json()["status"] == "graded")

    # 19. Certificates & Dynamic PDF Generation (/verify/[id])
    cert_verify = client.get("/certificates/verify/CERT-G360-2026-001")
    assert_test(
        "Certificate verification GET /certificates/verify/{id}",
        cert_verify.status_code == 200 and cert_verify.json().get("valid") is True and cert_verify.json().get("course_name") is not None
    )

    pdf_res = client.get("/certificates/CERT-G360-2026-001/pdf")
    is_valid_pdf = pdf_res.status_code == 200 and pdf_res.headers.get("content-type") == "application/pdf" and pdf_res.content.startswith(b"%PDF")
    assert_test("Download certificate PDF GET /certificates/{id}/pdf", is_valid_pdf, f"Status: {pdf_res.status_code}, content: {len(pdf_res.content)} bytes")

    pdf_verify_res = client.get("/certificates/verify/CERT-G360-2026-001/pdf")
    assert_test("Download verified certificate PDF GET /certificates/verify/{id}/pdf", pdf_verify_res.status_code == 200 and pdf_verify_res.content.startswith(b"%PDF"))

    # 20. Admin Portal Endpoints (/portal/admin)
    admin_students = client.get("/students/", headers=admin_headers)
    assert_test("Admin students GET /students/", admin_students.status_code == 200 and len(admin_students.json()) > 0)

    admin_enrollments = client.get("/enrollments/", headers=admin_headers)
    assert_test("Admin enrollments GET /enrollments/", admin_enrollments.status_code == 200 and len(admin_enrollments.json()) > 0)

    admin_audit = client.get("/audit-log/", headers=admin_headers)
    assert_test("Admin audit log GET /audit-log/", admin_audit.status_code == 200 and len(admin_audit.json()) > 0)

    admin_stats = client.get("/admin/stats", headers=admin_headers)
    assert_test(
        "Admin overview stats GET /admin/stats",
        admin_stats.status_code == 200 and admin_stats.json().get("total_students") > 0
    )

    # 21. Content / File Upload
    test_file_content = b"Global360 Sample Course Material Document"
    upload_res = client.post(
        "/uploads/",
        files={"file": ("lecture_notes.txt", test_file_content, "text/plain")},
        headers=headers,
    )
    assert_test(
        "Upload content POST /uploads/",
        upload_res.status_code == 201 and "url" in upload_res.json()
    )

    # 22. Blog Articles
    blog_res = client.get("/blog/")
    assert_test("List blog articles GET /blog/", blog_res.status_code == 200 and len(blog_res.json()) > 0)

    print(f"\n[RESULTS] {passed}/{total} tests PASSED ({round(passed/total*100, 1)}%)")
    if passed == total:
        print("[SUCCESS] All frontend integration gaps are 100% resolved!")
    return passed == total

if __name__ == "__main__":
    success = test_all()
    if not success:
        sys.exit(1)
