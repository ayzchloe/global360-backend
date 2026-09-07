from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ----- Auth -----
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        orm_mode = True
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----- Student -----
class StudentCreate(BaseModel):
    user_id: int
    program: Optional[str] = None
    status: str = "active"


class StudentOut(BaseModel):
    id: int
    user_id: int
    program: Optional[str]
    status: str

    class Config:
        orm_mode = True
        from_attributes = True


# ----- Certificate -----
class CertificateCreate(BaseModel):
    student_id: int
    certificate_id: str
    course_name: str
    issued_date: date
    status: str = "valid"


class CertificateOut(BaseModel):
    id: int
    student_id: int
    certificate_id: str
    course_name: str
    issued_date: date
    status: str

    class Config:
        orm_mode = True
        from_attributes = True


# ----- Applications (Admissions) -----
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
    track: str
    status: str
    submitted_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# ----- Newsletter -----
class NewsletterCreate(BaseModel):
    email: EmailStr