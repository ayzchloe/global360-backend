from datetime import date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    Enum,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Float,
)
from sqlalchemy.orm import relationship
from database import Base, utcnow


class UserRole(str, PyEnum):
    """Enumeration of user roles for role-based access control.

    Inherits from ``str`` so enum members compare/hash equal to their
    plain-string values (e.g. ``UserRole.admin == "admin"``), which keeps
    backward compatibility with existing code and database rows.
    """
    student = "student"
    instructor = "instructor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole, native_enum=False), default=UserRole.student)  # "student", "instructor", "admin"
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    student_profile = relationship("Student", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    enrollment_no = Column(String, unique=True, index=True, nullable=True)
    program = Column(String, nullable=True)  # e.g., "AI & Automation", "Full Stack Development"
    status = Column(String, default="active")  # "active", "graduated", "suspended"
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="student_profile")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("AssignmentSubmission", back_populates="student", cascade="all, delete-orphan")
    fee_challans = relationship("FeeChallan", back_populates="student", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=True)  # e.g. "AI-101"
    title = Column(String, nullable=False)
    track = Column(String, nullable=False)  # e.g. "ai-automation", "full-stack", "cloud-devops"
    level = Column(String, default="beginner")  # beginner / intermediate / advanced
    duration_weeks = Column(Integer, default=4)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    instructor = relationship("User", foreign_keys=[instructor_id])
    modules = relationship("Module", back_populates="course", order_by="Module.order", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="course", order_by="Lesson.order", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    sessions = relationship("LiveSession", back_populates="course", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", order_by="Lesson.order", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    duration_minutes = Column(Integer, default=30)
    order = Column(Integer, default=0)
    is_free_preview = Column(Boolean, default=False)

    course = relationship("Course", back_populates="lessons")
    module = relationship("Module", back_populates="lessons")
    progress_records = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="lesson")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(String, default="active")  # active / completed / dropped
    progress_percentage = Column(Float, default=0.0)
    enrolled_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    progress_items = relationship("LessonProgress", back_populates="enrollment", cascade="all, delete-orphan")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    enrollment = relationship("Enrollment", back_populates="progress_items")
    lesson = relationship("Lesson", back_populates="progress_records")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    max_points = Column(Integer, default=100)
    created_at = Column(DateTime, default=utcnow)

    course = relationship("Course", back_populates="assignments")
    lesson = relationship("Lesson", back_populates="assignments")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    content = Column(Text, nullable=True)  # Submission notes or code
    file_url = Column(String, nullable=True)  # Uploaded file / github link
    submitted_at = Column(DateTime, default=utcnow)
    grade = Column(Float, nullable=True)  # e.g. 95.0
    feedback = Column(Text, nullable=True)
    status = Column(String, default="submitted")  # submitted, graded, resubmit
    graded_at = Column(DateTime, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    certificate_id = Column(String, unique=True, index=True, nullable=False)
    course_name = Column(String, nullable=False)
    issued_date = Column(Date, nullable=False, default=date.today)
    grade = Column(String, default="Distinction")  # e.g. "Distinction", "A+", "A"
    status = Column(String, default="valid")  # valid / revoked
    skills = Column(String, nullable=True)  # comma separated skills
    verification_code = Column(String, nullable=True)

    student = relationship("Student", back_populates="certificates")


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    instructor_name = Column(String, nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    meeting_link = Column(String, nullable=False)
    session_type = Column(String, default="Live Lecture")  # Live Lecture, Mentorship, Q&A
    status = Column(String, default="scheduled")  # scheduled, ongoing, completed, cancelled
    created_at = Column(DateTime, default=utcnow)

    course = relationship("Course", back_populates="sessions")
    instructor = relationship("User", foreign_keys=[instructor_id])


class FeeChallan(Base):
    __tablename__ = "fee_challans"

    id = Column(Integer, primary_key=True, index=True)
    challan_no = Column(String, unique=True, index=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    title = Column(String, default="Semester Tuition Fee")
    program = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="pending")  # pending, paid, overdue, cancelled
    payment_method = Column(String, nullable=True)  # Bank Transfer, Online, Card
    issued_date = Column(Date, default=date.today)
    paid_date = Column(Date, nullable=True)

    student = relationship("Student", back_populates="fee_challans")


class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    account_title = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    iban = Column(String, nullable=True)
    branch_code = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class Partnership(Base):
    __tablename__ = "partnerships"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    partnership_type = Column(String, default="Industry Partner")  # Hiring Partner, Academic, Tech
    website = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, archived
    created_at = Column(DateTime, default=utcnow)


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="unread")  # unread, contacted, resolved
    created_at = Column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, GRADE, ISSUE_CERT
    resource = Column(String, nullable=False)  # Course, Student, Certificate, Challan
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow)


class BlogArticle(Base):
    __tablename__ = "blog_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    cover_image = Column(String, nullable=True)
    author_name = Column(String, default="Global360 Editorial")
    tags = Column(String, nullable=True)  # e.g. "AI, Automation, Career"
    read_time = Column(String, default="5 min read")
    is_published = Column(Boolean, default=True)
    published_at = Column(DateTime, default=utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    track = Column(String, nullable=False)
    message = Column(String, nullable=True)
    # bcrypt hash of the password the applicant chose at submission time
    # (NULL for legacy applications). Reused to create the User account when
    # an admin approves the application. Plaintext is never stored.
    hashed_password = Column(String, nullable=True)
    status = Column(String, default="pending")
    submitted_at = Column(DateTime, default=utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    subscribed_at = Column(DateTime, default=utcnow)