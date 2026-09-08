"""
Database seeder for Global360 backend.
Populates realistic courses, modules, lessons, users, enrollments,
submissions, fee challans, bank accounts, partnerships, certificates,
live sessions, and blog articles.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base, utcnow
import models
import auth


import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def seed_database():
    print("[*] Rebuilding & seeding Global360 Database...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded with courses
        if db.query(models.Course).count() > 0:
            print("Database already contains courses. Cleaning and re-seeding fresh data...")
            # We preserve existing users if any, or cleanly repopulate
            db.query(models.LessonProgress).delete()
            db.query(models.AssignmentSubmission).delete()
            db.query(models.Assignment).delete()
            db.query(models.Lesson).delete()
            db.query(models.Module).delete()
            db.query(models.Enrollment).delete()
            db.query(models.Certificate).delete()
            db.query(models.FeeChallan).delete()
            db.query(models.PaymentAccount).delete()
            db.query(models.Partnership).delete()
            db.query(models.LiveSession).delete()
            db.query(models.Notification).delete()
            db.query(models.AuditLog).delete()
            db.query(models.BlogArticle).delete()
            db.query(models.ContactInquiry).delete()
            db.query(models.Course).delete()
            db.commit()

        # ----------------------------------------------------
        # 1. Users & Profiles
        # ----------------------------------------------------
        print("Creating core users: Admin, Instructor, Student...")
        
        # Admin
        admin_user = db.query(models.User).filter(models.User.email == "admin@global360.edu").first()
        if not admin_user:
            admin_user = models.User(
                name="Global360 Administrator",
                email="admin@global360.edu",
                hashed_password=auth.hash_password("AdminPass123!"),
                role="admin",
                phone="+1 (555) 019-2831",
                bio="Chief Academic Operations Administrator.",
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        # Instructor
        instructor_user = db.query(models.User).filter(models.User.email == "instructor@global360.edu").first()
        if not instructor_user:
            instructor_user = models.User(
                name="Prof. Marcus Vance",
                email="instructor@global360.edu",
                hashed_password=auth.hash_password("InstructorPass123!"),
                role="instructor",
                phone="+1 (555) 019-4822",
                bio="Senior AI Researcher & Full-Stack Architect with 12+ years of industry experience.",
            )
            db.add(instructor_user)
            db.commit()
            db.refresh(instructor_user)

        # Student 1 (Primary Demo Student)
        student_user = db.query(models.User).filter(models.User.email == "student@global360.edu").first()
        if not student_user:
            student_user = models.User(
                name="Alex Mercer",
                email="student@global360.edu",
                hashed_password=auth.hash_password("StudentPass123!"),
                role="student",
                phone="+1 (555) 019-9941",
                bio="Aspiring AI Engineer specializing in autonomous workflows and web frameworks.",
            )
            db.add(student_user)
            db.commit()
            db.refresh(student_user)

        # Student Profile
        student_profile = db.query(models.Student).filter(models.Student.user_id == student_user.id).first()
        if not student_profile:
            student_profile = models.Student(
                user_id=student_user.id,
                enrollment_no="G360-STU-1001",
                program="AI & Automation Engineering",
                status="active",
                github_url="https://github.com/alexmercer-demo",
                linkedin_url="https://linkedin.com/in/alexmercer-demo",
            )
            db.add(student_profile)
            db.commit()
            db.refresh(student_profile)

        # Student 2
        student_user_2 = db.query(models.User).filter(models.User.email == "sarah.chen@example.com").first()
        if not student_user_2:
            student_user_2 = models.User(
                name="Sarah Chen",
                email="sarah.chen@example.com",
                hashed_password=auth.hash_password("StudentPass123!"),
                role="student",
                phone="+1 (555) 019-7711",
            )
            db.add(student_user_2)
            db.commit()
            db.refresh(student_user_2)

        student_profile_2 = db.query(models.Student).filter(models.Student.user_id == student_user_2.id).first()
        if not student_profile_2:
            student_profile_2 = models.Student(
                user_id=student_user_2.id,
                enrollment_no="G360-STU-1002",
                program="Modern Full-Stack Development",
                status="active",
            )
            db.add(student_profile_2)
            db.commit()
            db.refresh(student_profile_2)

        # ----------------------------------------------------
        # 2. Courses, Modules & Lessons
        # ----------------------------------------------------
        print("Creating courses, modules, and lessons...")

        # Course 1: AI Automation
        course_ai = models.Course(
            code="AI-360",
            title="Autonomous AI Agent Architecture & Automation",
            track="ai-automation",
            level="intermediate",
            duration_weeks=8,
            description="Master multi-agent orchestration, LLM memory architectures, vector embeddings, and enterprise workflow automation.",
            thumbnail_url="https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=800&q=80",
            instructor_id=instructor_user.id,
            order=1,
            is_published=True,
        )
        db.add(course_ai)
        db.commit()
        db.refresh(course_ai)

        # Modules for Course 1
        m1 = models.Module(course_id=course_ai.id, title="Module 1: LLM Foundations & Tool Calling", order=1)
        m2 = models.Module(course_id=course_ai.id, title="Module 2: Multi-Agent Systems & State Graphs", order=2)
        db.add_all([m1, m2])
        db.commit()
        db.refresh(m1)
        db.refresh(m2)

        # Lessons for Course 1
        l1 = models.Lesson(
            course_id=course_ai.id,
            module_id=m1.id,
            title="Introduction to Agentic Runtimes",
            content="Understanding deterministic systems vs cognitive agentic reasoning loops (ReAct pattern).",
            video_url="https://www.youtube.com/watch?v=demo1",
            duration_minutes=45,
            order=1,
            is_free_preview=True,
        )
        l2 = models.Lesson(
            course_id=course_ai.id,
            module_id=m1.id,
            title="Function Calling & Structured JSON Outputs",
            content="Techniques for binding Pydantic schemas directly into LLM prompts and API calls.",
            video_url="https://www.youtube.com/watch?v=demo2",
            duration_minutes=50,
            order=2,
        )
        l3 = models.Lesson(
            course_id=course_ai.id,
            module_id=m2.id,
            title="Multi-Agent Collaboration Networks",
            content="Designing supervisor and worker agent topologies with human-in-the-loop checkpoints.",
            video_url="https://www.youtube.com/watch?v=demo3",
            duration_minutes=60,
            order=3,
        )
        db.add_all([l1, l2, l3])

        # Course 2: Full Stack Development
        course_web = models.Course(
            code="FS-201",
            title="Modern Full-Stack Development with React 19 & FastAPI",
            track="full-stack",
            level="beginner",
            duration_weeks=10,
            description="Build scalable, high-performance web applications using modern React, TypeScript, Tailwind CSS, FastAPI, and PostgreSQL.",
            thumbnail_url="https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=800&q=80",
            instructor_id=instructor_user.id,
            order=2,
            is_published=True,
        )
        db.add(course_web)
        db.commit()
        db.refresh(course_web)

        m_web = models.Module(course_id=course_web.id, title="Module 1: RESTful API Engineering with FastAPI", order=1)
        db.add(m_web)
        db.commit()
        db.refresh(m_web)

        l_web1 = models.Lesson(
            course_id=course_web.id,
            module_id=m_web.id,
            title="FastAPI Dependency Injection & Pydantic Validation",
            content="Building reusable, secure dependency chains for authentication and database sessions.",
            duration_minutes=40,
            order=1,
        )
        l_web2 = models.Lesson(
            course_id=course_web.id,
            module_id=m_web.id,
            title="Connecting React Frontends with OpenAPI Clients",
            content="Consuming backend endpoints seamlessly with automatic TypeScript typings.",
            duration_minutes=45,
            order=2,
        )
        db.add_all([l_web1, l_web2])

        # Course 3: Cloud & DevOps
        course_cloud = models.Course(
            code="OPS-401",
            title="Enterprise Cloud Infrastructure & Kubernetes DevOps",
            track="cloud-devops",
            level="advanced",
            duration_weeks=8,
            description="Deploy resilient cloud native applications with Docker containers, CI/CD automated pipelines, and Kubernetes clusters.",
            thumbnail_url="https://images.unsplash.com/photo-1667372393119-3d4c48d07fc9?auto=format&fit=crop&w=800&q=80",
            instructor_id=instructor_user.id,
            order=3,
            is_published=True,
        )
        db.add(course_cloud)
        db.commit()

        # ----------------------------------------------------
        # 3. Enrollments & Progress Tracking
        # ----------------------------------------------------
        print("Enrolling students and setting up progress tracking...")
        enr1 = models.Enrollment(
            student_id=student_profile.id,
            course_id=course_ai.id,
            status="active",
            progress_percentage=66.7,
            enrolled_at=utcnow() - timedelta(days=14),
        )
        enr2 = models.Enrollment(
            student_id=student_profile.id,
            course_id=course_web.id,
            status="completed",
            progress_percentage=100.0,
            enrolled_at=utcnow() - timedelta(days=40),
            completed_at=utcnow() - timedelta(days=5),
        )
        db.add_all([enr1, enr2])
        db.commit()
        db.refresh(enr1)
        db.refresh(enr2)

        # Progress items for enr1
        p1 = models.LessonProgress(enrollment_id=enr1.id, lesson_id=l1.id, completed=True, completed_at=utcnow() - timedelta(days=10))
        p2 = models.LessonProgress(enrollment_id=enr1.id, lesson_id=l2.id, completed=True, completed_at=utcnow() - timedelta(days=4))
        p3 = models.LessonProgress(enrollment_id=enr1.id, lesson_id=l3.id, completed=False)
        db.add_all([p1, p2, p3])

        # Progress items for enr2
        p_w1 = models.LessonProgress(enrollment_id=enr2.id, lesson_id=l_web1.id, completed=True, completed_at=utcnow() - timedelta(days=20))
        p_w2 = models.LessonProgress(enrollment_id=enr2.id, lesson_id=l_web2.id, completed=True, completed_at=utcnow() - timedelta(days=6))
        db.add_all([p_w1, p_w2])
        db.commit()

        # ----------------------------------------------------
        # 4. Assignments & Submissions (Grading Queue)
        # ----------------------------------------------------
        print("Creating assignments and student submissions...")
        asg1 = models.Assignment(
            course_id=course_ai.id,
            lesson_id=l2.id,
            title="Multi-Tool Agent Implementation",
            description="Implement an autonomous agent capable of searching the web and executing safe Python computations.",
            due_date=utcnow() + timedelta(days=5),
            max_points=100,
        )
        asg2 = models.Assignment(
            course_id=course_web.id,
            lesson_id=l_web1.id,
            title="Production REST API with JWT Auth",
            description="Deliver a secure CRUD backend with role-based dependencies and SQLite/PostgreSQL storage.",
            due_date=utcnow() - timedelta(days=10),
            max_points=100,
        )
        db.add_all([asg1, asg2])
        db.commit()
        db.refresh(asg1)
        db.refresh(asg2)

        # Submission 1: PENDING (Appears in /assignments/pending grading queue!)
        sub1 = models.AssignmentSubmission(
            assignment_id=asg1.id,
            student_id=student_profile.id,
            content="Completed the agent runtime with LangChain and custom calculator tools. Unit tests included.",
            file_url="https://github.com/alexmercer-demo/agent-runtime",
            submitted_at=utcnow() - timedelta(hours=6),
            status="submitted",
        )
        # Submission 2: GRADED
        sub2 = models.AssignmentSubmission(
            assignment_id=asg2.id,
            student_id=student_profile.id,
            content="Repository includes automated tests and Dockerfile containerization.",
            file_url="https://github.com/alexmercer-demo/fastapi-production",
            submitted_at=utcnow() - timedelta(days=8),
            grade=98.0,
            feedback="Exceptional clean architecture and thorough unit test coverage!",
            status="graded",
            graded_at=utcnow() - timedelta(days=7),
        )
        db.add_all([sub1, sub2])
        db.commit()

        # ----------------------------------------------------
        # 5. Certificates & Verification
        # ----------------------------------------------------
        print("Issuing official sample certificates...")
        cert1 = models.Certificate(
            student_id=student_profile.id,
            certificate_id="CERT-G360-2026-001",
            course_name="Modern Full-Stack Development with React 19 & FastAPI",
            issued_date=date.today() - timedelta(days=5),
            grade="High Honors (Distinction)",
            status="valid",
            skills="FastAPI, React 19, TypeScript, PostgreSQL, REST APIs",
            verification_code="8F9A32CB",
        )
        cert2 = models.Certificate(
            student_id=student_profile_2.id,
            certificate_id="CERT-G360-2026-002",
            course_name="Autonomous AI Agent Architecture & Automation",
            issued_date=date.today() - timedelta(days=12),
            grade="Distinction",
            status="valid",
            skills="LLMs, LangChain, Tool Calling, Vector Databases",
            verification_code="12D4E5FA",
        )
        db.add_all([cert1, cert2])
        db.commit()

        # ----------------------------------------------------
        # 6. Live Scheduled Sessions
        # ----------------------------------------------------
        print("Scheduling upcoming live lecture sessions...")
        sess1 = models.LiveSession(
            title="Multi-Agent Memory & Production Deployment Workshop",
            course_id=course_ai.id,
            instructor_id=instructor_user.id,
            instructor_name=instructor_user.name,
            scheduled_time=utcnow() + timedelta(days=1, hours=2),
            duration_minutes=90,
            meeting_link="https://meet.google.com/g360-live-room",
            session_type="Live Workshop",
            status="scheduled",
        )
        sess2 = models.LiveSession(
            title="React 19 Server Actions & Optimistic UI Masterclass",
            course_id=course_web.id,
            instructor_id=instructor_user.id,
            instructor_name=instructor_user.name,
            scheduled_time=utcnow() + timedelta(days=3, hours=5),
            duration_minutes=60,
            meeting_link="https://meet.google.com/g360-react-room",
            session_type="Live Lecture",
            status="scheduled",
        )
        db.add_all([sess1, sess2])
        db.commit()

        # ----------------------------------------------------
        # 7. Fee Challans & Payment Accounts
        # ----------------------------------------------------
        print("Setting up fee challans and banking accounts...")
        challan1 = models.FeeChallan(
            challan_no="CHAL-202609-0001",
            student_id=student_profile.id,
            title="Semester Tuition Fee - AI & Automation",
            program="AI & Automation Engineering",
            amount=450.00,
            due_date=date.today() - timedelta(days=10),
            status="paid",
            payment_method="Bank Transfer (Online)",
            issued_date=date.today() - timedelta(days=25),
            paid_date=date.today() - timedelta(days=12),
        )
        challan2 = models.FeeChallan(
            challan_no="CHAL-202609-0002",
            student_id=student_profile.id,
            title="Advanced Cloud Lab Access Fee",
            program="AI & Automation Engineering",
            amount=150.00,
            due_date=date.today() + timedelta(days=14),
            status="pending",
            issued_date=date.today(),
        )
        db.add_all([challan1, challan2])

        acc1 = models.PaymentAccount(
            bank_name="Standard Chartered Bank",
            account_title="Global360 Education Pvt Ltd",
            account_number="01-2345678-01",
            iban="PK36SCBL0000001234567801",
            branch_code="0234",
            instructions="Please include your Challan Number (e.g. CHAL-202609-0002) in the transaction description.",
            is_active=True,
        )
        acc2 = models.PaymentAccount(
            bank_name="Stripe Digital Gateway",
            account_title="Global360 International Online Portal",
            account_number="Instant Checkout (Visa/Mastercard)",
            iban="N/A",
            instructions="Pay with any credit or debit card through the secure online payment portal.",
            is_active=True,
        )
        db.add_all([acc1, acc2])
        db.commit()

        # ----------------------------------------------------
        # 8. Partnerships
        # ----------------------------------------------------
        print("Adding industry and academic partnerships...")
        p_list = [
            models.Partnership(
                company_name="Google Cloud Platform",
                partnership_type="Tech & Cloud Partner",
                logo_url="https://upload.wikimedia.org/wikipedia/commons/5/51/Google_Cloud_logo.svg",
                website="https://cloud.google.com",
                description="Global360 students receive subsidized cloud computing credits and vertex AI sandbox environments.",
            ),
            models.Partnership(
                company_name="Microsoft Learn for Educators",
                partnership_type="Curriculum Partner",
                logo_url="https://upload.wikimedia.org/wikipedia/commons/9/96/Microsoft_logo_%282012%29.svg",
                website="https://microsoft.com",
                description="Official curriculum alignment with Azure AI Engineer Associate credentials.",
            ),
            models.Partnership(
                company_name="Apex Global Technologies",
                partnership_type="Hiring Partner",
                logo_url="https://images.unsplash.com/photo-1599305445671-ac291c95aaa9?auto=format&fit=crop&w=200&q=80",
                website="https://apexglobal.tech",
                description="Direct placement pipeline for top-tier Global360 graduates into full-stack and AI engineering positions.",
            ),
        ]
        db.add_all(p_list)
        db.commit()

        # ----------------------------------------------------
        # 9. Notifications
        # ----------------------------------------------------
        print("Creating student notifications...")
        n1 = models.Notification(
            user_id=student_user.id,
            title="Welcome to Global360 Portal!",
            message="Your student dashboard is now active. Explore your enrolled courses and upcoming live sessions.",
            link="/portal/dashboard",
            is_read=True,
        )
        n2 = models.Notification(
            user_id=student_user.id,
            title="Upcoming Masterclass Tomorrow",
            message="Prof. Vance will host a live session on Multi-Agent Memory at 2:00 PM UTC. Click to view schedule.",
            link="/portal/dashboard",
            is_read=False,
        )
        n3 = models.Notification(
            user_id=student_user.id,
            title="Assignment Graded: REST API with JWT",
            message="Your submission was graded: 98/100 (Distinction). Instructor feedback is available.",
            link="/portal/dashboard",
            is_read=False,
        )
        db.add_all([n1, n2, n3])
        db.commit()

        # ----------------------------------------------------
        # 10. Audit Logs
        # ----------------------------------------------------
        print("Recording initial system audit logs...")
        logs = [
            models.AuditLog(
                user_id=admin_user.id,
                user_email=admin_user.email,
                action="SYSTEM_INIT",
                resource="System",
                details="Global360 API v2.0 database tables and core schemas initialized successfully.",
                ip_address="127.0.0.1",
            ),
            models.AuditLog(
                user_id=admin_user.id,
                user_email=admin_user.email,
                action="CREATE_COURSE",
                resource="Course",
                details="Published course AI-360: Autonomous AI Agent Architecture & Automation",
                ip_address="127.0.0.1",
            ),
            models.AuditLog(
                user_id=instructor_user.id,
                user_email=instructor_user.email,
                action="GRADE_ASSIGNMENT",
                resource="AssignmentSubmission",
                details="Graded submission for Alex Mercer (Score: 98.0)",
                ip_address="192.168.1.45",
            ),
            models.AuditLog(
                user_id=admin_user.id,
                user_email=admin_user.email,
                action="ISSUE_CERTIFICATE",
                resource="Certificate",
                details="Issued official credential CERT-G360-2026-001",
                ip_address="127.0.0.1",
            ),
        ]
        db.add_all(logs)
        db.commit()

        # ----------------------------------------------------
        # 11. Blog Articles
        # ----------------------------------------------------
        print("Publishing blog articles...")
        b1 = models.BlogArticle(
            title="The 2026 Guide to Autonomous AI Agents in Enterprise Software",
            slug="2026-guide-autonomous-ai-agents",
            summary="How modern cognitive loops, multi-agent frameworks, and vector databases are replacing brittle scripted workflows.",
            content="Autonomous AI agents represent the fundamental evolution from conversational interfaces to proactive systems capable of executing multi-step business objectives...",
            cover_image="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80",
            author_name="Prof. Marcus Vance",
            tags="AI, Agents, Machine Learning, Automation",
            read_time="6 min read",
            is_published=True,
        )
        b2 = models.BlogArticle(
            title="FastAPI vs Express in 2026: Why Python Backends are Winning",
            slug="fastapi-vs-express-2026",
            summary="An in-depth architectural comparison examining typing, async throughput, and ecosystem synergies with modern AI tools.",
            content="With native asynchronous support, Pydantic type guarantees, and automatic OpenAPI generation, FastAPI has emerged as the premier framework for robust backends...",
            cover_image="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80",
            author_name="Global360 Editorial",
            tags="FastAPI, Python, Backend, Web Development",
            read_time="5 min read",
            is_published=True,
        )
        db.add_all([b1, b2])

        # ----------------------------------------------------
        # 12. Contact Inquiries & Admissions Applications
        # ----------------------------------------------------
        inquiry1 = models.ContactInquiry(
            name="David Miller",
            email="david.miller@example.com",
            subject="Inquiry regarding corporate AI training program",
            message="Hello, our engineering team of 25 developers is looking for structured training in Agentic AI. Can we discuss custom corporate cohort packages?",
            status="unread",
        )
        app1 = models.Application(
            full_name="Elena Rostova",
            email="elena.rostova@example.com",
            phone="+1 (555) 392-1049",
            track="ai-automation",
            message="Graduating with CS degree, eager to join the next cohort for AI Agent Architecture.",
            status="pending",
        )
        db.add_all([inquiry1, app1])
        db.commit()

        print("[SUCCESS] Database seeding complete! All tables and relations populated with rich mock data.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during database seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
