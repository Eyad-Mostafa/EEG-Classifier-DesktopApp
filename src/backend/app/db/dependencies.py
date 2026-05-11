from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db import get_session as create_session

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a SQLAlchemy Session and closes it after the request.
    Use `db: Session = Depends(get_db_session)` in any route.
    """
    session = create_session()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass