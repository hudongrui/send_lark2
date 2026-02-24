from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.sql import func
from pathlib import Path


DATABASE_URL = f"sqlite:///{Path(__file__).parent.parent.parent}/db/message.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Message(Base):
    __tablename__ = "requests"

    trace_id = Column(String(64), primary_key=True)
    username = Column(String(64), nullable=False, index=True)  # x-username from request header
    recipient = Column(String(256), nullable=False, index=False)
    content = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Index for username-base partitioning
    __table_args__ = (Index('idx_username_created', 'username', 'created_at'),)

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
