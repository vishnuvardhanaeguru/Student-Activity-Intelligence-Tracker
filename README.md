# 🎓 SAIT — Student Activity Intelligence Tracker
**Full-Stack Setup Guide**

---

## 📁 Project Structure

```
sait/
├── backend/
│   ├── main.py          ← FastAPI app (routes, models, auth, ML)
│   ├── database.py      ← DB config (SQLite / MySQL / PostgreSQL)
│   ├── requirements.txt ← Python dependencies
│   └── .env.example     ← Environment variable template
└── frontend/
    ├── login.html       ← Login / Registration page
    └── index.html       ← Main dashboard (from previous build)
```

---

## ⚡ Quick Start (5 Minutes)

### 1. Install Python dependencies
```bash
cd backend
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] python-multipart
```

### 2. Configure Database (choose one)

**Option A — SQLite (default, no setup needed)**
```bash
# Nothing to do! SQLite file created automatically.
```

**Option B — MySQL**
```sql
-- In MySQL shell:
CREATE DATABASE sait_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sait_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sait_db.* TO 'sait_user'@'localhost';
FLUSH PRIVILEGES;
```
```bash
pip install pymysql
# Set in .env:
DATABASE_URL=mysql+pymysql://sait_user:your_password@localhost:3306/sait_db
```

**Option C — PostgreSQL**
```sql
-- In psql:
CREATE DATABASE sait_db;
CREATE USER sait_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sait_db TO sait_user;
```
```bash
pip install psycopg2-binary
# Set in .env:
DATABASE_URL=postgresql://sait_user:your_password@localhost:5432/sait_db
```

### 3. Run the backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Open the frontend
Open `frontend/login.html` in your browser.
Or run a simple HTTP server:
```bash
cd frontend
python -m http.server 3000
# Visit: http://localhost:3000/login.html
```

---

## 🔑 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | ❌ | Login → returns JWT token |
| POST | `/auth/register/student` | ❌ | Register new student |
| POST | `/auth/register/teacher` | ❌ | Register new teacher |
| GET | `/auth/me` | ✅ JWT | Get current user profile |
| GET | `/students/` | ✅ Teacher | List all students |
| GET | `/students/{id}` | ✅ JWT | Get student details |
| POST | `/attendance/` | ✅ Teacher | Mark attendance |
| GET | `/attendance/student/{id}` | ✅ JWT | Get attendance records |
| POST | `/scores/` | ✅ Teacher | Add test/quiz score |
| GET | `/scores/student/{id}` | ✅ JWT | Get student scores |
| GET | `/risk/predict?att=&assign=&score=&part=` | ❌ | ML risk prediction |
| GET | `/analytics/class` | ✅ Teacher | Class-wide analytics |

### Swagger UI (Auto-generated docs)
Visit: **http://localhost:8000/docs**

---

## 🔐 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Teacher | teacher@sait.edu | teacher123 |
| Student | sneha@student.sait.edu | student123 |
| Student | rahul@student.sait.edu | student123 |
| Student | riya@student.sait.edu | student123 |

---

## 🤖 ML Risk Prediction Logic

The risk model uses a weighted decision-tree approach:

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| Attendance | ≥80% | 70-80% | <70% |
| Assignments | ≥75% | 65-75% | <65% |
| Avg Score | ≥70 | 60-70 | <60 |
| Participation | ≥50% | 40-50% | <40% |

**Output:** Low Risk / Medium Risk / High Risk + factors list

---

## 🔧 JWT Authentication Flow

```
Client                          Server
  │─── POST /auth/login ─────────►│
  │    {email, password}          │
  │◄── {access_token, role} ──────│
  │                               │
  │─── GET /students/ ────────────►│
  │    Authorization: Bearer <token>│
  │◄── [student list] ────────────│
```

Token expiry: **24 hours**
Algorithm: **HS256**
Password hashing: **bcrypt (cost factor 12)**

---

## 🚀 Production Deployment

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Use PostgreSQL for production
DATABASE_URL=postgresql://user:pass@host/sait_db

# Run with Gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
