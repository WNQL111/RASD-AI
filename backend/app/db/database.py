# -*- coding: utf-8 -*-
"""
RASD AI Database Persistence Engine & Session Factory
======================================================
Provides a unified SQLAlchemy engine supporting:
  - Local edge execution: SQLite (asis_v2.db) with check_same_thread=False
  - Enterprise clusters: PostgreSQL via DATABASE_URL environment variable
  - Scoped session generator `get_db()` with automatic teardown in finally block.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Try postgresql on localhost:5433 or default to sqlite for seamless local execution
    DATABASE_URL = "sqlite:///./asis_v2.db"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
