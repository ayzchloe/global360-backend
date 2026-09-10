from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ==========================================
# AUTH & USER SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "student"
    phone: Optional[str] = None


class UserAdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # "student", "instructor", or "admin"
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OAuthLoginRequest(BaseModel):
    provider: str  # "google" or "linkedin"
    token: Optional[str] = None  # OAuth access token or ID token
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


# ==========================================
# STUDENT SCHEMAS
# ==========================================

class StudentCreate(BaseModel):
    user_id: int
    program: Optional[str] = None
    status: Optional[str] = "active"
    enrollment_no: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class StudentUpdate(BaseModel):
    program: Optional[str] = None
    status: Optional[str] = None
    enrollment_no: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    user_id: int
    enrollment_no: Optional[str] = None
    program: Optional[str] = None
    status: str
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    user: Optional[UserOut] = None

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# LESSON, MODULE & COURSE SCHEMAS
# ==========================================

class LessonCreate(BaseModel):
    title: str
    module_id: Optional[int] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: int = 30
    order: int = 0
    is_free_preview: bool = False


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    module_id: Optional[int] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    order: Optional[int] = None
    is_free_preview: Optional[bool] = None


class LessonOut(BaseModel):
    id: int
    course_id: int
    module_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: int
    order: int
    is_free_preview: bool = False

    class Config:
        orm_mode = True
        from_attributes = True


class ModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = 0


class ModuleOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str] = None
    order: int
    lessons: List[LessonOut] = []

    class Config:
        orm_mode = True
        from_attributes = True


class CourseCreate(BaseModel):
    code: Optional[str] = None
    title: str
    track: str
    level: str = "beginner"
    duration_weeks: int = 4
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructor_id: Optional[int] = None
    order: int = 0
    is_published: bool = True


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    track: Optional[str] = None
    level: Optional[str] = None
    duration_weeks: Optional[int] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructor_id: Optional[int] = None
    order: Optional[int] = None
    is_published: Optional[bool] = None


class CourseOut(BaseModel):
    id: int
    code: Optional[str] = None
    title: str
    track: str
    level: str
    duration_weeks: int
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructor_id: Optional[int] = None
    order: int
    is_published: bool = True

    class Config:
        orm_mode = True
        from_attributes = True


class CourseDetailOut(CourseOut):
    lessons: List[LessonOut] = []
    modules: List[ModuleOut] = []


# ==========================================
# ENROLLMENT & PROGRESS SCHEMAS
# ==========================================

class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int


class EnrollmentOut(BaseModel):
    id: int
    student_id: int
    course_id: int
    status: str
    progress_percentage: float = 0.0
    enrolled_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class EnrollmentDetailOut(EnrollmentOut):
    course: CourseOut


class ProgressMark(BaseModel):
    enrollment_id: int
    lesson_id: int
    completed: bool = True


class ProgressOut(BaseModel):
    id: int
    enrollment_id: int
    lesson_id: int
    completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# ASSIGNMENTS & GRADING SCHEMAS
# ==========================================

class AssignmentCreate(BaseModel):
    course_id: int
    lesson_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_points: int = 100


class AssignmentOut(BaseModel):
    id: int
    course_id: int
    lesson_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_points: int
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class SubmissionCreate(BaseModel):
    content: Optional[str] = None
    file_url: Optional[str] = None


class GradeSubmissionRequest(BaseModel):
    grade: float
    feedback: Optional[str] = None


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None
    submitted_at: datetime
    grade: Optional[float] = None
    feedback: Optional[str] = None
    status: str
    graded_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class PendingSubmissionOut(BaseModel):
    id: int
    assignment_id: int
    assignment_title: str
    course_id: int
    course_title: str
    student_id: int
    student_name: str
    submitted_at: datetime
    content: Optional[str] = None
    file_url: Optional[str] = None
    status: str

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# CERTIFICATES SCHEMAS
# ==========================================

class CertificateCreate(BaseModel):
    student_id: int
    certificate_id: str
    course_name: str
    issued_date: date
    grade: Optional[str] = "Distinction"
    status: Optional[str] = "valid"
    skills: Optional[str] = None


class CertificateOut(BaseModel):
    id: int
    student_id: int
    certificate_id: str
    course_name: str
    issued_date: date
    grade: Optional[str] = "Distinction"
    status: str
    skills: Optional[str] = None
    verification_code: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class CertificateVerifyOut(BaseModel):
    valid: bool
    certificate_id: Optional[str] = None
    course_name: Optional[str] = None
    student_name: Optional[str] = None
    issued_date: Optional[date] = None
    grade: Optional[str] = None
    skills: Optional[List[str]] = []
    status: Optional[str] = None
    credential_url: Optional[str] = None
    pdf_url: Optional[str] = None
    message: Optional[str] = None


# ==========================================
# LIVE SESSIONS SCHEMAS
# ==========================================

class SessionCreate(BaseModel):
    title: str
    course_id: Optional[int] = None
    instructor_name: Optional[str] = None
    scheduled_time: datetime
    duration_minutes: int = 60
    meeting_link: str
    session_type: Optional[str] = "Live Lecture"


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    course_id: Optional[int] = None
    instructor_name: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    meeting_link: Optional[str] = None
    session_type: Optional[str] = None
    status: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    title: str
    course_id: Optional[int] = None
    instructor_id: Optional[int] = None
    instructor_name: Optional[str] = None
    scheduled_time: datetime
    duration_minutes: int
    meeting_link: str
    session_type: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# FINANCE & CHALLAN SCHEMAS
# ==========================================

class FeeChallanCreate(BaseModel):
    student_id: int
    amount: float
    due_date: date
    title: Optional[str] = "Semester Tuition Fee"
    program: Optional[str] = None
    status: Optional[str] = "pending"


class FeeChallanPayRequest(BaseModel):
    payment_method: str = "Online Payment"


class FeeChallanOut(BaseModel):
    id: int
    challan_no: str
    student_id: int
    title: str
    program: Optional[str] = None
    amount: float
    due_date: date
    status: str
    payment_method: Optional[str] = None
    issued_date: date
    paid_date: Optional[date] = None

    class Config:
        orm_mode = True
        from_attributes = True


class PaymentAccountCreate(BaseModel):
    bank_name: str
    account_title: str
    account_number: str
    iban: Optional[str] = None
    branch_code: Optional[str] = None
    instructions: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


class PaymentAccountOut(BaseModel):
    id: int
    bank_name: str
    account_title: str
    account_number: str
    iban: Optional[str] = None
    branch_code: Optional[str] = None
    instructions: Optional[str] = None
    is_active: bool
    is_default: bool

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# PARTNERSHIPS SCHEMAS
# ==========================================

class PartnershipCreate(BaseModel):
    company_name: str
    logo_url: Optional[str] = None
    partnership_type: Optional[str] = "Industry Partner"
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "active"


class PartnershipOut(BaseModel):
    id: int
    company_name: str
    logo_url: Optional[str] = None
    partnership_type: str
    website: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class PartnershipUpdate(BaseModel):
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    partnership_type: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# ==========================================
# CONTACT / INQUIRIES SCHEMAS
# ==========================================

class ContactInquiryCreate(BaseModel):
    name: str
    email: EmailStr
    subject: Optional[str] = "Inquiry from website"
    message: str


class ContactInquiryOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class InquiryStatusUpdate(BaseModel):
    status: str


# ==========================================
# NOTIFICATIONS SCHEMAS
# ==========================================

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    link: Optional[str] = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# ADMIN & AUDIT LOG SCHEMAS
# ==========================================

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    resource: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class AdminStatsOut(BaseModel):
    total_students: int
    active_enrollments: int
    total_courses: int
    pending_applications: int
    pending_assignments: int
    total_certificates_issued: int
    total_revenue: float
    total_challans_issued: int
    paid_challans: int


# ==========================================
# BLOG ARTICLES SCHEMAS
# ==========================================

class BlogArticleCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    summary: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    author_name: Optional[str] = "Global360 Editorial"
    tags: Optional[str] = None
    read_time: Optional[str] = "5 min read"
    is_published: bool = True


class BlogArticleOut(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    author_name: str
    tags: Optional[str] = None
    read_time: str
    is_published: bool
    published_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# ==========================================
# APPLICATION & NEWSLETTER SCHEMAS
# ==========================================

class ApplicationCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    track: str
    message: Optional[str] = None


class ApplicationOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    track: str
    message: Optional[str] = None
    status: str
    submitted_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class NewsletterCreate(BaseModel):
    email: EmailStr