from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db_path, get_session
from sqlalchemy import text

router = APIRouter(prefix="/db", tags=["Database"])

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@router.get("/health")
def db_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception:
        return {"database": "error"}


@router.get("/path")
def db_path():
    p = get_db_path("MyEEGApp")
    return {"db_path": str(p), "exists": p.exists()}


@router.get("/tables")
def db_tables(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    ).fetchall()
    return {"tables": [r[0] for r in rows]}
