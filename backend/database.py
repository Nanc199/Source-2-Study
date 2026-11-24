"""
Source2Study - Database Module
SQLAlchemy engine, session, and base setup for SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# For SQLite, we need check_same_thread=False to allow multi-threaded access
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create tables and ensure newly added columns exist in existing databases."""
    Base.metadata.create_all(bind=engine)
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                result = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
                existing_cols = {row[1] for row in result}
                if existing_cols:
                    if "is_verified" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0 NOT NULL")
                        # Existing users from prior tests remain verified
                        conn.exec_driver_sql("UPDATE users SET is_verified = 1")
                    if "verification_token" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN verification_token VARCHAR(255)")
                    if "verification_token_expires_at" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN verification_token_expires_at DATETIME")
                    if "reset_password_token" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN reset_password_token VARCHAR(255)")
                    if "reset_password_expires_at" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN reset_password_expires_at DATETIME")
                    conn.commit()
            except Exception:
                pass


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
