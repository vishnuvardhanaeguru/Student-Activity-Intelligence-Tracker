"""
SAIT Database Configuration
Supports SQLite (dev), MySQL, and PostgreSQL (production)
"""

import os

# ─── DEVELOPMENT (SQLite) ───────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./sait.db"

# ─── MYSQL ──────────────────────────────────────────────────────────────────
# Install: pip install pymysql
# Setup MySQL:
#   CREATE DATABASE sait_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#   CREATE USER 'sait_user'@'localhost' IDENTIFIED BY 'your_password';
#   GRANT ALL PRIVILEGES ON sait_db.* TO 'sait_user'@'localhost';
MYSQL_URL = "mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}".format(
    user=os.getenv("DB_USER", "sait_user"),
    password=os.getenv("DB_PASSWORD", "your_password"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "3306"),
    dbname=os.getenv("DB_NAME", "sait_db"),
)

# ─── POSTGRESQL ─────────────────────────────────────────────────────────────
# Install: pip install psycopg2-binary
# Setup PostgreSQL:
#   CREATE DATABASE sait_db;
#   CREATE USER sait_user WITH ENCRYPTED PASSWORD 'your_password';
#   GRANT ALL PRIVILEGES ON DATABASE sait_db TO sait_user;
POSTGRES_URL = "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
    user=os.getenv("DB_USER", "sait_user"),
    password=os.getenv("DB_PASSWORD", "your_password"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "sait_db"),
)

# ─── ACTIVE URL (set via env var DATABASE_URL or change here) ───────────────
# Options: SQLITE_URL | MYSQL_URL | POSTGRES_URL
DATABASE_URL = os.getenv("DATABASE_URL", SQLITE_URL)

# ─── ENGINE ARGS ─────────────────────────────────────────────────────────────
def get_engine_args():
    if "sqlite" in DATABASE_URL:
        return {"connect_args": {"check_same_thread": False}}
    elif "mysql" in DATABASE_URL:
        return {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
        }
    elif "postgresql" in DATABASE_URL:
        return {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    return {}
