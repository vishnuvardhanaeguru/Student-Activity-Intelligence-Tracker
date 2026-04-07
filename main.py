"""
SAIT Backend - Student Activity Intelligence Tracker
FastAPI + SQLAlchemy + JWT Auth
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os

# ─── CONFIG ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "sait-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Database URL — change to MySQL/PostgreSQL for production
# MySQL:    mysql+pymysql://user:password@localhost/sait_db
# PostgreSQL: postgresql://user:password@localhost/sait_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sait.db")

# ─── DATABASE SETUP ──────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ─── MODELS ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id          = Column(Integer, primary_key=True, index=True)
    email       = Column(String(120), unique=True, index=True, nullable=False)
    hashed_pw   = Column(String(256), nullable=False)
    role        = Column(String(20), nullable=False)   # "student" | "teacher"
    full_name   = Column(String(100), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    is_active   = Column(Boolean, default=True)
    # Relations
    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), unique=True)
    student_id  = Column(String(20), unique=True, index=True)  # e.g. STU-007
    course      = Column(String(60))
    department  = Column(String(80))
    year        = Column(Integer, default=1)
    phone       = Column(String(20))
    # Aggregate stats (updated on each record change)
    attendance_pct  = Column(Float, default=0.0)
    assignment_pct  = Column(Float, default=0.0)
    avg_score       = Column(Float, default=0.0)
    participation   = Column(Float, default=0.0)
    risk_level      = Column(String(10), default="Low")
    # Relations
    user        = relationship("User", back_populates="student_profile")
    attendance  = relationship("Attendance", back_populates="student")
    scores      = relationship("Score", back_populates="student")
    assignments = relationship("Assignment", back_populates="student")


class Teacher(Base):
    __tablename__ = "teachers"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), unique=True)
    teacher_id  = Column(String(20), unique=True, index=True)  # e.g. TCH-001
    department  = Column(String(80))
    subject     = Column(String(80))
    phone       = Column(String(20))
    user        = relationship("User", back_populates="teacher_profile")


class Attendance(Base):
    __tablename__ = "attendance"
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"))
    date        = Column(DateTime, default=datetime.utcnow)
    status      = Column(String(10))  # present | absent | late
    subject     = Column(String(60))
    student     = relationship("Student", back_populates="attendance")


class Score(Base):
    __tablename__ = "scores"
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"))
    subject     = Column(String(60))
    exam_type   = Column(String(40))  # quiz | mid-term | final | assignment
    score       = Column(Float)
    max_score   = Column(Float, default=100)
    date        = Column(DateTime, default=datetime.utcnow)
    student     = relationship("Student", back_populates="scores")


class Assignment(Base):
    __tablename__ = "assignments"
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"))
    title       = Column(String(120))
    subject     = Column(String(60))
    due_date    = Column(DateTime)
    submitted   = Column(Boolean, default=False)
    score       = Column(Float, nullable=True)
    student     = relationship("Student", back_populates="assignments")


class Alert(Base):
    __tablename__ = "alerts"
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"))
    type        = Column(String(20))   # attendance | score | assignment
    severity    = Column(String(10))   # low | medium | high
    message     = Column(Text)
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ─── PYDANTIC SCHEMAS ────────────────────────────────────────────────────────

class RegisterStudentRequest(BaseModel):
    email: str
    password: str
    full_name: str
    student_id: str
    course: str
    department: str
    year: int = 1
    phone: str = ""

class RegisterTeacherRequest(BaseModel):
    email: str
    password: str
    full_name: str
    teacher_id: str
    department: str
    subject: str
    phone: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    full_name: str

class AttendanceCreate(BaseModel):
    student_id: int
    status: str
    subject: str
    date: Optional[datetime] = None

class ScoreCreate(BaseModel):
    student_id: int
    subject: str
    exam_type: str
    score: float
    max_score: float = 100

class AssignmentCreate(BaseModel):
    student_id: int
    title: str
    subject: str
    due_date: datetime
    submitted: bool = False
    score: Optional[float] = None

class StudentOut(BaseModel):
    id: int
    student_id: str
    full_name: str
    email: str
    course: str
    department: str
    year: int
    attendance_pct: float
    assignment_pct: float
    avg_score: float
    participation: float
    risk_level: str
    class Config:
        from_attributes = True

# ─── SECURITY ────────────────────────────────────────────────────────────────

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    creds_exc = HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise creds_exc
    except JWTError:
        raise creds_exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise creds_exc
    return user

def require_teacher(current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return current_user

# ─── ML RISK PREDICTOR ───────────────────────────────────────────────────────

def predict_risk(att: float, assign: float, score: float, part: float = 70) -> str:
    """Simple decision-tree style rule-based ML model."""
    risk_score = 0
    if att < 60:    risk_score += 3.5
    elif att < 70:  risk_score += 2
    elif att < 80:  risk_score += 1
    if assign < 50: risk_score += 2.5
    elif assign < 65: risk_score += 1.5
    elif assign < 75: risk_score += 0.5
    if score < 50:  risk_score += 3
    elif score < 60: risk_score += 2
    elif score < 70: risk_score += 1
    if part < 40:   risk_score += 1
    if risk_score >= 5:   return "High"
    if risk_score >= 2.5: return "Medium"
    return "Low"

def recalculate_student_stats(student: Student, db: Session):
    """Recalculate and update student aggregate stats."""
    records = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    if records:
        present = sum(1 for r in records if r.status == "present")
        student.attendance_pct = round((present / len(records)) * 100, 1)

    scores = db.query(Score).filter(Score.student_id == student.id).all()
    if scores:
        student.avg_score = round(sum(s.score for s in scores) / len(scores), 1)

    assignments = db.query(Assignment).filter(Assignment.student_id == student.id).all()
    if assignments:
        done = sum(1 for a in assignments if a.submitted)
        student.assignment_pct = round((done / len(assignments)) * 100, 1)

    student.risk_level = predict_risk(
        student.attendance_pct, student.assignment_pct,
        student.avg_score, student.participation
    )
    db.commit()

# ─── APP ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="SAIT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# ─── SEED DEMO DATA ──────────────────────────────────────────────────────────

def seed_demo(db: Session):
    if db.query(User).first():
        return  # Already seeded
    demo_users = [
        {"email":"teacher@sait.edu","pw":"teacher123","name":"Dr. Priya Ramesh","role":"teacher",
         "t_id":"TCH-001","dept":"Computer Science","subject":"Data Structures","phone":"+91-9876543210"},
        {"email":"sneha@student.sait.edu","pw":"student123","name":"Sneha Iyer","role":"student",
         "s_id":"STU-007","course":"B.Tech CS","dept":"Computer Science","year":2},
        {"email":"rahul@student.sait.edu","pw":"student123","name":"Rahul Kumar","role":"student",
         "s_id":"STU-012","course":"B.Tech CS","dept":"Computer Science","year":2},
        {"email":"riya@student.sait.edu","pw":"student123","name":"Riya Sharma","role":"student",
         "s_id":"STU-019","course":"B.Tech CS","dept":"Computer Science","year":2},
    ]
    for u in demo_users:
        user = User(email=u["email"], hashed_pw=hash_password(u["pw"]),
                    role=u["role"], full_name=u["name"])
        db.add(user); db.flush()
        if u["role"] == "teacher":
            db.add(Teacher(user_id=user.id, teacher_id=u["t_id"],
                           department=u["dept"], subject=u["subject"], phone=u["phone"]))
        else:
            s = Student(user_id=user.id, student_id=u["s_id"],
                        course=u["course"], department=u["dept"], year=u["year"],
                        attendance_pct=79, assignment_pct=91, avg_score=84,
                        participation=80, risk_level="Low")
            db.add(s)
    db.commit()

@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_demo(db)
    finally:
        db.close()

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.post("/auth/register/student", response_model=Token)
def register_student(req: RegisterStudentRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(Student).filter(Student.student_id == req.student_id).first():
        raise HTTPException(400, "Student ID already exists")
    user = User(email=req.email, hashed_pw=hash_password(req.password),
                role="student", full_name=req.full_name)
    db.add(user); db.flush()
    student = Student(user_id=user.id, student_id=req.student_id,
                      course=req.course, department=req.department,
                      year=req.year, phone=req.phone)
    db.add(student); db.commit(); db.refresh(user)
    token = create_access_token({"sub": user.id, "role": "student"})
    return Token(access_token=token, token_type="bearer",
                 role="student", user_id=user.id, full_name=user.full_name)

@app.post("/auth/register/teacher", response_model=Token)
def register_teacher(req: RegisterTeacherRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=req.email, hashed_pw=hash_password(req.password),
                role="teacher", full_name=req.full_name)
    db.add(user); db.flush()
    teacher = Teacher(user_id=user.id, teacher_id=req.teacher_id,
                      department=req.department, subject=req.subject, phone=req.phone)
    db.add(teacher); db.commit(); db.refresh(user)
    token = create_access_token({"sub": user.id, "role": "teacher"})
    return Token(access_token=token, token_type="bearer",
                 role="teacher", user_id=user.id, full_name=user.full_name)

@app.post("/auth/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_pw):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    token = create_access_token({"sub": user.id, "role": user.role})
    return Token(access_token=token, token_type="bearer",
                 role=user.role, user_id=user.id, full_name=user.full_name)

@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat(),
    }
    if current_user.role == "student":
        s = current_user.student_profile
        if s:
            result["profile"] = {
                "student_id": s.student_id, "course": s.course,
                "department": s.department, "year": s.year,
                "attendance_pct": s.attendance_pct, "assignment_pct": s.assignment_pct,
                "avg_score": s.avg_score, "participation": s.participation,
                "risk_level": s.risk_level,
            }
    elif current_user.role == "teacher":
        t = current_user.teacher_profile
        if t:
            result["profile"] = {
                "teacher_id": t.teacher_id, "department": t.department,
                "subject": t.subject, "phone": t.phone,
            }
    return result

# ─── STUDENT ROUTES ──────────────────────────────────────────────────────────

@app.get("/students/", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db), _: User = Depends(require_teacher)):
    students = db.query(Student).join(User).all()
    return [
        StudentOut(
            id=s.id, student_id=s.student_id,
            full_name=s.user.full_name, email=s.user.email,
            course=s.course, department=s.department, year=s.year,
            attendance_pct=s.attendance_pct, assignment_pct=s.assignment_pct,
            avg_score=s.avg_score, participation=s.participation,
            risk_level=s.risk_level,
        ) for s in students
    ]

@app.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    return {
        "id": s.id, "student_id": s.student_id,
        "full_name": s.user.full_name, "email": s.user.email,
        "course": s.course, "department": s.department, "year": s.year,
        "attendance_pct": s.attendance_pct, "assignment_pct": s.assignment_pct,
        "avg_score": s.avg_score, "participation": s.participation,
        "risk_level": s.risk_level,
        "recent_scores": [
            {"subject": sc.subject, "exam_type": sc.exam_type,
             "score": sc.score, "max_score": sc.max_score,
             "date": sc.date.isoformat()} for sc in s.scores[-10:]
        ],
        "recent_attendance": [
            {"date": a.date.isoformat(), "status": a.status, "subject": a.subject}
            for a in s.attendance[-14:]
        ],
    }

# ─── ATTENDANCE ROUTES ───────────────────────────────────────────────────────

@app.post("/attendance/")
def mark_attendance(req: AttendanceCreate, db: Session = Depends(get_db),
                    _: User = Depends(require_teacher)):
    record = Attendance(
        student_id=req.student_id,
        status=req.status,
        subject=req.subject,
        date=req.date or datetime.utcnow()
    )
    db.add(record); db.flush()
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if student:
        recalculate_student_stats(student, db)
    return {"message": "Attendance marked", "record_id": record.id}

@app.get("/attendance/student/{student_id}")
def get_attendance(student_id: int, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    return [{"id": r.id, "date": r.date.isoformat(), "status": r.status,
             "subject": r.subject} for r in records]

# ─── SCORES ROUTES ───────────────────────────────────────────────────────────

@app.post("/scores/")
def add_score(req: ScoreCreate, db: Session = Depends(get_db),
              _: User = Depends(require_teacher)):
    score = Score(
        student_id=req.student_id, subject=req.subject,
        exam_type=req.exam_type, score=req.score, max_score=req.max_score
    )
    db.add(score); db.flush()
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if student:
        recalculate_student_stats(student, db)
    return {"message": "Score added", "score_id": score.id}

@app.get("/scores/student/{student_id}")
def get_scores(student_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    scores = db.query(Score).filter(Score.student_id == student_id).all()
    return [{"id": s.id, "subject": s.subject, "exam_type": s.exam_type,
             "score": s.score, "max_score": s.max_score,
             "date": s.date.isoformat()} for s in scores]

# ─── RISK PREDICTION ROUTE ───────────────────────────────────────────────────

@app.get("/risk/predict")
def predict_risk_endpoint(att: float, assign: float, score: float, part: float = 70):
    risk = predict_risk(att, assign, score, part)
    factors = []
    if att < 75:    factors.append(f"Low attendance ({att}%)")
    if assign < 75: factors.append(f"Low assignment completion ({assign}%)")
    if score < 65:  factors.append(f"Below-average score ({score})")
    if part < 50:   factors.append(f"Low participation ({part}%)")
    return {"risk_level": risk, "factors": factors,
            "recommendation": "Immediate intervention required" if risk == "High"
                              else "Monitor closely" if risk == "Medium" else "On track"}

# ─── ANALYTICS ROUTE ─────────────────────────────────────────────────────────

@app.get("/analytics/class")
def class_analytics(db: Session = Depends(get_db), _: User = Depends(require_teacher)):
    students = db.query(Student).all()
    if not students:
        return {"total": 0}
    return {
        "total_students": len(students),
        "avg_attendance": round(sum(s.attendance_pct for s in students) / len(students), 1),
        "avg_score": round(sum(s.avg_score for s in students) / len(students), 1),
        "avg_assignment": round(sum(s.assignment_pct for s in students) / len(students), 1),
        "risk_distribution": {
            "Low": sum(1 for s in students if s.risk_level == "Low"),
            "Medium": sum(1 for s in students if s.risk_level == "Medium"),
            "High": sum(1 for s in students if s.risk_level == "High"),
        },
        "at_risk_students": [
            {"id": s.id, "student_id": s.student_id,
             "full_name": s.user.full_name, "risk_level": s.risk_level,
             "attendance_pct": s.attendance_pct, "avg_score": s.avg_score}
            for s in students if s.risk_level in ["High", "Medium"]
        ]
    }

@app.get("/")
def root():
    return {"status": "SAIT API running", "docs": "/docs", "version": "1.0.0"}
