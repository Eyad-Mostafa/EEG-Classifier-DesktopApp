from sqlalchemy.orm import Session
from app.db.models import File, Pipeline, AnalysisRun

class SystemRepository:
    def __init__(self, session: Session):
        self.session = session

    def factory_reset(self) -> None:
        """
        Completely wipes all user-generated data, including history, 
        configurations, and global pipeline templates.
        """
        files = self.session.query(File).all()
        for f in files:
            self.session.delete(f)
            
        self.session.query(Pipeline).delete()
        
        self.session.query(AnalysisRun).delete()
        
        self.session.commit()