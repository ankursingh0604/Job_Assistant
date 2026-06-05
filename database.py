from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///data/applications.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

class Application(Base):
    __tablename__ = "applications"

    id             = Column(Integer, primary_key=True, index=True)
    company        = Column(String, nullable=False)
    role           = Column(String, nullable=False)
    jd_text        = Column(Text, nullable=False)
    match_score    = Column(Float, nullable=True)
    match_reasons  = Column(Text, nullable=True)
    cover_letter   = Column(Text, nullable=True)
    skills_to_highlight = Column(Text, nullable=True)
    status         = Column(String, default="pending")   # pending / applied / interview / rejected / offer
    applied_at     = Column(DateTime, default=datetime.utcnow)
    notes          = Column(Text, nullable=True)

def init_db():
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
