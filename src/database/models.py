from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    discord_message_id = Column(String, unique=True)
    channel_id = Column(String)
    author_id = Column(String)
    author_name = Column(String)
    content = Column(Text)
    created_at = Column(DateTime)

    # Create indexes to speed up searches
    __table_args__ = (
        Index('idx_content', 'content', postgresql_using='gin'),  # Full-text search index
        Index('idx_channel', 'channel_id'),
        Index('idx_author', 'author_id'),
        Index('idx_created', 'created_at'),
    )

# Create database connection
def init_db(db_url="sqlite:///messages.db"):
    """Initialize the database and return the engine"""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine  # Return engine instead of session