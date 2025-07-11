from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from typing import Optional

Base = declarative_base()


class Session(Base):
    """Database model for agent sessions."""

    __tablename__ = "session"

    # Store UUID as string in SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_dir = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    device_id = Column(String, nullable=True)  # Add device_id column
    summary = Column(String, nullable=True)  # Add summary column

    # Relationship with events
    events = relationship(
        "Event", back_populates="session", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        id: uuid.UUID,
        workspace_dir: str,
        device_id: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        """Initialize a session with a UUID and workspace directory.

        Args:
            id: The UUID for the session
            workspace_dir: The workspace directory path
            device_id: Optional device identifier
            summary: Optional task summary
        """
        self.id = str(id)  # Convert UUID to string for storage
        self.workspace_dir = workspace_dir
        self.device_id = device_id
        self.summary = summary


class Event(Base):
    """Database model for agent events."""

    __tablename__ = "event"

    # Store UUID as string in SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36), ForeignKey("session.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, nullable=False)
    event_payload = Column(SQLiteJSON, nullable=False)  # Use SQLite's JSON type

    # Relationship with session
    session = relationship("Session", back_populates="events")

    def __init__(self, session_id: uuid.UUID, event_type: str, event_payload: dict):
        """Initialize an event.

        Args:
            session_id: The UUID of the session this event belongs to
            event_type: The type of event
            event_payload: The event payload as a dictionary
        """
        self.session_id = str(session_id)  # Convert UUID to string for storage
        self.event_type = event_type
        self.event_payload = event_payload


class ProUsage(Base):
    """Database model for tracking Pro user usage."""

    __tablename__ = "pro_usage"

    # Store UUID as string in SQLite
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pro_key = Column(String(8), nullable=False, index=True)  # 8-character hex key
    month_year = Column(String(7), nullable=False)  # Format: YYYY-MM
    sonnet_requests = Column(Integer, default=0)  # Premium model credits used (Sonnet=1, Opus=4, OpenRouter=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, pro_key: str, month_year: str, sonnet_requests: int = 0):
        """Initialize Pro usage tracking.

        Args:
            pro_key: The Pro key (8-character hex string)
            month_year: The month and year in YYYY-MM format
            sonnet_requests: Premium model credits used (default: 0)
        """
        self.pro_key = pro_key
        self.month_year = month_year
        self.sonnet_requests = sonnet_requests


def init_db(engine):
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
