from contextlib import contextmanager
from typing import Optional, Generator
import uuid
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from ii_agent.db.models import Base, Session, Event, ProUsage
from ii_agent.core.event import RealtimeEvent
from ii_agent.utils.constants import PERSISTENT_DATA_ROOT, PERSISTENT_DB_PATH
from datetime import datetime


def get_default_db_path() -> str:
    """Get the appropriate database path based on persistent storage availability."""
    if os.path.exists(PERSISTENT_DATA_ROOT):
        # Ensure the persistent directory exists
        os.makedirs(PERSISTENT_DATA_ROOT, exist_ok=True)
        return PERSISTENT_DB_PATH
    return "events.db"


class DatabaseManager:
    """Manager class for database operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file. If None, uses default persistent path.
        """
        if db_path is None:
            db_path = get_default_db_path()
            
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionFactory = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[DBSession, None, None]:
        """Get a database session as a context manager.

        Yields:
            A database session that will be automatically committed or rolled back
        """
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_session(
        self,
        session_uuid: uuid.UUID,
        workspace_path: Path,
        device_id: Optional[str] = None,
    ) -> None:
        """Create a new session with a UUID-based workspace directory.

        Args:
            session_uuid: The UUID for the session
            workspace_path: The path to the workspace directory
            device_id: Optional device identifier for the session

        Returns:
            A tuple of (session_uuid, workspace_path)
        """

        # Create session in database
        with self.get_session() as session:
            db_session = Session(
                id=session_uuid, workspace_dir=str(workspace_path), device_id=device_id
            )
            session.add(db_session)
            session.flush()  # This will populate the id field

        return session_uuid, workspace_path

    def save_event(self, session_id: uuid.UUID, event: RealtimeEvent) -> uuid.UUID:
        """Save an event to the database.

        Args:
            session_id: The UUID of the session this event belongs to
            event: The event to save

        Returns:
            The UUID of the created event
        """
        with self.get_session() as session:
            db_event = Event(
                session_id=session_id,
                event_type=event.type.value,
                event_payload=event.model_dump(),
            )
            session.add(db_event)
            session.flush()  # This will populate the id field
            return uuid.UUID(db_event.id)

    def get_session_events(self, session_id: uuid.UUID) -> list[Event]:
        """Get all events for a session.

        Args:
            session_id: The UUID of the session

        Returns:
            A list of events for the session
        """
        with self.get_session() as session:
            return (
                session.query(Event).filter(Event.session_id == str(session_id)).all()
            )

    def get_session_by_workspace(self, workspace_dir: str) -> Optional[Session]:
        """Get a session by its workspace directory.

        Args:
            workspace_dir: The workspace directory path

        Returns:
            The session if found, None otherwise
        """
        with self.get_session() as session:
            return (
                session.query(Session)
                .filter(Session.workspace_dir == workspace_dir)
                .first()
            )

    def get_session_by_id(self, session_id: uuid.UUID) -> Optional[Session]:
        """Get a session by its UUID.

        Args:
            session_id: The UUID of the session

        Returns:
            The session if found, None otherwise
        """
        with self.get_session() as session:
            return session.query(Session).filter(Session.id == str(session_id)).first()

    def get_session_by_device_id(self, device_id: str) -> Optional[Session]:
        """Get a session by its device ID.

        Args:
            device_id: The device identifier

        Returns:
            The session if found, None otherwise
        """
        with self.get_session() as session:
            return session.query(Session).filter(Session.device_id == device_id).first()

    def track_pro_usage(self, pro_key: str) -> bool:
        """Track a Sonnet 4 request for a Pro user.

        Args:
            pro_key: The Pro key (8-character hex string)

        Returns:
            True if tracking was successful, False if usage limit exceeded
        """
        current_month = datetime.now().strftime("%Y-%m")
        
        with self.get_session() as session:
            # Get or create usage record for this month
            usage_record = (
                session.query(ProUsage)
                .filter(ProUsage.pro_key == pro_key, ProUsage.month_year == current_month)
                .first()
            )
            
            if usage_record is None:
                # Create new usage record
                usage_record = ProUsage(pro_key=pro_key, month_year=current_month, sonnet_requests=1)
                session.add(usage_record)
            else:
                # Check if user has exceeded limit (e.g., 1000 requests per month)
                if usage_record.sonnet_requests >= 1000:
                    return False
                
                # Increment usage
                usage_record.sonnet_requests += 1
                usage_record.updated_at = datetime.utcnow()
            
            return True

    def get_pro_usage(self, pro_key: str) -> dict:
        """Get usage statistics for a Pro user.

        Args:
            pro_key: The Pro key (8-character hex string)

        Returns:
            Dictionary with usage statistics
        """
        current_month = datetime.now().strftime("%Y-%m")
        
        with self.get_session() as session:
            usage_record = (
                session.query(ProUsage)
                .filter(ProUsage.pro_key == pro_key, ProUsage.month_year == current_month)
                .first()
            )
            
            if usage_record is None:
                return {
                    "month": current_month,
                    "sonnet_requests": 0,
                    "limit": 1000,
                    "remaining": 1000
                }
            
            return {
                "month": current_month,
                "sonnet_requests": usage_record.sonnet_requests,
                "limit": 1000,
                "remaining": max(0, 1000 - usage_record.sonnet_requests)
            }
